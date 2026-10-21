from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.menu import whole_menu
from apps.menu.importers import KIND_ORDER, export_csv, export_rows


class Command(BaseCommand):
    help = (
        'Export the menu as one CSV per kind, in import order and the same '
        'columns import_menu reads (edit and re-import).'
    )

    def add_arguments(self, parser):
        parser.add_argument('dir', nargs='?', help='Output folder (default: menu-export-YYYY-MM-DD)')

    def handle(self, *args, **options):
        out_dir = Path(options['dir'] or f'menu-export-{timezone.localdate().isoformat()}')
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / '0-whole-menu.csv'
        path.write_text(whole_menu.export_csv(), encoding='utf-8')
        rows = sum(1 for _ in whole_menu.export_rows())
        self.stdout.write(f'{path}  ({rows} row{"" if rows == 1 else "s"}) — everything on one sheet')
        for n, kind in enumerate(KIND_ORDER, start=1):
            path = out_dir / f'{n}-{kind}.csv'
            text = export_csv(kind)
            path.write_text(text, encoding='utf-8')
            rows = sum(1 for _ in export_rows(kind))
            self.stdout.write(f'{path}  ({rows} row{"" if rows == 1 else "s"})')
        self.stdout.write(self.style.SUCCESS(f'Exported {len(KIND_ORDER) + 1} files to {out_dir}/'))
