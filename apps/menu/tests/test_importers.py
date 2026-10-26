import csv
import io
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.test import TestCase

from apps.core.models import ColorScheme
from apps.menu import importers as im
from apps.menu.models import (
    Menu, MenuCategory, MenuCategoryAssignment, MenuItem, MenuItemAddon,
    MenuItemCategoryAssignment, MenuItemVariation, MenuSubCategory,
)


def make_csv(*rows):
    """CSV text from dicts; the header is the union of keys in first-seen order."""
    header = []
    for row in rows:
        header += [k for k in row if k not in header]
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=header)
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


class MenuFixture(TestCase):
    def setUp(self):
        self.scheme = ColorScheme.objects.create(name='Black & Gold')
        self.burgers = MenuCategory.objects.create(name='Burgers', slug='burgers', order=1)
        self.beer = MenuCategory.objects.create(name='Beer', slug='beer', category_type='drinks', order=2)
        self.on_tap = MenuSubCategory.objects.create(category=self.beer, name='On Tap', slug='beer-on-tap')
        self.burger = MenuItem.objects.create(
            name='Classic Burger', slug='classic-burger', price=Decimal('14.00'),
            short_description='Half-pound patty', description='<p>Our <strong>classic</strong>.</p>')
        self.lager = MenuItem.objects.create(name='Lager', slug='lager', price=Decimal('6.00'))
        MenuItemVariation.objects.create(menu_item=self.lager, name='Pint', price=Decimal('6.00'))
        MenuItemAddon.objects.create(menu_item=self.burger, name='Bacon', price=Decimal('2.00'))
        self.food = Menu.objects.create(title='Food Menu', slug='food-menu', menu_type='food',
                                        role='default_food', color_scheme=self.scheme)
        MenuCategoryAssignment.objects.create(menu=self.food, category=self.burgers, display_order=1)
        MenuItemCategoryAssignment.objects.create(menu_item=self.burger, category=self.burgers, order=1)
        MenuItemCategoryAssignment.objects.create(menu_item=self.lager, category=self.beer,
                                                  subcategory=self.on_tap)


class RoundTripTests(MenuFixture):
    def test_export_then_import_changes_nothing_for_every_kind(self):
        for kind in im.KIND_ORDER:
            with self.subTest(kind=kind):
                result = im.parse(kind, im.export_csv(kind))
                self.assertTrue(result.ok, [r.errors for r in result.rows] + result.errors)
                self.assertTrue(result.rows)
                self.assertEqual({r.action for r in result.rows}, {'unchanged'})

    def test_export_header_matches_import_columns(self):
        header = next(csv.reader(io.StringIO(im.export_csv('items').lstrip('﻿'))))
        self.assertEqual(header, [c.name for c in im.KINDS['items'].columns])

    def test_legacy_choice_value_round_trips_when_unchanged(self):
        Menu.objects.filter(pk=self.food.pk).update(menu_type='combined')  # no longer a valid choice
        result = im.parse('menus', im.export_csv('menus'))
        self.assertTrue(result.ok)
        result = im.parse('menus', make_csv({'slug': 'food-menu', 'menu_type': 'combined', 'title': 'Renamed'}))
        self.assertEqual(result.rows[0].action, 'update')
        self.assertEqual(list(result.rows[0].changes), ['title'])


