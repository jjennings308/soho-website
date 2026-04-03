from django.shortcuts import render, get_object_or_404
from django.http import Http404, JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Prefetch

from apps.core.utils import get_active_template
from apps.events.models import EventDay

from .models import (
    Menu,
    MenuCategoryAssignment,
    MenuItemCategoryAssignment,
    MenuItemVariation,
    MenuItemAddon,
    MenuItem,
)


# =============================================================================
# HELPERS
# =============================================================================

def _get_menu_mode():
    """Returns 'limited' or 'full' based on EventDay calendar + SiteSettings."""
    return EventDay.get_current_menu_mode()


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


def _item_assignment_qs(limited_menu=False):
    """
    Returns a base MenuItemCategoryAssignment queryset with item data
    fully prefetched. Used by views and template tags.
    """
    qs = MenuItemCategoryAssignment.objects.filter(
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
        'menu_item__media',
    ).order_by('subcategory__order', 'order')

    if limited_menu:
        qs = qs.filter(available_game_day=True)

    return qs


# =============================================================================
# MENU VIEWS
# =============================================================================

def full(request):
    """
    Renders the default menu. Supports ?type=food or ?type=drinks to filter
    to a single tab on a combined menu.
    """
    active_type = request.GET.get('type')  # 'food', 'drinks', or None

    # Determine which default menu to load
    if active_type == 'food':
        menu_type = 'food'
    elif active_type == 'drinks':
        menu_type = 'drinks'
    else:
        menu_type = 'combined'

    menu = Menu.objects.filter(
        menu_type=menu_type,
        is_default=True,
        is_active=True,
    ).prefetch_related(
        Prefetch(
            'menu_category_assignments',
            queryset=MenuCategoryAssignment.objects.select_related(
                'category'
            ).order_by('display_order'),
        ),
    ).first()

    # Fallback: if no combined menu, try food
    if not menu:
        menu = Menu.objects.filter(
            is_default=True,
            is_active=True,
        ).prefetch_related(
            Prefetch(
                'menu_category_assignments',
                queryset=MenuCategoryAssignment.objects.select_related(
                    'category'
                ).order_by('display_order'),
            ),
        ).first()

    limited_menu = (_get_menu_mode() == 'limited')

    titles = {
        'food':     ' - Food Menu',
        'drinks':   ' - Drink Menu',
        'combined': ' - Menu',
    }

    context = {
        'menu':               menu,
        'category_assignments': menu.menu_category_assignments.all() if menu else [],
        'active_type':        active_type,
        'limited_menu':       limited_menu,
        'title':              titles.get(menu_type, ' - Menu'),
    }
    return render(request, get_active_template('menu'), context)


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

    limited_menu = (_get_menu_mode() == 'limited')
    colors = menu.resolve_colors()

    context = {
        'menu':               menu,
        'category_assignments': menu.menu_category_assignments.all(),
        'colors':             colors,
        'limited_menu':       limited_menu,
        'title':              f' - {menu.title}',
    }
    return render(request, get_active_template('menu_detail'), context)


def promotions(request):
    """Lists all currently active promotional menus."""
    limited_menu = (_get_menu_mode() == 'limited')

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
    ).order_by('start_date', 'title')

    active_promos = [m for m in promo_menus if m.is_currently_active]

    context = {
        'promo_menus':  active_promos,
        'limited_menu': limited_menu,
        'title':        ' - Promotions',
    }
    return render(request, get_active_template('promotions'), context)


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
