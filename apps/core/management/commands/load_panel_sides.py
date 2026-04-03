from django.core.management.base import BaseCommand
from apps.core.models import PanelSide
from apps.content.models import ContentSlot


PANEL_SIDES = [
    # ── Image panels ──────────────────────────────────────────────────────────
    {
        'slug': 'front-door-image',
        'label': 'Front Door Image Panel',
        'mode': 'image',
        'bg_color': 'bg-secondary',
        'image_fallback_url': '/static/img/front_door.webp',
    },
    {
        'slug': 'catering-image',
        'label': 'Catering Image Panel',
        'mode': 'image',
        'bg_color': 'bg-secondary',
        'image_fallback_url': '/static/img/front_door.webp',
    },
    {
        'slug': 'gameday-image',
        'label': 'Game Day Image Panel',
        'mode': 'image',
        'bg_color': 'bg-secondary',
        'image_fallback_url': '/static/img/steelers_game.png',
    },

    # ── Text panels ───────────────────────────────────────────────────────────
    {
        'slug': 'about-text',
        'label': 'About Text Panel',
        'mode': 'text',
        'bg_color': 'bg-secondary',
        'text_color': 'text-secondary',
        'content_slot_slug': 'about_short',
        'button_label': 'More About Us',
        'button_href': '/about',
        'button_bg_color': 'steeler-gold',
        'button_text_color': 'steeler-black',
    },
    {
        'slug': 'catering-text',
        'label': 'Catering Text Panel',
        'mode': 'text',
        'bg_color': 'bg-primary',
        'text_color': 'text-primary',
        'content_slot_slug': 'catering_body',
        'button_label': 'Call Now!',
        'button_href': 'tel:(412) 321-7646',
        'button_bg_color': 'bg-secondary',
        'button_text_color': 'text-secondary',
    },
    {
        'slug': 'gameday-text',
        'label': 'Game Day Text Panel',
        'mode': 'text',
        'bg_color': 'steeler-black',
        'text_color': 'text-secondary',
        'content_slot_slug': 'gameday_body',
    },
]


class Command(BaseCommand):
    help = 'Seeds initial PanelSide records. Safe to re-run.'

    def handle(self, *args, **options):
        for data in PANEL_SIDES:
            content_slot_slug = data.pop('content_slot_slug', None)

            content_slot = None
            if content_slot_slug:
                try:
                    content_slot = ContentSlot.objects.get(slug=content_slot_slug)
                except ContentSlot.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  Warning: ContentSlot '{content_slot_slug}' not found — "
                            f"run load_content_slots first."
                        )
                    )

            panel, created = PanelSide.objects.get_or_create(
                slug=data['slug'],
                defaults={**data, 'content_slot': content_slot},
            )
            action = 'Created' if created else 'Already exists'
            self.stdout.write(f"{action}: PanelSide '{panel.label}'")

        self.stdout.write(self.style.SUCCESS('load_panel_sides complete.'))