class CreateUpdateTests(MenuFixture):
    def test_create_one_of_each_kind_in_order(self):
        steps = [
            ('categories', {'name': 'Desserts', 'order': '5'}),
            ('subcategories', {'category': 'desserts', 'name': 'Cakes'}),
            ('items', {'name': 'Cheesecake', 'price': '8', 'is_new': 'yes'}),
            ('variations', {'item': 'cheesecake', 'name': 'Slice', 'price': '8'}),
            ('addons', {'item': 'Cheesecake', 'name': 'Berries', 'price': '1.5'}),
            ('menus', {'title': 'Dessert Menu', 'menu_type': 'Promotion', 'color_scheme': 'black & gold'}),
            ('menu_categories', {'menu': 'dessert-menu', 'category': 'Desserts', 'display_order': '1'}),
            ('placements', {'item': 'cheesecake', 'category': 'desserts', 'subcategory': 'Cakes',
                            'override_price': '7.50'}),
        ]
        for kind, row in steps:
            with self.subTest(kind=kind):
                result = im.apply(kind, make_csv(row))
                self.assertEqual(result.rows[0].action, 'new', result.rows[0].errors)

        desserts = MenuCategory.objects.get(slug='desserts')
        self.assertEqual(desserts.order, 5)
        self.assertTrue(desserts.is_active)  # blank cell on create → model default
        self.assertEqual(MenuSubCategory.objects.get(name='Cakes').slug, 'desserts-cakes')
        cake = MenuItem.objects.get(slug='cheesecake')
        self.assertEqual((cake.price, cake.is_new, cake.is_available), (Decimal('8.00'), True, True))
        self.assertEqual(Menu.objects.get(slug='dessert-menu').color_scheme, self.scheme)
        placement = MenuItemCategoryAssignment.objects.get(menu_item=cake)
        self.assertEqual((placement.subcategory.name, placement.override_price), ('Cakes', Decimal('7.50')))

    def test_update_changes_only_given_cells_and_blank_keeps(self):
        result = im.apply('items', make_csv({'slug': 'classic-burger', 'price': '15.50', 'short_description': ''}))
        row = result.rows[0]
        self.assertEqual(row.action, 'update')
        self.assertEqual(row.changes, {'price': ('14.00', '15.50')})
        self.burger.refresh_from_db()
        self.assertEqual(self.burger.price, Decimal('15.50'))
        self.assertEqual(self.burger.short_description, 'Half-pound patty')

    def test_dash_clears(self):
        im.apply('items', make_csv({'slug': 'classic-burger', 'short_description': '-', 'price': '-'}))
        self.burger.refresh_from_db()
        self.assertEqual((self.burger.short_description, self.burger.price), ('', None))
        im.apply('placements', make_csv({'item': 'lager', 'category': 'beer', 'subcategory': '-'}))
        self.assertIsNone(MenuItemCategoryAssignment.objects.get(menu_item=self.lager).subcategory)

    def test_dash_on_required_field_is_an_error(self):
        result = im.parse('items', make_csv({'slug': 'classic-burger', 'name': '-'}))
        self.assertFalse(result.ok)
        self.assertIn('name:', result.rows[0].errors[0])

    def test_match_by_slugified_name_when_slug_blank(self):
        result = im.parse('items', make_csv({'name': 'Classic Burger', 'price': '16'}))
        self.assertEqual(result.rows[0].action, 'update')

    def test_child_kinds_match_on_parent_and_name(self):
        result = im.parse('variations', make_csv({'item': 'lager', 'name': 'pint', 'price': '6.50'}))
        self.assertEqual(result.rows[0].action, 'update')
        result = im.parse('menu_categories', make_csv({'menu': 'food-menu', 'category': 'beer'}))
        self.assertEqual(result.rows[0].action, 'new')

    def test_unchanged_row(self):
        result = im.parse('items', make_csv({'slug': 'classic-burger', 'price': '14', 'is_vegan': 'no'}))
        self.assertEqual(result.rows[0].action, 'unchanged')

    def test_imports_never_delete(self):
        im.apply('items', make_csv({'name': 'New Item'}))
        self.assertTrue(MenuItem.objects.filter(slug='classic-burger').exists())
        self.assertTrue(MenuItem.objects.filter(slug='lager').exists())


