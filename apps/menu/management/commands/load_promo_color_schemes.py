"""
Management command: load_promo_color_schemes
Seeds PromoColorScheme records for SoHo Pittsburgh.

Usage:
    python manage.py load_promo_color_schemes

Safe to run multiple times — uses get_or_create on name, then updates fields.
The default scheme (SoHo Black & Gold) is always enforced on every run.
"""

from django.core.management.base import BaseCommand
from apps.menu.models import PromoColorScheme


SCHEMES = [
    # ── SoHo House ────────────────────────────────────────────────────────────
    {
        'name':          'SoHo Black & Gold',
        'primary_color': '#FFB612',   # Steelers/Pitt gold
        'accent_color':  '#FFD700',   # brighter gold highlight
        'text_color':    '#F5F5F5',   # near-white on dark bg
        'bg_color':      '#101010',   # near-black
        'is_default':    True,
    },

    # ── Pittsburgh Sports ─────────────────────────────────────────────────────
    {
        'name':          'Pittsburgh Steelers',
        'primary_color': '#FFB612',   # Steelers gold
        'accent_color':  '#101820',   # Steelers black
        'text_color':    '#101820',
        'bg_color':      '#FFB612',
        'is_default':    False,
    },
    {
        'name':          'Pittsburgh Pirates',
        'primary_color': '#FDB827',   # Pirates gold
        'accent_color':  '#27251F',   # Pirates black
        'text_color':    '#27251F',
        'bg_color':      '#FDB827',
        'is_default':    False,
    },
    {
        'name':          'Pittsburgh Penguins',
        'primary_color': '#FCB514',   # Penguins gold
        'accent_color':  '#000000',   # Penguins black
        'text_color':    '#FFFFFF',
        'bg_color':      '#000000',
        'is_default':    False,
    },
    {
        'name':          'Pitt Panthers',
        'primary_color': '#003594',   # Pitt royal blue
        'accent_color':  '#FFB81C',   # Pitt gold
        'text_color':    '#FFFFFF',
        'bg_color':      '#003594',
        'is_default':    False,
    },

    # ── Winter / Holiday ──────────────────────────────────────────────────────
    {
        'name':          'Christmas',
        'primary_color': '#C41E3A',   # Christmas red
        'accent_color':  '#2E8B57',   # Christmas green
        'text_color':    '#FFFFFF',
        'bg_color':      '#1A3C2A',   # deep evergreen
        'is_default':    False,
    },
    {
        'name':          "New Year's Eve",
        'primary_color': '#C9A84C',   # champagne gold
        'accent_color':  '#E8E8E8',   # silver
        'text_color':    '#F0F0F0',
        'bg_color':      '#0D0D0D',   # midnight black
        'is_default':    False,
    },
    {
        'name':          'Halloween',
        'primary_color': '#FF6B00',   # pumpkin orange
        'accent_color':  '#9B59B6',   # purple
        'text_color':    '#F0F0F0',
        'bg_color':      '#1A0A00',   # very dark brown-black
        'is_default':    False,
    },
    {
        'name':          'Thanksgiving',
        'primary_color': '#C1440E',   # burnt sienna
        'accent_color':  '#E8A020',   # harvest gold
        'text_color':    '#FDF3E3',   # warm cream
        'bg_color':      '#3D1C02',   # dark walnut
        'is_default':    False,
    },

    # ── Spring / Summer ───────────────────────────────────────────────────────
    {
        'name':          "St. Patrick's Day",
        'primary_color': '#009A44',   # Kelly green
        'accent_color':  '#F5A800',   # golden amber (for the beer)
        'text_color':    '#FFFFFF',
        'bg_color':      '#004D22',   # dark green
        'is_default':    False,
    },
    {
        'name':          "Valentine's Day",
        'primary_color': '#C0002A',   # deep red
        'accent_color':  '#FF6B8A',   # soft pink
        'text_color':    '#FFF0F3',   # blush white
        'bg_color':      '#3D0010',   # dark burgundy
        'is_default':    False,
    },
    {
        'name':          'Fourth of July',
        'primary_color': '#B22234',   # flag red
        'accent_color':  '#3C3B6E',   # flag blue
        'text_color':    '#FFFFFF',
        'bg_color':      '#3C3B6E',
        'is_default':    False,
    },
    {
        'name':          'Summer',
        'primary_color': '#F5A800',   # golden amber
        'accent_color':  '#FF6B35',   # sunset orange
        'text_color':    '#1A1A1A',
        'bg_color':      '#FFF8E7',   # warm cream
        'is_default':    False,
    },

    # ── Bar / Drink Themes ────────────────────────────────────────────────────
    {
        'name':          'Happy Hour',
        'primary_color': '#F5A800',   # amber
        'accent_color':  '#FFD700',   # gold highlight
        'text_color':    '#1A1A1A',
        'bg_color':      '#1C1005',   # dark bourbon brown
        'is_default':    False,
    },
    {
        'name':          'Oktoberfest',
        'primary_color': '#003399',   # Bavarian blue
        'accent_color':  '#F5A800',   # wheat/amber
        'text_color':    '#FFFFFF',
        'bg_color':      '#001A66',   # deep Bavarian blue
        'is_default':    False,
    },
    {
        'name':          'Mardi Gras',
        'primary_color': '#7B2D8B',   # purple
        'accent_color':  '#F5A800',   # gold
        'text_color':    '#FFFFFF',
        'bg_color':      '#1A0A2E',   # deep purple-black
        'is_default':    False,
    },
]


class Command(BaseCommand):
    help = 'Seeds PromoColorScheme records for SoHo Pittsburgh.'

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for data in SCHEMES:
            is_default = data.pop('is_default')
            obj, created = PromoColorScheme.objects.get_or_create(
                name=data['name'],
                defaults={**data, 'is_default': is_default},
            )
            if created:
                created_count += 1
                self.stdout.write(f"  Created: {obj.name}")
            else:
                # Update all fields in case colors have been revised
                for field, value in data.items():
                    setattr(obj, field, value)
                # Only set is_default=True here; never forcibly clear it on
                # non-default schemes — an admin may have changed that manually.
                if is_default:
                    obj.is_default = True
                obj.save()
                updated_count += 1
                self.stdout.write(f"  Updated: {obj.name}")

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. {created_count} created, {updated_count} updated.'
        ))
