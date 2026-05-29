"""
One-time management command to copy `name` → `display_name` for
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
        'One-time: copies name → display_name for Menu, MenuCategory, '
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

        targets = []
        if model_choice in ('menu', 'all'):
            targets.append(('Menu', Menu))
        if model_choice in ('category', 'all'):
            targets.append(('MenuCategory', MenuCategory))
        if model_choice in ('subcategory', 'all'):
            targets.append(('MenuSubCategory', MenuSubCategory))

        total_updated = 0

        for label, Model in targets:
            self.stdout.write(f'\n{label}:')

            # Only touch records where display_name is blank
            qs = Model.objects.filter(display_name='').order_by('name')
            count = qs.count()

            if count == 0:
                self.stdout.write('  All records already have a display_name — skipping.')
                continue

            self.stdout.write(f'  {count} records with blank display_name:')

            updated = 0
            for obj in qs:
                self.stdout.write(f'    [{obj.pk}] {obj.name!r} → display_name = {obj.name!r}')
                if not dry_run:
                    obj.display_name = obj.name
                    obj.save(update_fields=['display_name'])
                updated += 1

            if dry_run:
                self.stdout.write(f'  Would update {updated} records.')
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'  Updated {updated} records.')
                )

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