class CellFormatTests(MenuFixture):
    def test_choice_accepts_code_or_label(self):
        for value in ('vegetarian', 'Vegetarian', 'VEGETARIAN'):
            with self.subTest(value=value):
                result = im.parse('items', make_csv({'slug': 'classic-burger', 'dietary_type': value}))
                self.assertEqual(result.rows[0].changes['dietary_type'][1], 'vegetarian')
        result = im.parse('items', make_csv({'slug': 'classic-burger', 'spice_level': 'Hot'}))
        self.assertEqual(result.rows[0].changes['spice_level'][1], '3')

    def test_bad_choice_lists_allowed_codes(self):
        result = im.parse('items', make_csv({'slug': 'classic-burger', 'dietary_type': 'keto'}))
        self.assertIn('not one of: none, vegetarian', result.rows[0].errors[0])

    def test_booleans(self):
        for yes in ('yes', 'Y', 'true', '1'):
            with self.subTest(value=yes):
                row = im.parse('items', make_csv({'slug': 'classic-burger', 'is_vegan': yes})).rows[0]
                self.assertEqual(row.changes['is_vegan'], ('no', 'yes'))
        for no in ('no', 'N', 'false', '0'):
            with self.subTest(value=no):
                row = im.parse('items', make_csv({'slug': 'classic-burger', 'is_available': no})).rows[0]
                self.assertEqual(row.changes['is_available'], ('yes', 'no'))
        self.assertIn('not yes/no', im.parse('items', make_csv({'slug': 'lager', 'is_vegan': 'maybe'})).rows[0].errors[0])

    def test_numbers_dates_and_times(self):
        result = im.apply('items', make_csv({
            'slug': 'lager', 'price': '6.5', 'calories': '180', 'available_from': '16:00', 'available_until': '23:30',
        }))
        self.assertTrue(result.ok)
        self.lager.refresh_from_db()
        self.assertEqual((self.lager.price, self.lager.calories), (Decimal('6.50'), 180))
        self.assertEqual(self.lager.available_from.strftime('%H:%M'), '16:00')
        bad = im.parse('items', make_csv({'slug': 'lager', 'price': '$6', 'available_from': '25:00', 'calories': '1.5'}))
        self.assertEqual(len(bad.rows[0].errors), 3)
        # 12-hour times, as Excel saves a time cell
        for cell in ('4pm', '4:00 PM', '4:00PM'):
            self.assertEqual(im.KINDS['items'].by_name['available_from'].canonical(cell), '16:00', cell)

    def test_menu_datetimes_are_eastern(self):
        im.apply('menus', make_csv({'slug': 'food-menu', 'active_from': '2026-11-01 17:00', 'valid_from': '2026-11-01'}))
        self.food.refresh_from_db()
        local = self.food.active_from.astimezone(ZoneInfo('America/New_York'))
        self.assertEqual((local.hour, local.minute), (17, 0))
        im.apply('menus', make_csv({'slug': 'food-menu', 'active_until': '2026-11-30'}))
        self.food.refresh_from_db()
        self.assertEqual(self.food.active_until.astimezone(ZoneInfo('America/New_York')).hour, 0)

    def test_description_is_plain_text_and_formatting_survives_round_trip(self):
        export = im.export_csv('items')
        self.assertIn('Our classic.', export)
        self.assertNotIn('<strong>', export)
        im.apply('items', export)
        self.burger.refresh_from_db()
        self.assertIn('<strong>classic</strong>', self.burger.description)  # unchanged → HTML kept

        im.apply('items', make_csv({'slug': 'classic-burger', 'description': 'Line one\nline two\n\nNew <para>'}))
        self.burger.refresh_from_db()
        self.assertEqual(self.burger.description, '<p>Line one<br>line two</p><p>New &lt;para&gt;</p>')

    def test_excel_encodings(self):
        text = make_csv({'slug': 'lager', 'short_description': 'Crisp — brewed in Pittsburgh, café style'})
        for data in (('﻿' + text).encode('utf-8'), text.encode('cp1252')):
            with self.subTest(encoding=data[:3]):
                decoded = im.read_csv_bytes(data)
                row = im.parse('items', decoded).rows[0]
                self.assertEqual(row.changes['short_description'][1], 'Crisp — brewed in Pittsburgh, café style')


