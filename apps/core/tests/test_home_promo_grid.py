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

    def test_grid_shows_up_to_three_items_per_subcategory(self):
        grid = _build_promo_grid(self.menu)
        assignments = [
            assignment
            for group in grid
            for assignment in group['assignments']
        ]

        self.assertEqual(len(assignments), 6)
        self.assertEqual(
            Counter(assignment.subcategory.name for assignment in assignments),
            {self.drafts.name: 3, self.well_spirits.name: 3},
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

        grid = _build_promo_grid(self.menu)
        assignments = [
            assignment
            for group in grid
            for assignment in group['assignments']
        ]

        self.assertEqual(len(assignments), 9)
        self.assertEqual(len({assignment.subcategory_id for assignment in assignments}), 3)
        self.assertNotIn(extra_2.pk, {assignment.subcategory_id for assignment in assignments})

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
