from django.core.management.base import BaseCommand
from apps.core.models import PanelSide


PANEL_SIDES = [
    # ── Image panels ──────────────────────────────────────────────────────────
    {
        'slug': 'front-door-image',
        'label': 'Front Door Image Panel',
        'component': 'image',
        'bg_color': 'bg-secondary',
        'image_fallback_url': '/static/img/front_door.webp',
    },
    {
        'slug': 'catering-image',
        'label': 'Catering Image Panel',
        'component': 'image',
        'bg_color': 'bg-secondary',
        'image_fallback_url': '/static/img/front_door.webp',
    },
    {
        'slug': 'gameday-image',
        'label': 'Game Day Image Panel',
        'component': 'image',
        'bg_color': 'bg-secondary',
        'image_fallback_url': '/static/img/steelers_game.png',
    },

    # ── Content panels ────────────────────────────────────────────────────────
    {
        'slug': 'about-text',
        'label': 'About Text Panel',
        'component': 'content',
        'bg_color': 'bg-secondary',
        'text_color': 'text-secondary',
    },
    {
        'slug': 'catering-text',
        'label': 'Catering Text Panel',
        'component': 'content',
        'bg_color': 'bg-primary',
        'text_color': 'text-primary',
    },
    {
        'slug': 'gameday-text',
        'label': 'Game Day Text Panel',
        'component': 'content',
        'bg_color': 'bg-primary',
        'text_color': 'text-secondary',
    },
]


class Command(BaseCommand):
    help = 'Seeds initial PanelSide records. Safe to re-run.'

    def handle(self, *args, **options):
        for data in PANEL_SIDES:
            panel, created = PanelSide.objects.get_or_create(
                slug=data['slug'],
                defaults=data,
            )
            action = 'Created' if created else 'Already exists'
            self.stdout.write(f"{action}: PanelSide '{panel.label}'")

        self.stdout.write(self.style.SUCCESS('load_panel_sides complete.'))