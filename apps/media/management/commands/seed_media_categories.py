"""
Management command to seed the standard MediaCategory records.

Usage:
    python manage.py seed_media_categories

Safe to re-run — uses get_or_create throughout. Running again will not
duplicate categories. Existing categories are left untouched (name, description,
and is_gallery_visible are only set on creation, not overwritten on subsequent runs).
"""

from django.core.management.base import BaseCommand
from apps.media.models import MediaCategory


# ---------------------------------------------------------------------------
# Category definitions
# Each tuple: (slug, name, description, display_order, is_gallery_visible)
# is_gallery_visible=False marks internal-only categories that should never
# appear as tabs on the public /gallery/ page.
# ---------------------------------------------------------------------------
CATEGORIES = [
    # ── Food photography — public gallery tabs ────────────────────────────
    ('starters',        'Starters',        'Appetizers and shareable plates',            1,  True),
    ('soups-and-salads','Soups & Salads',   'Fresh salads and homemade soups',            2,  True),
    ('wraps-and-tacos', 'Wraps & Tacos',    'Fresh wraps and tacos',                      3,  True),
    ('sandwiches',      'Sandwiches',       'Signature sandwiches',                       4,  True),
    ('burgers',         'Burgers',          'Half-pound burgers',                         5,  True),
    ('sides',           'Sides',            'Side dishes and add-ons',                    6,  True),
    ('pizza',           'Pizza',            'All pizzas baked on homemade dough',         7,  True),
    ('kids',            'Kids',             "Kids' menu selections",                      8,  True),
    ('desserts',        'Desserts',         'Sweet endings to your meal',                 9,  True),
    ('drinks',          'Drinks',           'Cocktails, beer, wine, and more',            10, True),

    # ── Venue photography — public gallery tabs ───────────────────────────
    ('interior',        'Interior',         'Inside the restaurant',                      11, True),
    ('exterior',        'Exterior',         'Outside and entrance',                       12, True),
    ('atmosphere',      'Atmosphere',       'Events, ambiance, and the SoHo experience',  13, True),

    # ── Internal library categories — not shown on public gallery ─────────
    ('banners',         'Banners',          'Images used in site banners and panels',     50, False),
    ('menu-backgrounds','Menu Backgrounds', 'Background images for menu category sections',51, False),
]


class Command(BaseCommand):
    help = 'Seeds the standard MediaCategory records for the media library.'

    def handle(self, *args, **kwargs):
        created_count = 0
        skipped_count = 0

        for slug, name, description, display_order, is_gallery_visible in CATEGORIES:
            obj, created = MediaCategory.objects.get_or_create(
                slug=slug,
                defaults={
                    'name':               name,
                    'description':        description,
                    'display_order':      display_order,
                    'is_published':       True,
                    'is_gallery_visible': is_gallery_visible,
                },
            )
            if created:
                self.stdout.write(f'  + {name}')
                created_count += 1
            else:
                skipped_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'\nDone. {created_count} created, {skipped_count} already existed.'
            )
        )
