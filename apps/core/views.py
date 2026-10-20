# core/views.py
from django.core.mail import send_mail, EmailMessage
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views import View
from django.views.generic import TemplateView
from django.db.models import Prefetch
from .forms import ContactForm, EventInquiryForm
from .models import Review, SitePopup, SiteSettings
from .utils import get_banner, get_panel_side
from apps.content.models import ContentGroup
from apps.menu.models import Menu, MenuCategoryAssignment, MenuItemCategoryAssignment


def get_content_group(slug):
    """
    Fetch a ContentGroup with all slots and blocks prefetched.
    Returns None if the group does not exist or has no active blocks.
    Mirrors the template tag but for use in views.
    """
    try:
        group = (
            ContentGroup.objects
            .prefetch_related('slots', 'slots__blocks')
            .get(slug=slug)
        )
    except ContentGroup.DoesNotExist:
        return None
    if not any(slot.get_active_block() for slot in group.slots.all()):
        return None
    return group

def _build_promo_grid(menu):
    """
    Returns a list of category dicts for the homepage 3x3 promo grid.
    Each dict has 'category' and 'assignments' (up to 9 items total,
    grouped by category in display order).

    Structure:
        [
            {'category': <MenuCategory>, 'assignments': [<MenuItemCategoryAssignment>, ...]},
            ...
        ]
    """
    if menu is None:
        return []

    category_assignments = (
        MenuCategoryAssignment.objects
        .filter(menu=menu, category__is_active=True)
        .select_related('category')
        .order_by('display_order')
    )

    result = []
    total = 0

    for cat_assignment in category_assignments:
        if total >= 9:
            break

        remaining = 9 - total
        item_assignments = (
            MenuItemCategoryAssignment.objects
            .filter(
                category=cat_assignment.category,
                is_active=True,
                menu_item__is_available=True,
            )
            .select_related('menu_item', 'subcategory')
            .order_by('subcategory__order', 'order')[:remaining]
        )

        items = list(item_assignments)
        if items:
            result.append({
                'category': cat_assignment.category,
                'assignments': items,
            })
            total += len(items)

    return result

def _get_random_promo_item(menu):
    """
    Returns one random MenuItemCategoryAssignment from the given menu,
    preferring items that have a media image attached.
    Returns None if the menu is None or has no items.
    """
    if menu is None:
        return None

    qs = (
        MenuItemCategoryAssignment.objects
        .filter(
            category__menu_assignments__menu=menu,
            is_active=True,
            menu_item__is_available=True,
        )
        .select_related('menu_item', 'category')
        .order_by('?')
    )
    return qs.first()

class HomeView(TemplateView):
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['site_settings'] = SiteSettings.load()

        # ── Banners ───────────────────────────────────────────────────────────
        context['hero_banner'] = get_banner('hero')

        # ── Catering & Events 50/50 ───────────────────────────────────────────
        context['catering_left']  = get_panel_side('home-events-image')
        context['catering_right'] = get_panel_side('home-events-text')

        # ── Middle Banner ───────────────────────────────────────────────────
        context['middle_banner'] = get_banner('homeMiddleBanner')

        # ── Homepage promo menus ──────────────────────────────────────────────
        promo_qs = Menu.objects.filter(
            menu_type='promo',
            is_active=True,
        ).prefetch_related(
            'menu_category_assignments__category',
        )

        promo_slot_1 = promo_qs.filter(homepage_slot='slot_1').first()
        promo_slot_2 = promo_qs.filter(homepage_slot='slot_2').first()

        context['promo_slot_1']      = promo_slot_1
        context['promo_slot_2']      = promo_slot_2
        context['promo_slot_1_grid'] = _build_promo_grid(promo_slot_1)
        context['promo_slot_2_grid'] = promo_slot_2_grid = _build_promo_grid(promo_slot_2)
        context['promo_slot_1_item'] = _get_random_promo_item(promo_slot_1)
        context['promo_slot_2_item'] = _get_random_promo_item(promo_slot_2)
        context['site_popup'] = SitePopup.get_active()
        context['featured_reviews'] = list(
            Review.objects.filter(is_active=True, is_featured=True)[:3]
        )

        return context

