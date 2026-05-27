from django.shortcuts import render, get_object_or_404
from django.http import Http404, JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Prefetch
from django.views.generic import TemplateView
from apps.events.models import EventDay

from .models import (
    Menu,
    MenuCategoryAssignment,
    MenuItemCategoryAssignment,
    MenuItemVariation,
    MenuItemAddon,
    MenuItem,
)
from .utils import get_active_menus


# =============================================================================
# HELPERS
# =============================================================================

def _prefetch_category_assignments(menu_qs):
    """
    Applies consistent prefetch to a Menu queryset so category and item
    assignments are fetched in as few queries as possible.
    """
    return menu_qs.prefetch_related(
        Prefetch(
            'menu_category_assignments',
            queryset=MenuCategoryAssignment.objects.select_related(
                'category'
            ).order_by('display_order'),
        ),
    )


def _item_assignment_qs():
    """
    Returns a base MenuItemCategoryAssignment queryset with item data
    fully prefetched. Used by views and template tags.
    """
    return MenuItemCategoryAssignment.objects.filter(
        is_active=True,
        menu_item__is_available=True,
    ).select_related(
        'menu_item',
        'subcategory',
        'category',
    ).prefetch_related(
        Prefetch(
            'menu_item__variations',
            queryset=MenuItemVariation.objects.filter(
                is_available=True
            ).order_by('order', 'price'),
        ),
        Prefetch(
            'menu_item__addons',
            queryset=MenuItemAddon.objects.filter(
                is_available=True
            ).order_by('order', 'price'),
        ),
    ).order_by('subcategory__order', 'order')


# =============================================================================
# MENU VIEWS
# =============================================================================

def full(request):
    """
    Renders the main menu page using role-based menu selection.
    ?type=food  — food sections only
    ?type=drinks — drinks sections only
    no param    — both food then drinks sequentially
    """
    active_type = request.GET.get('type')  # 'food', 'drinks', or None
    menus = get_active_menus()

    context = {
        'food_menu':   menus['food']   if active_type in (None, 'food')   else None,
        'drink_menu':  menus['drinks'] if active_type in (None, 'drinks') else None,
        'event_mode':  menus['event_mode'],
        'active_type': active_type,
        'title':       ' - Menu',
    }
    return render(request, 'menu/menu.html', context)


def menu_detail(request, slug):
    """
    Detail view for any named Menu — default or promo.
    Used for promo landing pages, happy hour page, etc.
    """
    menu = get_object_or_404(
        Menu.objects.prefetch_related(
            Prefetch(
                'menu_category_assignments',
                queryset=MenuCategoryAssignment.objects.select_related(
                    'category'
                ).order_by('display_order'),
            ),
        ),
        slug=slug,
        is_active=True,
    )

    if not menu.is_currently_active:
        raise Http404

    colors = menu.resolve_colors()

    context = {
        'menu':                 menu,
        'category_assignments': menu.menu_category_assignments.all(),
        'colors':               colors,
        'title':                f' - {menu.title}',
    }
    return render(request, 'menu/menu_detail.html', context)


def promotions(request):
    """Lists all currently active promotional menus."""
    promo_menus = Menu.objects.filter(
        menu_type='promo',
        is_active=True,
    ).prefetch_related(
        Prefetch(
            'menu_category_assignments',
            queryset=MenuCategoryAssignment.objects.select_related(
                'category'
            ).order_by('display_order'),
        ),
    ).order_by('active_from', 'title')

    active_promos = [m for m in promo_menus if m.is_currently_active]

    # TODO: add show_in_event_mode boolean to Menu to control promo visibility
    # during event mode (e.g. hide Happy Hour during game days)

    context = {
        'promo_menus': active_promos,
        'title':       ' - Promotions',
    }
    return render(request, 'menu/promotions.html', context)


class EventDayMenuView(TemplateView):
    """
    Always renders the event menus (event_food + event_drinks roles)
    regardless of whether event mode is currently active.

    When event mode is NOT active, shows a preview banner explaining
    this is the limited menu served during select events.
    When event mode IS active, renders identically to the main menu page.
    """
    template_name = 'menu/event_day_menu.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['food_menu']  = Menu.objects.filter(role='event_food').first()
        context['drink_menu'] = Menu.objects.filter(role='event_drinks').first()
        context['is_preview'] = not (EventDay.get_current_menu_mode() == 'limited')
        return context


# =============================================================================
# API ENDPOINT
# =============================================================================

@staff_member_required
def menu_item_data(request, pk):
    """
    Returns basic item data as JSON for admin use
    (e.g. auto-filling promo item fields).
    """
    item = get_object_or_404(MenuItem, pk=pk)
    return JsonResponse({
        'name':        item.name,
        'price':       str(item.price) if item.price else '',
        'description': item.description or '',
    })
