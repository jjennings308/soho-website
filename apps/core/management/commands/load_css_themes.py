"""
Management command: load_css_themes
====================================
Reads static/css/theme.css (base brand) and static/css/theme/*.css (overlays)
and seeds ThemeStyle + ThemeOverlay records from the CSS custom properties.

Two distinct jobs:
  1. theme.css        → creates a "Soho Base" ThemeStyle (assign to Theme.base_style)
  2. theme/*.css      → creates a ThemeStyle + ThemeOverlay per file

Usage:
    python manage.py load_css_themes
    python manage.py load_css_themes --dry-run
    python manage.py load_css_themes --update     # overwrite existing records
"""

import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.core.models import ThemeOverlay, ThemeStyle


# ── Complete CSS var → ThemeStyle field mapping ───────────────────────────────
CSS_VAR_TO_FIELD = {
    # Fonts
    '--font-primary':           'primary_font',
    '--font-secondary':         'secondary_font',
    '--font-accent':            'accent_font',
    # Text colors
    '--color-text-primary':     'primary_text_color',
    '--color-text-secondary':   'secondary_text_color',
    '--color-text-tertiary':    'tertiary_text_color',
    '--color-text-accent':      'accent_text_color',
    '--color-text-heading':     'heading_text_color',
    '--color-text-nav':         'nav_text_color',
    # Background colors
    '--color-bg-primary':       'primary_bg_color',
    '--color-bg-secondary':     'secondary_bg_color',
    '--color-bg-tertiary':      'tertiary_bg_color',
    '--color-bg-accent':        'accent_bg_color',
    '--color-nav-bg':           'nav_bg_color',
    # Extended gold palette
    '--color-gold-primary':     'gold_primary_color',
    '--color-gold-bright':      'gold_bright_color',
    '--color-gold-deep':        'gold_deep_color',
    '--color-gold-light':       'gold_light_color',
    # Neutrals
    '--color-dark-gray':        'dark_gray_color',
    '--color-mid-gray':         'mid_gray_color',
}

# ── Overlay file metadata ─────────────────────────────────────────────────────
OVERLAY_METADATA = {
    'christmas.css': {
        'style_name':   'Christmas / Holiday',
        'overlay_name': 'Christmas',
        'description':  'Warm candlelight accents with holiday red and green.',
        'valid_from':   (12, 1),
        'valid_to':     (12, 31),
    },
    'pgh_black_gold.css': {
        'style_name':   'Pittsburgh Black & Gold',
        'overlay_name': 'Pittsburgh Black & Gold',
        'description':  'Steelers-intensity gold (#ffb612) over deep black. '
                        'Activate during playoffs or Pittsburgh-specific events.',
        'valid_from':   None,
        'valid_to':     None,
    },
    'valentines.css': {
        'style_name':   "Valentine's Day",
        'overlay_name': "Valentine's Day",
        'description':  "Romantic deep reds and pinks for Valentine's Day promotions.",
        'valid_from':   (2, 1),
        'valid_to':     (2, 14),
    },
}


def parse_css_vars(css_text):
    """
    Extract CSS custom property declarations from a CSS file.
    Strips comments, handles :root and @media blocks.
    Skips var() references — we want literal values only.
    Returns { '--var-name': 'value' }.
    """
    css_text = re.sub(r'/\*.*?\*/', '', css_text, flags=re.DOTALL)
    vars_found = {}
    for match in re.finditer(r'(--[\w-]+)\s*:\s*([^;}{]+);', css_text):
        var_name = match.group(1).strip()
        value = match.group(2).strip()
        if not value.startswith('var('):
            vars_found[var_name] = value
    return vars_found


def css_vars_to_fields(all_vars):
    """Split CSS vars into mapped fields and unmapped (component tokens)."""
    field_values = {}
    unmapped = {}
    for var_name, value in all_vars.items():
        if var_name in CSS_VAR_TO_FIELD:
            field_values[CSS_VAR_TO_FIELD[var_name]] = value
        else:
            unmapped[var_name] = value
    return field_values, unmapped


