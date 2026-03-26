from django.db import models
from django.core.validators import RegexValidator


GOOGLE_FONTS_MAP = {
    '"Playfair Display", serif':    'Playfair+Display:ital,wght@0,400;0,600;0,700;0,900;1,400',
    '"Cormorant Garamond", serif':  'Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400',
    '"Libre Baskerville", serif':   'Libre+Baskerville:ital,wght@0,400;0,700;1,400',
    '"Inter", sans-serif':          'Inter:wght@300;400;500;600;700',
    '"Lato", sans-serif':           'Lato:ital,wght@0,300;0,400;0,700;1,300;1,400',
    '"Montserrat", sans-serif':     'Montserrat:wght@300;400;500;600;700',
    '"Open Sans", sans-serif':      'Open+Sans:ital,wght@0,300;0,400;0,600;1,400',
    '"Cinzel", serif':              'Cinzel:wght@400;600;700',
    '"Oswald", sans-serif':         'Oswald:wght@300;400;500;600',
    '"Raleway", sans-serif':        'Raleway:wght@300;400;500;600;700',
    'Georgia, serif':               None,
    '"Courier New", monospace':     None,
}

FONT_CHOICES = [
    ('Georgia, serif',               'Georgia'),
    ('"Playfair Display", serif',    'Playfair Display'),
    ('"Cormorant Garamond", serif',  'Cormorant Garamond'),
    ('"Libre Baskerville", serif',   'Libre Baskerville'),
    ('"Inter", sans-serif',          'Inter'),
    ('"Lato", sans-serif',           'Lato'),
    ('"Montserrat", sans-serif',     'Montserrat'),
    ('"Open Sans", sans-serif',      'Open Sans'),
    ('"Cinzel", serif',              'Cinzel (Elegant)'),
    ('"Oswald", sans-serif',         'Oswald'),
    ('"Raleway", sans-serif',        'Raleway'),
    ('"Courier New", monospace',     'Courier New'),
]


class Theme(models.Model):
    """
    A site theme. Controls the template directory and font stack.

    Font fields map to CSS variables injected at render time:
        --font-primary   → primary_font
        --font-secondary → secondary_font
        --font-accent    → accent_font

    All brand/palette colors are constants defined in theme.css — not
    admin-overridable. Promotional colors live in apps/menu/models.py.

    is_active — theme is enabled and available to be selected as active_theme.
                Only active themes can be set as SiteSettings.active_theme.
                Deactivating a theme that is currently active_theme will
                automatically clear SiteSettings.active_theme.
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    theme_directory = models.CharField(
        max_length=100,
        help_text="Folder name under templates/themes/ (e.g., 'classic', 'elegant')"
    )

    primary_font = models.CharField(
        max_length=100, choices=FONT_CHOICES, blank=True,
        help_text="--font-primary — headings and titles"
    )
    secondary_font = models.CharField(
        max_length=100, choices=FONT_CHOICES, blank=True,
        help_text="--font-secondary — body text and descriptions"
    )
    accent_font = models.CharField(
        max_length=100, choices=FONT_CHOICES, blank=True,
        help_text="--font-accent — prices, labels, and UI accents"
    )

    preview_image = models.ImageField(upload_to='theme_previews/', blank=True, null=True)
    is_active = models.BooleanField(
        default=False,
        help_text="Enable this theme so it can be selected as the site's active theme."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Theme'
        verbose_name_plural = 'Themes'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # If this theme is being deactivated and it's the current site theme,
        # clear SiteSettings.active_theme to avoid pointing at an inactive theme.
        if self.pk and not self.is_active:
            try:
                previous = Theme.objects.get(pk=self.pk)
                if previous.is_active:
                    # Was active, now being deactivated — clear if it's current
                    SiteSettings.objects.filter(active_theme=self).update(active_theme=None)
            except Theme.DoesNotExist:
                pass

        super().save(*args, **kwargs)

    @classmethod
    def get_active_theme(cls):
        """Returns the theme currently set as SiteSettings.active_theme."""
        return SiteSettings.load().active_theme

    def to_css_vars(self):
        """
        Returns a dict of { 'css-var-name': 'value' } for all non-blank font fields.
        Colors are constants in theme.css and are never included here.
        """
        mapping = {
            'font-primary':   self.primary_font,
            'font-secondary': self.secondary_font,
            'font-accent':    self.accent_font,
        }
        return {k: v for k, v in mapping.items() if v}

    def get_google_fonts(self):
        fonts = set()
        for field in [self.primary_font, self.secondary_font, self.accent_font]:
            if field and field in GOOGLE_FONTS_MAP and GOOGLE_FONTS_MAP[field]:
                fonts.add(GOOGLE_FONTS_MAP[field])
        return list(fonts)

    def get_google_fonts_url(self):
        font_families = self.get_google_fonts()
        if not font_families:
            return None
        families_param = '&family='.join(sorted(font_families))
        return f"https://fonts.googleapis.com/css2?family={families_param}&display=swap"

    def resolve_style_vars(self):
        """Delegates to to_css_vars(). Kept for call-site compatibility."""
        return self.to_css_vars()


class SiteSettings(models.Model):
    """
    Singleton (pk=1 always) — global site configuration.

    Editable copy (taglines, body text, hours, etc.) lives in apps/content
    and is managed via ContentSlot / ContentBlock. Use the content_tags
    template tag to render those blocks:

        {% load content_tags %}
        {% get_active_block 'hours_text' as block %}
        {{ block.body|safe }}

    Slots that correspond to removed fields:
        tagline             → 'site_tagline'
        description         → 'site_description'
        hours_text          → 'hours_text'
        short_about_text    → 'about_short'
        catering_text       → 'catering_body'
        maintenance_message → 'maintenance_message'
    """
    restaurant_name = models.CharField(max_length=200, default="Your Restaurant")

    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    email = models.EmailField(blank=True)

    address_line1 = models.CharField(max_length=200, blank=True)
    address_line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True, default="USA")

    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    yelp_url = models.URLField(blank=True)

    active_theme = models.ForeignKey(
        Theme,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='site_settings',
        limit_choices_to={'is_active': True},
        help_text="The theme currently in use. Only active themes can be selected."
    )

    meta_description = models.TextField(blank=True, max_length=160)
    meta_keywords = models.CharField(max_length=255, blank=True)

    logo = models.ImageField(upload_to='site/', blank=True, null=True)
    favicon = models.ImageField(upload_to='site/', blank=True, null=True)

    maintenance_mode = models.BooleanField(default=False)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Site Settings'
        verbose_name_plural = 'Site Settings'

    def __str__(self):
        return f"Site Settings - {self.restaurant_name}"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
