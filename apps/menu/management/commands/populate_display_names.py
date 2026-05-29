"""
One-time management command to copy name/title → display_name for
Menu, MenuCategory, and MenuSubCategory records where display_name is blank.

Place at:
    apps/menu/management/commands/populate_display_names.py

Usage:
    python manage.py populate_display_names
    python manage.py populate_display_names --dry-run
    python manage.py populate_display_names --model=menu
    python manage.py populate_display_names --model=category
    python manage.py populate_display_names --model=subcategory
"""

from django.core.management.base import BaseCommand
from apps.menu.models import Menu, MenuCategory, MenuSubCategory


class Command(BaseCommand):
    help = (
        'One-time: copies name/title to display_name for Menu, MenuCategory, '
        'and MenuSubCategory where display_name is blank. Safe to re-run.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without saving anything.',
        )
        parser.add_argument(
            '--model',
            choices=['menu', 'category', 'subcategory', 'all'],
            default='all',
            help='Which model to populate. Default: all.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        model_choice = options['model']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no changes will be saved.\n'))

        # (label, Model, source_field, order_by_field)
        # Menu uses 'title' as its human name field — not 'name'
        # MenuCategory and MenuSubCategory use 'name'
        all_targets = [
            ('menu',        'Menu',            Menu,            'title', 'title'),
            ('category',    'MenuCategory',    MenuCategory,    'name',  'name'),
            ('subcategory', 'MenuSubCategory', MenuSubCategory, 'name',  'name'),
        ]

        targets = [
            t for t in all_targets
            if model_choice == 'all' or model_choice == t[0]
        ]

        total_updated = 0

        for _key, label, Model, source_field, order_field in targets:
            self.stdout.write(f'\n{label} (copying from: {source_field!r}):')

            qs = Model.objects.filter(display_name='').order_by(order_field)
            count = qs.count()

            if count == 0:
                self.stdout.write('  All records already have a display_name — skipping.')
                continue

            self.stdout.write(f'  {count} records with blank display_name:')

            updated = 0
            for obj in qs:
                source_value = getattr(obj, source_field, '') or ''
                self.stdout.write(
                    f'    [{obj.pk}] {source_value!r} → display_name'
                )
                if not dry_run:
                    obj.display_name = source_value
                    obj.save(update_fields=['display_name'])
                updated += 1

            if dry_run:
                self.stdout.write(f'  Would update {updated} records.')
            else:
                self.stdout.write(self.style.SUCCESS(f'  Updated {updated} records.'))

            total_updated += updated

        self.stdout.write('')
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN complete. Would update {total_updated} records total. '
                    f'Run without --dry-run to apply.'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Done. {total_updated} records updated across {len(targets)} model(s).'
                )
            )
