from django.core.management.base import BaseCommand
from django.db import transaction
from apps.core.models import Banner, BannerButton, PanelSide
from apps.content.models import ContentGroup, ContentSlot, ContentBlock


class Command(BaseCommand):
    help = (
        'Migrates legacy Banner.title/content/buttons and PanelSide.title/button_label '
        'into ContentGroups. Safe to re-run. Use --dry-run to preview without saving.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would happen without saving anything.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no changes will be saved.\n'))
            with transaction.atomic():
                banners_migrated, panels_migrated = self._run_migration()
                transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING('\n[DRY RUN] All changes rolled back.'))
        else:
            banners_migrated, panels_migrated = self._run_migration()

        self.stdout.write(
            self.style.SUCCESS(
                f'\nDone. {banners_migrated} banner(s) migrated, '
                f'{panels_migrated} panel(s) migrated.'
            )
        )

    def _run_migration(self):
        banners_migrated = 0
        panels_migrated = 0

        # ── Banners ──────────────────────────────────────────────────────────
        self.stdout.write('── Banners ──────────────────────────────────────────')

        banner_ids_with_buttons = set(
            BannerButton.objects.values_list('banner_id', flat=True)
        )
        banners = (
            Banner.objects
            .select_related('content_group')
            .prefetch_related('buttons')
            .order_by('slug')
        )

        for banner in banners:
            has_legacy = (
                banner.title.strip()
                or banner.content.strip()
                or banner.pk in banner_ids_with_buttons
            )
            if not has_legacy:
                continue

            self.stdout.write(f'\nBanner "{banner.label}" (slug={banner.slug})')

            if banner.content_group_id:
                self.stdout.write(
                    f'  [!] SKIP — content_group already assigned '
                    f'(pk={banner.content_group_id}, slug="{banner.content_group.slug}")'
                )
                continue

            # 1. ContentGroup
            group, created = ContentGroup.objects.get_or_create(
                slug=banner.slug,
                defaults={
                    'label': banner.label,
                    'description': 'Migrated from Banner legacy fields.',
                },
            )
            self._log('ContentGroup', created, group.slug, indent=1)

            # 2. Title slot + block
            if banner.title.strip():
                slot, slot_created = ContentSlot.objects.get_or_create(
                    slug=f'{banner.slug}-title',
                    defaults={
                        'label': f'{banner.label} — Title',
                        'group': group,
                        'component_type': ContentSlot.ComponentType.TITLE,
                        'order': 1,
                    },
                )
                self._log('ContentSlot[title]', slot_created, slot.slug, indent=2)
                block, block_created = ContentBlock.objects.get_or_create(
                    slot=slot,
                    label='Migrated',
                    defaults={'body': banner.title.strip(), 'is_active': True},
                )
                self._log('ContentBlock', block_created,
                          f'body="{banner.title[:60]}"', indent=3)

            # 3. Body slot + block
            if banner.content.strip():
                slot, slot_created = ContentSlot.objects.get_or_create(
                    slug=f'{banner.slug}-body',
                    defaults={
                        'label': f'{banner.label} — Body',
                        'group': group,
                        'component_type': ContentSlot.ComponentType.BODY,
                        'order': 2,
                    },
                )
                self._log('ContentSlot[body]', slot_created, slot.slug, indent=2)
                block, block_created = ContentBlock.objects.get_or_create(
                    slot=slot,
                    label='Migrated',
                    defaults={'body': banner.content.strip(), 'is_active': True},
                )
                self._log('ContentBlock', block_created,
                          f'body="{banner.content[:60]}"', indent=3)

            # 4. Button slots + blocks (all buttons, ordered)
            for btn in banner.buttons.all().order_by('order'):
                slot_slug = f'{banner.slug}-button-{btn.order + 1}'
                slot, slot_created = ContentSlot.objects.get_or_create(
                    slug=slot_slug,
                    defaults={
                        'label': f'{banner.label} — Button: {btn.label}',
                        'group': group,
                        'component_type': ContentSlot.ComponentType.BUTTON,
                        'order': 10 + btn.order,
                    },
                )
                self._log('ContentSlot[button]', slot_created, slot.slug, indent=2)
                block, block_created = ContentBlock.objects.get_or_create(
                    slot=slot,
                    label='Migrated',
                    defaults={
                        'button_label': btn.label,
                        'button_url': btn.href,
                        'is_active': True,
                    },
                )
                self._log('ContentBlock', block_created,
                          f'button_label="{btn.label}" button_url="{btn.href}"',
                          indent=3)

            # 5. Assign group to banner
            banner.content_group = group
            banner.save(update_fields=['content_group'])
            self.stdout.write(f'  → Assigned ContentGroup "{group.slug}" to banner')
            banners_migrated += 1

        # ── PanelSides ───────────────────────────────────────────────────────
        self.stdout.write('\n── PanelSides ───────────────────────────────────────')

        panels = (
            PanelSide.objects
            .select_related('content_group', 'content_slot')
            .order_by('slug')
        )

        for panel in panels:
            has_legacy = (
                panel.title.strip()
                or panel.button_label.strip()
                or panel.content_slot_id
            )
            if not has_legacy:
                continue

            self.stdout.write(f'\nPanelSide "{panel.label}" (slug={panel.slug})')

            if panel.content_group_id:
                self.stdout.write(
                    f'  [!] SKIP — content_group already assigned '
                    f'(pk={panel.content_group_id}, slug="{panel.content_group.slug}")'
                )
                continue

            # 1. ContentGroup
            group, created = ContentGroup.objects.get_or_create(
                slug=panel.slug,
                defaults={
                    'label': panel.label,
                    'description': 'Migrated from PanelSide legacy fields.',
                },
            )
            self._log('ContentGroup', created, group.slug, indent=1)

            # 2. Title slot + block
            if panel.title.strip():
                slot, slot_created = ContentSlot.objects.get_or_create(
                    slug=f'{panel.slug}-title',
                    defaults={
                        'label': f'{panel.label} — Title',
                        'group': group,
                        'component_type': ContentSlot.ComponentType.TITLE,
                        'order': 1,
                    },
                )
                self._log('ContentSlot[title]', slot_created, slot.slug, indent=2)
                block, block_created = ContentBlock.objects.get_or_create(
                    slot=slot,
                    label='Migrated',
                    defaults={'body': panel.title.strip(), 'is_active': True},
                )
                self._log('ContentBlock', block_created,
                          f'body="{panel.title[:60]}"', indent=3)

            # 3. Body from content_slot → new body slot + block
            if panel.content_slot_id:
                active_block = panel.content_slot.get_active_block()
                if active_block and active_block.body.strip():
                    slot, slot_created = ContentSlot.objects.get_or_create(
                        slug=f'{panel.slug}-body',
                        defaults={
                            'label': f'{panel.label} — Body',
                            'group': group,
                            'component_type': ContentSlot.ComponentType.BODY,
                            'order': 2,
                        },
                    )
                    self._log('ContentSlot[body]', slot_created, slot.slug, indent=2)
                    block, block_created = ContentBlock.objects.get_or_create(
                        slot=slot,
                        label='Migrated',
                        defaults={'body': active_block.body, 'is_active': True},
                    )
                    self._log('ContentBlock', block_created,
                              f'body="{active_block.body[:60]}"', indent=3)
                else:
                    src_slug = panel.content_slot.slug
                    self.stdout.write(
                        f'  [?] content_slot "{src_slug}" has no active block '
                        f'with body — body slot skipped'
                    )

            # 4. Button slot + block
            if panel.button_label.strip() and panel.button_href.strip():
                slot, slot_created = ContentSlot.objects.get_or_create(
                    slug=f'{panel.slug}-button',
                    defaults={
                        'label': f'{panel.label} — Button',
                        'group': group,
                        'component_type': ContentSlot.ComponentType.BUTTON,
                        'order': 3,
                    },
                )
                self._log('ContentSlot[button]', slot_created, slot.slug, indent=2)
                block, block_created = ContentBlock.objects.get_or_create(
                    slot=slot,
                    label='Migrated',
                    defaults={
                        'button_label': panel.button_label.strip(),
                        'button_url': panel.button_href.strip(),
                        'is_active': True,
                    },
                )
                self._log('ContentBlock', block_created,
                          f'button_label="{panel.button_label}" '
                          f'button_url="{panel.button_href}"',
                          indent=3)

            # 5. Assign group to panel
            panel.content_group = group
            panel.save(update_fields=['content_group'])
            self.stdout.write(f'  → Assigned ContentGroup "{group.slug}" to panel')
            panels_migrated += 1

        return banners_migrated, panels_migrated

    def _log(self, kind, created, detail, indent=1):
        prefix = '  ' * indent
        symbol = '[+]' if created else '[=]'
        action = 'Created   ' if created else 'Exists    '
        self.stdout.write(f'{prefix}{symbol} {action} {kind} — {detail}')
