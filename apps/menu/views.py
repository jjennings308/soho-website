from django.shortcuts import render
from django.db.models import Prefetch
from .models import MenuItem, MenuItemVariation, MenuItemAddon, MenuItemImage

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
        Prefetch('gallery_images', queryset=MenuItemImage.objects.order_by('order')),
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
    return render(request, 'menu/full.html', context)