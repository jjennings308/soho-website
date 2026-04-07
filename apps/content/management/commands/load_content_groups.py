import csv
import os
from django.core.management.base import BaseCommand, CommandError
from apps.content.models import ContentGroup, ContentSlot


class Command(BaseCommand):
    help = (
        'Load ContentGroups and their ContentSlots from a CSV file. '
        'Safe to re-run — existing records are not overwritten.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Path to the CSV file to import'
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all current groups and their slots without making changes'
        )

    def handle(self, *args, **options):

        # ------------------------------------------------------------------
        # --list mode: report current state, no changes
        # ------------------------------------------------------------------
        if options['list']:
            groups = ContentGroup.objects.prefetch_related('slots').order_by('slug')
            if not groups.exists():
                self.stdout.write('No content groups found.')
                return
            for group in groups:
                self.stdout.write(self.style.MIGRATE_HEADING(f'\n{group.label} ({group.slug})'))
                slots = group.slots.order_by('order', 'slug')
                if not slots.exists():
                    self.stdout.write('    (no slots)')
                for slot in slots:
                    self.stdout.write(
                        f'    [{slot.component_type or "—":10}] order={slot.order}  '
                        f'{slot.slug:<40} {slot.label}'
                    )
            return

        # ------------------------------------------------------------------
        # Validate file path
        # ------------------------------------------------------------------
        csv_path = options['csv_file']
        if not os.path.isfile(csv_path):
            raise CommandError(f'File not found: {csv_path}')
        if not csv_path.lower().endswith('.csv'):
            raise CommandError(f'Expected a .csv file, got: {csv_path}')

        # ------------------------------------------------------------------
        # Parse and load
        # ------------------------------------------------------------------
        self.stdout.write(self.style.MIGRATE_HEADING(f'Loading content groups from {csv_path}...'))

        groups_created = 0
        groups_skipped = 0
        slots_created = 0
        slots_skipped = 0
        errors = []

        current_group = None
        line_num = 1  # header is line 1

        valid_component_types = {ct.value for ct in ContentSlot.ComponentType}

        try:
            with open(csv_path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                # Validate headers
                required_headers = {'type', 'slug', 'label'}
                missing = required_headers - set(reader.fieldnames or [])
                if missing:
                    raise CommandError(
                        f'CSV is missing required columns: {", ".join(sorted(missing))}\n'
                        f'Expected headers: type, slug, label, description, component_type, order'
                    )

                for row in reader:
                    line_num += 1
                    row_type = row.get('type', '').strip().lower()
                    slug = row.get('slug', '').strip()
                    label = row.get('label', '').strip()
                    description = row.get('description', '').strip()
                    component_type = row.get('component_type', '').strip().lower()
                    order_raw = row.get('order', '').strip()

                    # Skip blank rows
                    if not row_type and not slug:
                        continue

                    # Validate required fields
                    if not slug:
                        errors.append(f'Line {line_num}: missing slug — row skipped')
                        continue
                    if not label:
                        errors.append(f'Line {line_num}: missing label for slug "{slug}" — row skipped')
                        continue
                    if row_type not in ('group', 'slot'):
                        errors.append(f'Line {line_num}: invalid type "{row_type}" — must be "group" or "slot" — row skipped')
                        continue

                    # ----------------------------------------------------------
                    # Group row
                    # ----------------------------------------------------------
                    if row_type == 'group':
                        group, created = ContentGroup.objects.get_or_create(
                            slug=slug,
                            defaults={'label': label, 'description': description}
                        )
                        current_group = group
                        if created:
                            self.stdout.write(self.style.SUCCESS(f'  ✓ group created   {slug}'))
                            groups_created += 1
                        else:
                            self.stdout.write(f'  – group exists    {slug}')
                            groups_skipped += 1

                    # ----------------------------------------------------------
                    # Slot row
                    # ----------------------------------------------------------
                    elif row_type == 'slot':
                        if current_group is None:
                            errors.append(
                                f'Line {line_num}: slot "{slug}" has no preceding group row — row skipped'
                            )
                            continue

                        # Validate component_type if provided
                        if component_type and component_type not in valid_component_types:
                            errors.append(
                                f'Line {line_num}: invalid component_type "{component_type}" for slot "{slug}" '
                                f'— valid values: {", ".join(sorted(valid_component_types))} — row skipped'
                            )
                            continue

                        # Parse order, default to 0
                        try:
                            order = int(order_raw) if order_raw else 0
                        except ValueError:
                            errors.append(
                                f'Line {line_num}: invalid order value "{order_raw}" for slot "{slug}" '
                                f'— defaulting to 0'
                            )
                            order = 0

                        slot, created = ContentSlot.objects.get_or_create(
                            slug=slug,
                            defaults={
                                'label': label,
                                'description': description,
                                'group': current_group,
                                'component_type': component_type,
                                'order': order,
                            }
                        )
                        if created:
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'    ✓ slot created    {slug:<40} [{component_type or "—"}]'
                                )
                            )
                            slots_created += 1
                        else:
                            self.stdout.write(
                                f'    – slot exists     {slug:<40} [{component_type or "—"}]'
                            )
                            slots_skipped += 1

        except FileNotFoundError:
            raise CommandError(f'File not found: {csv_path}')
        except UnicodeDecodeError:
            raise CommandError(f'Could not read file — ensure it is saved as UTF-8: {csv_path}')

        # ------------------------------------------------------------------
        # Summary
        # ------------------------------------------------------------------
        self.stdout.write('')
        if errors:
            self.stdout.write(self.style.WARNING(f'{len(errors)} warning(s):'))
            for err in errors:
                self.stdout.write(self.style.WARNING(f'  ⚠ {err}'))
            self.stdout.write('')

        self.stdout.write(
            self.style.SUCCESS(
                f'Done. '
                f'Groups: {groups_created} created, {groups_skipped} already existed. '
                f'Slots: {slots_created} created, {slots_skipped} already existed.'
            )
        )