def about(request):
    context = {
        'about_banner':  get_content_group('about_page_banner'),
        'about_mission': get_content_group('about_page_mission'),
        'about_vision':  get_content_group('about_page_vision'),
        'about_values':  get_content_group('about_page_values'),
        'about_info':    get_content_group('about_page_info'),
        'left_contact':  get_panel_side('contact-text'),
        'right_contact': get_panel_side('contact-map'),
        'bottom_banner': get_banner('t'),
    }
    return render(request, 'core/about.html', context)


def contact(request):
    from django.shortcuts import redirect
    return redirect('/about/#contact')

def theme_test(request):
    return render(request, 'core/theme_test.html')

def gallery(request):
    return render(request, 'core/gallery.html')

def online_delivery(request):
    return render(request, 'core/online_delivery.html')


def reviews(request):
    all_reviews = Review.objects.filter(is_active=True)
    context = {
        'reviews': all_reviews,
        'site_settings': SiteSettings.load(),
    }
    return render(request, 'core/reviews.html', context)


def privacy(request):
    return render(request, 'core/legal/privacy.html')


def terms(request):
    return render(request, 'core/legal/terms.html')


def accessibility(request):
    return render(request, 'core/legal/accessibility.html')


def _first_errors(form):
    """Flatten form errors to {field: first message} for the form partials."""
    return {field: errs[0] for field, errs in form.errors.items()}


class ContactFormView(View):
    def post(self, request):
        form = ContactForm(request.POST)
        if not form.is_valid():
            return render(request, 'core/partials/contact_form.html', {
                'errors': _first_errors(form), 'data': request.POST,
            })
        data = form.cleaned_data

        site = SiteSettings.load()
        recipient = site.notification_email or site.email

        if recipient:
            send_mail(
                subject=f'Website Contact — {data["name"]}',
                message=(
                    f'Name: {data["name"]}\n'
                    f'Email: {data["email"]}\n'
                    f'Phone: {data["phone"] or "—"}\n\n'
                    f'{data["message"]}'
                ),
                from_email=None,
                recipient_list=[recipient],
                fail_silently=True,
            )

        return render(request, 'core/partials/contact_form.html', {'success': True})


class EventInquiryView(View):
    def post(self, request):
        form = EventInquiryForm(request.POST)
        if not form.is_valid():
            return render(request, 'core/partials/event_inquiry_form.html', {
                'errors': _first_errors(form), 'data': request.POST,
            })

        inquiry = form.save()

        site = SiteSettings.load()
        restaurant_email = site.notification_email or site.email

        # Notification to restaurant
        if restaurant_email:
            html = render_to_string('core/emails/event_inquiry_notification.html', {'inquiry': inquiry})
            txt = render_to_string('core/emails/event_inquiry_notification.txt', {'inquiry': inquiry})
            send_mail(
                subject=f'New Event Inquiry — {inquiry.get_event_type_display()} from {inquiry.name}',
                message=txt,
                from_email=None,
                recipient_list=[restaurant_email],
                html_message=html,
                fail_silently=True,
            )

        # Confirmation to inquirer
        html = render_to_string('core/emails/event_inquiry_confirmation.html', {'inquiry': inquiry})
        txt = render_to_string('core/emails/event_inquiry_confirmation.txt', {'inquiry': inquiry})
        send_mail(
            subject='We received your event inquiry — SoHo Pittsburgh',
            message=txt,
            from_email=None,
            recipient_list=[inquiry.email],
            html_message=html,
            fail_silently=True,
        )

        return render(request, 'core/partials/event_inquiry_form.html', {'success': True, 'inquiry': inquiry})