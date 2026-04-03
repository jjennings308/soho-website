from django.core.management.base import BaseCommand
from apps.core.models import Banner, BannerButton


BANNERS = [
    {
        'slug': 'hero',
        'label': 'Home Hero Banner',
        'title': 'Welcome to Soho',
        'content': 'Craft cocktails and seasonal plates.',
        'bg_color': 'bg-primary',
        'text_color': 'text-primary',
        'image_opacity': '0.40',
        'image_only': False,
        'buttons': [],
    },
    {
        'slug': 'grubhub',
        'label': 'Order Online Banner',
        'title': 'Order Online',
        'content': '',
        'bg_color': 'bg-secondary',
        'text_color': 'text-primary',
        'image_opacity': '0.40',
        'image_only': False,
        'buttons': [
            {
                'label': 'Order Grubhub Directly from SoHo',
                'href': 'http://menus.fyi/11489616',
                'bg_color': 'bg-secondary',
                'text_color': 'gold-bright',
                'order': 0,
            },
        ],
    },
]


class Command(BaseCommand):
    help = 'Seeds initial Banner and BannerButton records. Safe to re-run.'

    def handle(self, *args, **options):
        for data in BANNERS:
            buttons = data.pop('buttons')
            banner, created = Banner.objects.get_or_create(
                slug=data['slug'],
                defaults=data,
            )
            action = 'Created' if created else 'Already exists'
            self.stdout.write(f"{action}: Banner '{banner.label}'")

            for btn_data in buttons:
                btn, btn_created = BannerButton.objects.get_or_create(
                    banner=banner,
                    label=btn_data['label'],
                    defaults=btn_data,
                )
                btn_action = 'Created' if btn_created else 'Already exists'
                self.stdout.write(f"  {btn_action}: Button '{btn.label}'")

        self.stdout.write(self.style.SUCCESS('load_banners complete.'))