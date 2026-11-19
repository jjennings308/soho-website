from collections import Counter
from decimal import Decimal

from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse

from apps.core.views import _build_promo_grid
from apps.menu.models import (
    Menu,
    MenuCategory,
    MenuCategoryAssignment,
    MenuItem,
    MenuItemCategoryAssignment,
    MenuSubCategory,
)


class HomePromoGridTests(TestCase):
    def setUp(self):
        self.menu = Menu.objects.create(
            title='Happy Hour', slug='happy-hour', menu_type='promo',
            homepage_slot='slot_1',
        )
        self.category = MenuCategory.objects.create(
            name='Happy Hour Drinks', slug='happy-hour-drinks',
            display_name='From the Bar',
        )
        MenuCategoryAssignment.objects.create(menu=self.menu, category=self.category)

        self.drafts = MenuSubCategory.objects.create(
            category=self.category, name='Half-Price Drafts for Happy Hour',
            display_name='Half-Price Drafts', slug='half-price-drafts', order=0,
        )
        self.well_spirits = MenuSubCategory.objects.create(
            category=self.category, name='Half-Price Well Spirits for Happy Hour',
            display_name='Half-Price Well Spirits', slug='half-price-well-spirits',
            order=1,
        )
        self.draft_items = [
            self.make_item('Draft', number, self.drafts) for number in range(6)
        ]
        self.well_items = [
            self.make_item('Well', number, self.well_spirits) for number in range(6)
        ]

    def make_item(self, prefix, number, subcategory):
        item = MenuItem.objects.create(
            name=f'{prefix} {number}', slug=f'{prefix.lower()}-{number}',
            price=Decimal('5.00'),
        )
        return MenuItemCategoryAssignment.objects.create(
            menu_item=item, category=self.category,
            subcategory=subcategory, order=number,
        )

    def grid_assignments(self):
        return [assignment for group in _build_promo_grid(self.menu) for assignment in group['assignments']]

    def test_grid_shows_all_items_in_each_subcategory(self):
        assignments = self.grid_assignments()

        self.assertEqual(len(assignments), 12)
        self.assertEqual(
            Counter(assignment.subcategory.name for assignment in assignments),
            {self.drafts.name: 6, self.well_spirits.name: 6},
        )

    def test_grid_uses_at_most_three_subcategories(self):
        extra_1 = MenuSubCategory.objects.create(
            category=self.category, name='Extra One', slug='extra-one', order=2,
        )
        extra_2 = MenuSubCategory.objects.create(
            category=self.category, name='Extra Two', slug='extra-two', order=3,
        )
        for subcategory in (extra_1, extra_2):
            for number in range(3):
                self.make_item(f'Extra{subcategory.order}', number, subcategory)

        assignments = self.grid_assignments()

        self.assertEqual(len(assignments), 6 + 6 + 3)
        self.assertEqual(
            {assignment.subcategory_id for assignment in assignments},
            {self.drafts.pk, self.well_spirits.pk, extra_1.pk},
        )
        self.assertNotIn(extra_2.pk, {assignment.subcategory_id for assignment in assignments})

    def add_food_category(self, count):
        """A category of plain items, shown before the drinks (like Weekday Happy Hour)."""
        food = MenuCategory.objects.create(name='Happy Hour Food', slug='happy-hour-food')
        MenuCategoryAssignment.objects.filter(menu=self.menu, category=self.category).update(display_order=2)
        MenuCategoryAssignment.objects.create(menu=self.menu, category=food, display_order=1)
        for number in range(count):
            item = MenuItem.objects.create(name=f'Food {number}', slug=f'food-{number}', price=Decimal('6.00'))
            MenuItemCategoryAssignment.objects.create(menu_item=item, category=food, order=number)
        return food

    def test_subcategory_box_counts_as_one_slot(self):
        # The real bug: 6 food items came first, then each draft counted as a slot, so the
        # drafts box lost an item and the well spirits box never showed.
        food = self.add_food_category(6)

        grid = _build_promo_grid(self.menu)

        self.assertEqual([group['category'] for group in grid], [food, self.category])
        self.assertEqual(len(grid[0]['assignments']), 6)
        self.assertEqual(
            Counter(assignment.subcategory_id for assignment in grid[1]['assignments']),
            {self.drafts.pk: 6, self.well_spirits.pk: 6},
        )

    def test_plain_items_stop_when_the_slots_run_out(self):
        for number in range(8):
            item = MenuItem.objects.create(name=f'Plain {number}', slug=f'plain-{number}', price=Decimal('4.00'))
            MenuItemCategoryAssignment.objects.create(menu_item=item, category=self.category, order=number)

        assignments = self.grid_assignments()

        plain = [assignment for assignment in assignments if assignment.subcategory_id is None]
        boxed = [assignment for assignment in assignments if assignment.subcategory_id]
        self.assertEqual(len(plain), 7)          # 9 slots − 2 boxes
        self.assertEqual(len(boxed), 12)         # both boxes, all their items

    def test_featured_card_shows_subcategory_above_item_name(self):
        assignment = self.draft_items[0]
        html = render_to_string(
            'menu/partials/homepage_promo_card.html',
            {'menu': self.menu, 'assignment': assignment, 'anchor': 'promo1'},
        )

        self.assertLess(
            html.index('Half-Price Drafts'),
            html.index(assignment.menu_item.name),
        )

    def test_homepage_groups_subcategories_like_the_menu(self):
        html = self.client.get(reverse('core:home')).content.decode()

        self.assertEqual(html.count('promo-subcat-card'), 2)
        self.assertIn('Half-Price Drafts', html)
        self.assertIn('Half-Price Well Spirits', html)
