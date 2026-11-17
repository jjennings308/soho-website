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

    def test_grid_gives_every_subcategory_a_share_of_the_nine_slots(self):
        grid = _build_promo_grid(self.menu)
        assignments = [
            assignment
            for group in grid
            for assignment in group['assignments']
        ]

        self.assertEqual(len(assignments), 9)
        self.assertEqual(
            Counter(assignment.subcategory.name for assignment in assignments),
            {self.drafts.name: 5, self.well_spirits.name: 4},
        )

    def test_item_card_shows_the_subcategory_above_the_item_name(self):
        assignment = self.draft_items[0]
        html = render_to_string(
            'menu/partials/homepage_item_card.html',
            {'assignment': assignment, 'show_images': False},
        )

        self.assertLess(
            html.index('Half-Price Drafts'),
            html.index(assignment.menu_item.name),
        )

    def test_homepage_renders_both_subcategories_as_item_cards(self):
        html = self.client.get(reverse('core:home')).content.decode()

        self.assertIn('Half-Price Drafts', html)
        self.assertIn('Half-Price Well Spirits', html)
        self.assertNotIn('promo-subcat-card', html)
