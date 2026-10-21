from decimal import Decimal

from apps.menu import whole_menu as wm
from apps.menu.models import (
    Menu, MenuCategory, MenuCategoryAssignment, MenuItem, MenuItemCategoryAssignment, MenuSubCategory,
)

from .test_importers import MenuFixture, make_csv


def counts(result):
    return {s.kind: (s.result.count('new'), s.result.count('update')) for s in result.stages}


class WholeMenuRoundTripTests(MenuFixture):
    def test_export_then_import_changes_nothing(self):
        result = wm.parse_sheet(wm.export_csv())
        self.assertTrue(result.ok, (result.errors, result.row_errors))
        self.assertEqual(result.count('new') + result.count('update'), 0)
        self.assertEqual([s.kind for s in result.stages], wm.STAGES)

    def test_export_has_one_row_per_placement_on_each_menu(self):
        rows = list(wm.export_rows())
        # food-menu shows burgers, which has one placement (classic burger); beer is on no menu.
        self.assertEqual(len(rows), 1)
        row = dict(zip(wm.COLUMNS, rows[0]))
        self.assertEqual((row['menu'], row['category'], row['item'], row['price']),
                         ('food-menu', 'burgers', 'classic-burger', '14.00'))

    def test_template_has_columns_and_example(self):
        header, example = [line.split(',') for line in wm.template_csv().lstrip('﻿').strip().splitlines()]
        self.assertEqual(header, wm.COLUMNS)
        self.assertEqual(example[0], 'food-menu')


class WholeMenuCreateUpdateTests(MenuFixture):
    def test_one_row_creates_menu_category_item_and_links(self):
        result = wm.apply_sheet(make_csv({
            'menu': 'Brunch', 'menu_type': 'Food', 'category': 'Eggs', 'item': 'Shakshuka',
            'price': '13', 'short_description': 'Baked eggs, tomato', 'vegan': 'no', 'featured': 'yes',
        }))
        self.assertTrue(result.ok)
        self.assertEqual(counts(result), {'categories': (1, 0), 'items': (1, 0), 'menus': (1, 0),
                                          'menu_categories': (1, 0), 'placements': (1, 0)})
        brunch = Menu.objects.get(slug='brunch')
        self.assertEqual(brunch.menu_type, 'food')
        item = MenuItem.objects.get(slug='shakshuka')
        self.assertEqual((item.price, item.is_featured), (Decimal('13.00'), True))
        link = MenuCategoryAssignment.objects.get(menu=brunch)
        self.assertEqual((link.category.slug, link.display_order), ('eggs', 1))
        self.assertEqual(MenuItemCategoryAssignment.objects.get(menu_item=item).category.slug, 'eggs')

    def test_new_menu_needs_menu_type(self):
        result = wm.parse_sheet(make_csv({'menu': 'Brunch', 'category': 'burgers', 'item': 'classic-burger'}))
        self.assertEqual(result.row_errors, {2: ['menu_type: required to create the new menu "Brunch"']})

    def test_update_by_name_with_blank_keeping_values(self):
        result = wm.apply_sheet(make_csv({'menu': 'Food Menu', 'category': 'Burgers', 'item': 'Classic Burger',
                                          'price': '15', 'short_description': ''}))
        self.assertEqual(counts(result)['items'], (0, 1))
        self.burger.refresh_from_db()
        self.assertEqual((self.burger.price, self.burger.short_description), (Decimal('15.00'), 'Half-pound patty'))

    def test_special_price_note_and_shown_set_the_placement(self):
        wm.apply_sheet(make_csv({'menu': 'food-menu', 'category': 'burgers', 'item': 'classic-burger',
                                 'special_price': '12', 'note': 'Lunch only', 'shown': 'no'}))
        placement = MenuItemCategoryAssignment.objects.get(menu_item=self.burger, category=self.burgers)
        self.assertEqual((placement.override_price, placement.note, placement.is_active),
                         (Decimal('12.00'), 'Lunch only', False))
        self.burger.refresh_from_db()
        self.assertEqual(self.burger.price, Decimal('14.00'))  # item's own price untouched

    def test_new_links_go_after_existing_ones(self):
        MenuItemCategoryAssignment.objects.filter(menu_item=self.burger).update(order=7)
        wm.apply_sheet(make_csv(
            {'menu': 'food-menu', 'category': 'beer', 'item': 'lager'},
            {'menu': 'food-menu', 'category': 'burgers', 'item': 'Veggie Burger'},
            {'menu': 'food-menu', 'category': 'burgers', 'item': 'Turkey Burger', 'item_order': '3'},
        ))
        self.assertEqual(MenuCategoryAssignment.objects.get(menu=self.food, category=self.beer).display_order, 2)
        orders = dict(MenuItemCategoryAssignment.objects.filter(category=self.burgers)
                      .values_list('menu_item__slug', 'order'))
        self.assertEqual(orders, {'classic-burger': 7, 'veggie-burger': 8, 'turkey-burger': 3})

    def test_blank_order_keeps_existing_order(self):
        MenuCategoryAssignment.objects.filter(menu=self.food).update(display_order=5)
        wm.apply_sheet(make_csv({'menu': 'food-menu', 'category': 'burgers', 'item': 'classic-burger', 'price': '15'}))
        self.assertEqual(MenuCategoryAssignment.objects.get(menu=self.food).display_order, 5)

    def test_subcategory_by_name_within_category(self):
        result = wm.apply_sheet(make_csv({'menu': 'food-menu', 'category': 'beer', 'item': 'lager',
                                          'subcategory': 'On Tap'}))
        self.assertTrue(result.ok)
        self.assertEqual(MenuItemCategoryAssignment.objects.get(menu_item=self.lager).subcategory, self.on_tap)


