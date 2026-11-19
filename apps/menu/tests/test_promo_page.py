"""The full promo page (menu:menu_detail, menu_detail.html)."""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.menu.models import (
    Menu, MenuCategory, MenuCategoryAssignment, MenuItem, MenuItemCategoryAssignment, MenuSubCategory,
)


class PromoPageSubcategoryTests(TestCase):
    def setUp(self):
        self.menu = Menu.objects.create(title='Happy Hour', slug='happy-hour', menu_type='promo')
        drinks = MenuCategory.objects.create(name='Happy Hour Drinks', slug='happy-hour-drinks',
                                             display_name='From the Bar')
        MenuCategoryAssignment.objects.create(menu=self.menu, category=drinks)
        self.boxes = {}
        for order, (display, names) in enumerate([
            ('Half-Price Drafts', ['Coors Light', 'Miller Lite', 'Bud Light', 'Yuengling']),
            ('Half-Price Well Spirit', ['Svedka Vodka', 'Bacardi Superior Rum', 'Tanqueray Gin',
                                        'Jose Cuervo Gold']),
        ]):
            sub = MenuSubCategory.objects.create(category=drinks, name=f'{display} for Happy Hour',
                                                 display_name=display, slug=f'sub-{order}', order=order)
            self.boxes[display] = names
            for n, name in enumerate(names):
                item = MenuItem.objects.create(name=name, slug=f'{order}-{n}', price=Decimal('3.00'))
                MenuItemCategoryAssignment.objects.create(menu_item=item, category=drinks, subcategory=sub, order=n)

    def test_each_subcategory_renders_as_a_box_with_all_its_items(self):
        html = self.client.get(reverse('menu:menu_detail', args=['happy-hour'])).content.decode()

        self.assertEqual(html.count('class="promo-subcat-card'), 2)
        for display, names in self.boxes.items():
            self.assertIn(display, html)
            for name in names:
                self.assertIn(name, html)
