# core/views.py
from django.shortcuts import render
from django.views.generic import TemplateView
from django.db.models import Prefetch
from .models import SiteSettings
from .utils import get_banner, get_panel_side
from apps.content.models import ContentGroup
from apps.menu.models import Menu, MenuCategoryAssignment, MenuItemCategoryAssignment


def get_content_group(slug):
    """
    Fetch a ContentGroup with all slots and blocks prefetched.
    Returns None if the group does not exist.
    Mirrors the template tag but for use in views.
    """
    try:
        return (
            ContentGroup.objects
            .prefetch_related('slots', 'slots__blocks')
            .get(slug=slug)
        )
    except ContentGroup.DoesNotExist:
        return None

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
            .prefetch_related('menu_item__media')
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
        .prefetch_related('menu_item__media')
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

        # ── Catering Banner ───────────────────────────────────────────────────
        context['catering_banner'] = get_banner('catering')

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
    }
    return render(request, 'core/about.html', context)


def contact(request):
    context = {
        'left_contact':  get_panel_side('contact-text'),
        'right_contact': get_panel_side('contact-map'),
    }
    return render(request, 'contact.html', context)

def theme_test(request):
    return render(request, 'core/theme_test.html')

def gallery(request):
    return render(request, 'core/gallery.html')

def online_delivery(request):
    return render(request, 'core/online_delivery.html')