class Command(BaseCommand):
    help = (
        'Seeds ThemeStyle and ThemeOverlay records from CSS files.\n'
        '  static/css/theme.css    -> "Soho Base" ThemeStyle\n'
        '  static/css/theme/*.css  -> ThemeStyle + ThemeOverlay per file'
    )

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Show what would be created without writing to the database.')
        parser.add_argument('--update', action='store_true',
                            help='Update existing records if they already exist.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        update = options['update']
        base_dir = Path(settings.BASE_DIR)

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — nothing will be saved.\n'))

        # ── Step 1: Base brand ThemeStyle from theme.css ──────────────────────
        self.stdout.write('\n== Base Brand Style (theme.css) ==')
        brand_css_path = base_dir / 'static' / 'css' / 'theme.css'

        if not brand_css_path.exists():
            self.stderr.write(self.style.ERROR(f'  Not found: {brand_css_path}'))
        else:
            css_text = brand_css_path.read_text(encoding='utf-8')
            all_vars = parse_css_vars(css_text)
            field_values, unmapped = css_vars_to_fields(all_vars)

            self.stdout.write(f'  Parsed {len(all_vars)} variables — {len(field_values)} map to ThemeStyle fields')
            if unmapped:
                self.stdout.write(
                    '  Not mapped (spacing/layout/shadows — stays in theme.css): '
                    + ', '.join(unmapped.keys())
                )

            style_name = 'Soho Base'
            if not dry_run:
                defaults = {
                    **field_values,
                    'description': 'Base Soho Pittsburgh brand style — seeded from theme.css',
                }
                if update:
                    obj, created = ThemeStyle.objects.update_or_create(name=style_name, defaults=defaults)
                else:
                    obj, created = ThemeStyle.objects.get_or_create(name=style_name, defaults=defaults)
                status = 'CREATED' if created else ('UPDATED' if update else 'SKIPPED (use --update to overwrite)')
                self.stdout.write(self.style.SUCCESS(f'  ThemeStyle "{style_name}": {status} (pk={obj.pk})'))
                self.stdout.write('  -> Assign this to your Theme\'s "Base Style" field in admin.')
            else:
                self.stdout.write(f'  [dry-run] Would create ThemeStyle: "{style_name}"')
                for field, val in field_values.items():
                    self.stdout.write(f'    {field} = {val}')

        # ── Step 2: Overlay ThemeStyles from theme/*.css ──────────────────────
        theme_css_dir = base_dir / 'static' / 'css' / 'theme'
        if not theme_css_dir.exists():
            self.stderr.write(self.style.ERROR(f'  Not found: {theme_css_dir}'))
            return

        css_files = sorted(theme_css_dir.glob('*.css'))
        if not css_files:
            self.stderr.write(self.style.WARNING(f'  No .css files found in {theme_css_dir}'))
            return

        self.stdout.write(f'\n== Overlay Styles ({len(css_files)} file(s) in static/css/theme/) ==')

        for css_path in css_files:
            filename = css_path.name
            meta = OVERLAY_METADATA.get(filename)

            if not meta:
                self.stdout.write(self.style.WARNING(
                    f'\n  Skipping {filename} — add an entry to OVERLAY_METADATA to include it.'
                ))
                continue

            self.stdout.write(f'\n-- {filename}')
            css_text = css_path.read_text(encoding='utf-8')
            all_vars = parse_css_vars(css_text)

            if not all_vars:
                self.stdout.write(self.style.WARNING('   No CSS variables found — skipping.'))
                continue

            field_values, unmapped = css_vars_to_fields(all_vars)
            self.stdout.write(f'   Mapped to fields: {list(field_values.keys())}')
            if unmapped:
                self.stdout.write('   Component overrides (keep in CSS):')
                for k, v in unmapped.items():
                    self.stdout.write(f'     {k}: {v}')

            # ThemeStyle
            style_name = meta['style_name']
            style_obj = None
            if not dry_run:
                defaults = {**field_values, 'description': meta['description']}
                if update:
                    style_obj, created = ThemeStyle.objects.update_or_create(name=style_name, defaults=defaults)
                else:
                    style_obj, created = ThemeStyle.objects.get_or_create(name=style_name, defaults=defaults)
                status = 'CREATED' if created else ('UPDATED' if update else 'SKIPPED')
                self.stdout.write(f'   ThemeStyle "{style_name}": {status} (pk={style_obj.pk})')
            else:
                self.stdout.write(f'   [dry-run] Would create ThemeStyle: "{style_name}"')

            # ThemeOverlay
            overlay_name = meta['overlay_name']
            valid_from = meta.get('valid_from')
            valid_to = meta.get('valid_to')

            if not dry_run and style_obj:
                overlay_defaults = {'style': style_obj, 'description': meta['description'], 'is_active': False}
                if update:
                    overlay_obj, created = ThemeOverlay.objects.update_or_create(name=overlay_name, defaults=overlay_defaults)
                else:
                    overlay_obj, created = ThemeOverlay.objects.get_or_create(name=overlay_name, defaults=overlay_defaults)
                status = 'CREATED' if created else ('UPDATED' if update else 'SKIPPED')
                date_hint = (
                    f' (set dates in admin: {valid_from[0]:02d}/{valid_from[1]:02d} -> {valid_to[0]:02d}/{valid_to[1]:02d})'
                    if valid_from else ' (no date range — toggle is_active manually)'
                )
                self.stdout.write(f'   ThemeOverlay "{overlay_name}": {status} (pk={overlay_obj.pk}){date_hint}')
            elif dry_run:
                date_str = (
                    f'{valid_from[0]:02d}/{valid_from[1]:02d} -> {valid_to[0]:02d}/{valid_to[1]:02d}'
                    if valid_from else 'manual toggle'
                )
                self.stdout.write(f'   [dry-run] Would create ThemeOverlay: "{overlay_name}" ({date_str})')

        self.stdout.write(self.style.SUCCESS(
            '\n Done.\n'
            'Next steps:\n'
            '  1. python manage.py migrate  (applies new ThemeStyle fields)\n'
            '  2. Admin -> Themes -> assign "Soho Base" as Base Style on your Theme\n'
            '  3. Admin -> Theme Overlays -> set valid_from/valid_to dates\n'
            '  4. Admin -> Site Settings -> assign Active Overlay when needed\n'
            '  5. Remove overlay <link> tags from base.html (keep theme.css — it\n'
            '     still provides spacing/shadow tokens that have no model field)'
        ))