class WholeMenuErrorTests(MenuFixture):
    def test_repeated_values_must_agree(self):
        result = wm.parse_sheet(make_csv(
            {'menu': 'food-menu', 'category': 'burgers', 'item': 'classic-burger', 'price': '14'},
            {'menu': 'food-menu', 'category': 'beer', 'item': 'classic-burger', 'price': '14.00'},  # same value
            {'menu': 'food-menu', 'category': 'beer', 'item': 'classic-burger', 'price': '16'},
        ))
        self.assertEqual(result.row_errors, {4: ['price: "16" here but "14" on line 2']})

    def test_blank_never_conflicts(self):
        result = wm.parse_sheet(make_csv(
            {'menu': 'food-menu', 'category': 'burgers', 'item': 'classic-burger', 'price': '14'},
            {'menu': 'food-menu', 'category': 'beer', 'item': 'classic-burger', 'price': ''},
        ))
        self.assertTrue(result.ok)

    def test_late_stage_error_saves_nothing_and_names_sheet_line(self):
        text = make_csv(
            {'menu': 'New Menu', 'menu_type': 'promo', 'category': 'New Cat', 'item': 'New Thing'},
            {'menu': 'food-menu', 'category': 'burgers', 'item': 'classic-burger', 'subcategory': 'No Such'},
        )
        preview = wm.parse_sheet(text)
        self.assertFalse(preview.ok)
        self.assertEqual(preview.stopped_at, 'placements')
        bad = [r for s in preview.stages for r in s.result.rows if r.errors]
        self.assertEqual(bad[0].sheet_lines, [3])
        self.assertIn('no subcategory in "burgers"', bad[0].errors[0])
        with self.assertRaises(wm.SheetRefused):
            wm.apply_sheet(text)
        self.assertFalse(Menu.objects.filter(slug='new-menu').exists())
        self.assertFalse(MenuCategory.objects.filter(slug='new-cat').exists())
        self.assertFalse(MenuItem.objects.filter(slug='new-thing').exists())

    def test_preview_saves_nothing(self):
        result = wm.parse_sheet(make_csv({'menu': 'Brunch', 'menu_type': 'food', 'category': 'Eggs', 'item': 'Toast'}))
        self.assertTrue(result.ok)
        self.assertEqual(result.count('new'), 5)
        self.assertFalse(Menu.objects.filter(slug='brunch').exists())
        self.assertFalse(MenuItem.objects.filter(slug='toast').exists())

    def test_file_level_errors(self):
        self.assertIn('Unknown column(s): prise', wm.parse_sheet('menu,category,item,prise\n').errors[0])
        self.assertIn('Missing required column(s): item', wm.parse_sheet('menu,category\nx,y\n').errors[0])

    def test_key_cells_required_and_ambiguous_names_refused(self):
        MenuItem.objects.create(name='Lager', slug='lager1')
        result = wm.parse_sheet(make_csv(
            {'menu': 'food-menu', 'category': '', 'item': 'classic-burger'},
            {'menu': 'food-menu', 'category': 'beer', 'item': 'Lager'},
        ))
        self.assertEqual(result.row_errors[2], ['category: required'])
        self.assertIn('matches more than one — use its slug', result.row_errors[3][0])

    def test_cell_errors_are_reported_through_the_engine(self):
        result = wm.parse_sheet(make_csv({'menu': 'food-menu', 'category': 'burgers', 'item': 'classic-burger',
                                          'price': 'cheap'}))
        self.assertEqual(result.stopped_at, 'items')
        row = next(r for r in result.stages[1].result.rows if r.errors)
        self.assertEqual((row.sheet_lines, row.errors), ([2], ['price: "cheap" is not a number (use e.g. 12.50, no currency sign)']))
