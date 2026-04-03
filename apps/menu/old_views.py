from django.shortcuts import render
from django.db.models import Prefetch
from apps.core.utils import get_active_template
from django.shortcuts import get_object_or_404
from .models import MenuItem, MenuItemVariation, MenuItemAddon, MenuPromotion, MenuPromotionItem
def full(request):
    menu_type = request.GET.get('type')  # ?type=Food or ?type=Drinks, absent = all

    menu_items = MenuItem.objects.filter(is_available=True)
    
    if menu_type:
        menu_items = menu_items.filter(category__menu_type__name=menu_type)

    menu_items = menu_items.select_related(
        'category', 'category__menu_type', 'subcategory',
    ).prefetch_related(
        Prefetch('variations',     queryset=MenuItemVariation.objects.filter(is_available=True).order_by('order', 'price')),
        Prefetch('addons',         queryset=MenuItemAddon.objects.filter(is_available=True).order_by('order', 'price')),
    ).order_by(
        'category__menu_type__order', 'category__order', 'category__name',
        'subcategory__order', 'subcategory__name', 'order', 'name',
    )

    titles = {'Food': ' - Food Menu', 'Drinks': ' - Drink Menu'}
    context = {
        'menu_items': menu_items,
        'title': titles.get(menu_type, ' - Full Menu'),
        'active_type': menu_type,  # useful for highlighting active nav link
    }
    return render(request, get_active_template('menu'), context)

def promotions(request):
    """List all currently active promotions."""
    active_promotions = MenuPromotion.objects.filter(is_active=True).prefetch_related(
        Prefetch(
            'promotion_items',
            queryset=MenuPromotionItem.objects.select_related('menu_item').order_by('order'),
        )
    )
    # Filter by date range in Python using the is_currently_active property
    active_promotions = [p for p in active_promotions if p.is_currently_active]

    context = {
        'promotions': active_promotions,
        'title': ' - Promotions',
    }
    return render(request, get_active_template('promotions'), context)


def promotion_detail(request, slug):
    """Detail view for a single promotion."""
    promotion = get_object_or_404(MenuPromotion, slug=slug, is_active=True)

    if not promotion.is_currently_active:
        from django.http import Http404
        raise Http404

    items = promotion.promotion_items.select_related('menu_item').order_by('order')
    colors = promotion.resolve_colors()

    context = {
        'promotion': promotion,
        'items': items,
        'colors': colors,
        'title': f' - {promotion.title}',
    }
    return render(request, get_active_template('promotion_detail'), context)

from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def menu_item_data(request, pk):
    item = get_object_or_404(MenuItem, pk=pk)
    return JsonResponse({
        'name': item.name,
        'price': str(item.price) if item.price else '',
        'description': item.description or '',
    })