class DateFormatTests(MenuFixture):
    """CSV dates are m/d/yyyy (CLAUDE.md, 2026-10-23); ISO still read; day-first never."""

    def menu_row(self, **cells):
        return im.parse('menus', make_csv({'slug': 'food-menu', **cells})).rows[0]

    def test_export_writes_m_d_yyyy_without_leading_zeros(self):
        Menu.objects.filter(pk=self.food.pk).update(
            valid_from=date(2027, 9, 8),
            active_from=datetime(2027, 9, 8, 17, 30, tzinfo=ZoneInfo('America/New_York')),
        )
        row = dict(zip([c.name for c in im.KINDS['menus'].columns],
                       next(r for r in im.export_rows('menus') if 'food-menu' in r)))
        self.assertEqual(row['valid_from'], '9/8/2027')
        self.assertEqual(row['active_from'], '9/8/2027 17:30')

    def test_m_d_yyyy_import_with_or_without_leading_zeros(self):
        for cell in ('9/18/2027', '09/18/2027'):
            with self.subTest(cell=cell):
                self.assertEqual(self.menu_row(valid_from=cell).changes['valid_from'], ('', '9/18/2027'))
        im.apply('menus', make_csv({'slug': 'food-menu', 'valid_from': '9/18/2027', 'active_from': '9/18/2027 17:30'}))
        self.food.refresh_from_db()
        self.assertEqual(self.food.valid_from, date(2027, 9, 18))
        local = self.food.active_from.astimezone(ZoneInfo('America/New_York'))
        self.assertEqual((local.month, local.day, local.hour, local.minute), (9, 18, 17, 30))

    def test_iso_still_accepted_and_older_exports_reimport_unchanged(self):
        im.apply('menus', make_csv({'slug': 'food-menu', 'valid_from': '9/18/2027', 'active_from': '9/18/2027 17:30'}))
        row = self.menu_row(valid_from='2027-09-18', active_from='2027-09-18 17:30')
        self.assertEqual(row.action, 'unchanged')

    def test_day_first_dates_are_refused(self):
        row = self.menu_row(valid_from='13/9/2027')
        self.assertEqual(row.errors, ['valid_from: "13/9/2027" is not a date (use M/D/YYYY)'])
        row = self.menu_row(active_from='13/9/2027 17:30')
        self.assertEqual(row.errors, ['active_from: "13/9/2027 17:30" is not a date and time (use M/D/YYYY HH:MM)'])

    def test_other_formats_refused(self):
        for cell in ('2/30/2027', '9/18/27', '20270918', 'Sept 18 2027'):
            with self.subTest(cell=cell):
                self.assertIn('use M/D/YYYY', self.menu_row(valid_from=cell).errors[0])

    def test_bare_date_in_a_datetime_column_means_midnight(self):
        im.apply('menus', make_csv({'slug': 'food-menu', 'active_until': '11/30/2026'}))
        self.food.refresh_from_db()
        local = self.food.active_until.astimezone(ZoneInfo('America/New_York'))
        self.assertEqual((local.month, local.day, local.hour), (11, 30, 0))


