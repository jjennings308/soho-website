from django.core.management.base import BaseCommand
from apps.core.models import Banner


BANNERS = [
    {
        'slug': 'hero',
        'label': 'Home Hero Banner',
        'bg_color': 'bg-primary',
        'text_color': 'text-primary',
        'image_opacity': '0.40',
        'image_only': False,
    },
    {
        'slug': 'grubhub',
        'label': 'Order Online Banner',
        'bg_color': 'bg-secondary',
        'text_color': 'text-primary',
        'image_opacity': '0.40',
        'image_only': False,
    },
]


class Command(BaseCommand):
    help = 'Seeds initial Banner records. Safe to re-run.'

    def handle(self, *args, **options):
        for data in BANNERS:
            banner, created = Banner.objects.get_or_create(
                slug=data['slug'],
                defaults=data,
            )
            action = 'Created' if created else 'Already exists'
            self.stdout.write(f"{action}: Banner '{banner.label}'")

        self.stdout.write(self.style.SUCCESS('load_banners complete.'))