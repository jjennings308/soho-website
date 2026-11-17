from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.menu.models import (
    CategoryOptionGroup, MenuCategory, MenuItem, MenuItemAddon, OptionChoice, OptionGroup,
    format_upcharge,
)
from apps.menu.templatetags.menu_tags import _currency


class FormatUpchargeTests(TestCase):
    def test_whole_dollars(self):
        self.assertEqual(format_upcharge(Decimal('7.00')), '+7')

    def test_cents_follow_currency_filter(self):
        self.assertEqual(format_upcharge(Decimal('7.50')), '+7.5')

    def test_none_and_zero_are_blank(self):
        self.assertEqual(format_upcharge(None), '')
        self.assertEqual(format_upcharge(Decimal('0')), '')

    def test_menu_tags_currency_matches_filter(self):
        self.assertEqual(_currency(Decimal('13.50')), '13.5')
        self.assertEqual(_currency(Decimal('14.00')), '14')
        self.assertEqual(_currency(Decimal('0')), '')


class OptionGroupModelTests(TestCase):
    def setUp(self):
        self.salads = MenuCategory.objects.create(name='Soups and Salads', slug='soups-and-salads')
        self.starters = MenuCategory.objects.create(name='Starters', slug='starters')

    def test_slug_filled_from_name_and_unique(self):
        a = OptionGroup.objects.create(name='Dressings')
        b = OptionGroup.objects.create(name='Dressings')
        self.assertEqual(a.slug, 'dressings')
        self.assertEqual(b.slug, 'dressings-2')

    def test_given_slug_kept_on_rename(self):
        g = OptionGroup.objects.create(name='Sauces', slug='sauces')
        g.name = 'Signature Sauces & Dry Rubs'
        g.save()
        g.refresh_from_db()
        self.assertEqual(g.slug, 'sauces')

    def test_choice_upcharge_display(self):
        g = OptionGroup.objects.create(name='Add to Any Salad', is_add_on=True)
        steak = OptionChoice.objects.create(group=g, name='Steak', upcharge=Decimal('8'))
        free = OptionChoice.objects.create(group=g, name='Croutons', upcharge=Decimal('0'))
        none = OptionChoice.objects.create(group=g, name='Extra dressing')
        self.assertEqual(steak.display_upcharge, '+8')
        self.assertEqual(free.display_upcharge, '')
        self.assertEqual(none.display_upcharge, '')

    def test_negative_upcharge_rejected(self):
        g = OptionGroup.objects.create(name='Add to Any Salad', is_add_on=True)
        choice = OptionChoice(group=g, name='Steak', upcharge=Decimal('-1'))
        with self.assertRaises(ValidationError):
            choice.full_clean()

    def test_choices_ordered(self):
        g = OptionGroup.objects.create(name='Dressings')
        OptionChoice.objects.create(group=g, name='Ranch', order=2)
        OptionChoice.objects.create(group=g, name='Caesar', order=1)
        self.assertEqual([c.name for c in g.choices.all()], ['Caesar', 'Ranch'])

    def test_group_without_choices_is_valid(self):
        g = OptionGroup(name='Sides', note='Prices vary')
        g.full_clean()
        g.save()
        self.assertEqual(g.choices.count(), 0)

    def test_one_group_on_several_categories(self):
        g = OptionGroup.objects.create(name='Dressings')
        CategoryOptionGroup.objects.create(category=self.salads, group=g)
        CategoryOptionGroup.objects.create(category=self.starters, group=g)
        self.assertEqual(set(g.categories.all()), {self.salads, self.starters})
        self.assertEqual(list(self.salads.option_groups.all()), [g])

    def test_group_attached_once_per_category(self):
        g = OptionGroup.objects.create(name='Dressings')
        CategoryOptionGroup.objects.create(category=self.salads, group=g)
        with self.assertRaises(IntegrityError):
            CategoryOptionGroup.objects.create(category=self.salads, group=g)


class AddonsDisplayTests(TestCase):
    def setUp(self):
        self.item = MenuItem.objects.create(name='Cheese Quesadilla', slug='cheese-quesadilla')

    def test_lists_available_addons_in_order(self):
        MenuItemAddon.objects.create(menu_item=self.item, name='Pulled pork', price=Decimal('6'), order=2)
        MenuItemAddon.objects.create(menu_item=self.item, name='Grilled chicken', price=Decimal('5'), order=1)
        MenuItemAddon.objects.create(
            menu_item=self.item, name='Steak', price=Decimal('7'), order=3, is_available=False)
        self.assertEqual(self.item.addons_display, 'Grilled chicken +5 · Pulled pork +6')

    def test_blank_when_none(self):
        self.assertEqual(self.item.addons_display, '')

    def test_zero_price_written_to_db_shows_no_bare_plus(self):
        # The model's 0.01 minimum normally prevents this; guard anyway.
        MenuItemAddon.objects.create(menu_item=self.item, name='Salsa', price=Decimal('0'))
        self.assertEqual(self.item.addons_display, 'Salsa')