class FileErrorTests(MenuFixture):
    def test_unknown_column_refuses_file(self):
        result = im.parse('items', make_csv({'slug': 'lager', 'prise': '7'}))
        self.assertFalse(result.ok)
        self.assertIn('Unknown column(s): prise', result.errors[0])

    def test_unmatched_lookup_is_a_row_error_not_a_create(self):
        result = im.parse('placements', make_csv({'item': 'lager', 'category': 'wine'}))
        self.assertEqual(result.rows[0].errors, ['category: no category "wine"'])
        result = im.parse('menu_categories', make_csv({'menu': 'Food Menu', 'category': 'beer'}))
        self.assertIn('no menu (by slug) "Food Menu"', result.rows[0].errors[0])

    def test_ambiguous_name_asks_for_slug(self):
        MenuItem.objects.create(name='Lager', slug='lager1')
        result = im.parse('variations', make_csv({'item': 'Lager', 'name': 'Pitcher'}))
        self.assertIn('matches more than one item — use its slug', result.rows[0].errors[0])
        self.assertTrue(im.parse('variations', make_csv({'item': 'lager1', 'name': 'Pitcher', 'price': '20'})).ok)

    def test_subcategory_must_belong_to_the_placement_category(self):
        result = im.parse('placements', make_csv({'item': 'classic-burger', 'category': 'burgers', 'subcategory': 'On Tap'}))
        self.assertIn('no subcategory in "burgers"', result.rows[0].errors[0])

    def test_one_bad_row_refuses_the_whole_file(self):
        text = make_csv(
            {'slug': 'classic-burger', 'price': '20'},
            {'name': 'Brand New'},
            {'slug': 'lager', 'price': 'free'},
        )
        with self.assertRaises(im.ImportRefused):
            im.apply('items', text)
        self.burger.refresh_from_db()
        self.assertEqual(self.burger.price, Decimal('14.00'))
        self.assertFalse(MenuItem.objects.filter(name='Brand New').exists())

    def test_same_record_twice_in_a_file(self):
        result = im.parse('items', make_csv({'name': 'Wings'}, {'name': 'wings'}))
        self.assertIn('same record as line 2', result.rows[1].errors[0])

    def test_existing_placement_matches_rather_than_duplicating(self):
        result = im.parse('placements', make_csv({'item': 'lager', 'category': 'beer'}))
        self.assertEqual(result.rows[0].action, 'unchanged')

    def test_unique_slug_enforced_through_the_form(self):
        result = im.parse('items', make_csv({'name': 'Lager Special', 'slug': 'lager'}))
        # slug given → matches the existing lager, so it's an update of that record
        self.assertEqual(result.rows[0].action, 'update')
        result = im.parse('subcategories', make_csv({'category': 'burgers', 'name': 'Smash', 'slug': 'beer-on-tap'}))
        self.assertIn('slug:', result.rows[0].errors[0])
        self.assertIn('already exists', result.rows[0].errors[0])

    def test_slugified_title_matches_existing_menu(self):
        result = im.parse('menus', make_csv({'title': 'Food Menu'}))
        self.assertEqual(result.rows[0].action, 'unchanged')


class MenuRoleTests(MenuFixture):
    def test_same_role_twice_in_file_is_an_error(self):
        result = im.parse('menus', make_csv(
            {'slug': 'food-menu', 'role': 'default_food'},
            {'title': 'New Food', 'menu_type': 'food', 'role': 'Default Food Menu'},
        ))
        self.assertIn('also set on line 2', result.rows[1].errors[0])

    def test_taking_a_role_from_a_menu_not_in_the_file_is_noted_and_applied(self):
        result = im.apply('menus', make_csv({'title': 'Winter Food', 'menu_type': 'food', 'role': 'default_food'}))
        self.assertIn('takes Default Food Menu from "Food Menu"', result.rows[0].notes[0])
        self.food.refresh_from_db()
        self.assertEqual(self.food.role, 'none')
        self.assertEqual(Menu.objects.get(slug='winter-food').role, 'default_food')

    def test_swapping_roles_within_one_file(self):
        Menu.objects.create(title='Event Food', slug='event-food', menu_type='food', role='event_food')
        result = im.apply('menus', make_csv(
            {'slug': 'food-menu', 'role': 'event_food'},
            {'slug': 'event-food', 'role': 'default_food'},
        ))
        self.assertTrue(result.ok)
        self.assertEqual(dict(Menu.objects.values_list('slug', 'role')),
                         {'food-menu': 'event_food', 'event-food': 'default_food'})
