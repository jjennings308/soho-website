import io
import tempfile
from decimal import Decimal
from pathlib import Path

from django.core.management import CommandError, call_command

from apps.menu import importers as im

from .test_importers import MenuFixture, make_csv


class CommandTests(MenuFixture):
    def test_export_then_dry_run_then_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            call_command('export_menu', tmp, stdout=io.StringIO())
            files = sorted(p.name for p in Path(tmp).iterdir())
            self.assertEqual(files, ['0-whole-menu.csv'] + [f'{n}-{k}.csv' for n, k in enumerate(im.KIND_ORDER, start=1)])

            path = Path(tmp) / 'edit.csv'
            path.write_text(make_csv({'slug': 'lager', 'price': '7'}), encoding='utf-8')
            out = io.StringIO()
            call_command('import_menu', 'items', str(path), stdout=out)
            self.assertIn('price: 6.00 → 7.00', out.getvalue())
            self.assertIn('Dry run', out.getvalue())
            self.lager.refresh_from_db()
            self.assertEqual(self.lager.price, Decimal('6.00'))

            call_command('import_menu', 'items', str(path), '--apply', stdout=io.StringIO())
            self.lager.refresh_from_db()
            self.assertEqual(self.lager.price, Decimal('7.00'))

    def test_errors_fail_the_command_and_save_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'bad.csv'
            path.write_text(make_csv({'slug': 'lager', 'price': 'cheap'}), encoding='utf-8')
            out = io.StringIO()
            with self.assertRaises(CommandError):
                call_command('import_menu', 'items', str(path), '--apply', stdout=out)
            self.assertIn('price: "cheap" is not a number', out.getvalue())


class WholeMenuCommandTests(MenuFixture):
    def test_dry_run_then_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'sheet.csv'
            path.write_text(make_csv({'menu': 'food-menu', 'category': 'burgers', 'item': 'classic-burger',
                                      'price': '16'}), encoding='utf-8')
            out = io.StringIO()
            call_command('import_menu', 'whole_menu', str(path), stdout=out)
            self.assertIn('— items —', out.getvalue())
            self.assertIn('line 2  UPDATE   Classic Burger', out.getvalue())
            self.burger.refresh_from_db()
            self.assertEqual(self.burger.price, Decimal('14.00'))
            call_command('import_menu', 'whole_menu', str(path), '--apply', stdout=io.StringIO())
            self.burger.refresh_from_db()
            self.assertEqual(self.burger.price, Decimal('16.00'))

    def test_errors_fail_the_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'sheet.csv'
            path.write_text(make_csv({'menu': 'Brand New', 'category': 'burgers', 'item': 'classic-burger'}),
                            encoding='utf-8')
            out = io.StringIO()
            with self.assertRaises(CommandError):
                call_command('import_menu', 'whole_menu', str(path), '--apply', stdout=out)
            self.assertIn('menu_type: required', out.getvalue())
