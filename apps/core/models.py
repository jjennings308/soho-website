from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from django_ckeditor_5.fields import CKEditor5Field


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


class ThemeStyle(models.Model):
    """
    Controls fonts for a theme or overlay.
    All brand/palette colors are constants defined in theme.css — not admin-overridable.
    Promotional colors live in apps/menu/models.py (PromoSettings, MenuPromotion).

    CSS variable → field mapping:
        --font-primary   → primary_font
        --font-secondary → secondary_font
        --font-accent    → accent_font
    """
    FONT_CHOICES = [
        ('Georgia, serif',                  'Georgia'),
        ('"Playfair Display", serif',        'Playfair Display'),
        ('"Cormorant Garamond", serif',      'Cormorant Garamond'),
        ('"Libre Baskerville", serif',       'Libre Baskerville'),
        ('"Inter", sans-serif',             'Inter'),
        ('"Lato", sans-serif',              'Lato'),
        ('"Montserrat", sans-serif',        'Montserrat'),
        ('"Open Sans", sans-serif',         'Open Sans'),
        ('"Cinzel", serif',                 'Cinzel (Elegant)'),
        ('"Oswald", sans-serif',            'Oswald'),
        ('"Raleway", sans-serif',           'Raleway'),
        ('"Courier New", monospace',        'Courier New'),
    ]

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Theme Style'
        verbose_name_plural = 'Theme Styles'

    def __str__(self):
        return self.name

    def to_css_vars(self):
        """
        Returns a dict of { 'css-var-name': 'value' } for all non-blank fields.
        Only fonts are emitted — all colors are constants in theme.css.
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


class ThemeOverlay(models.Model):
    """
    A seasonal or event-based font overlay applied on top of the base theme.
    Colors are brand constants in theme.css and are not affected by overlays.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    style = models.ForeignKey(
        ThemeStyle,
        on_delete=models.PROTECT,
        related_name='overlays',
        help_text="Font style to apply when this overlay is active"
    )
    valid_from = models.DateField(
        blank=True, null=True,
        help_text="Start date for automatic activation (leave blank for manual control)"
    )
    valid_to = models.DateField(
        blank=True, null=True,
        help_text="End date for automatic activation (leave blank for manual control)"
    )
    is_active = models.BooleanField(
        default=False,
        help_text="Manual activation toggle — used when no date range is set"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Theme Overlay'
        verbose_name_plural = 'Theme Overlays'

    def __str__(self):
        return self.name

    @property
    def is_currently_active(self):
        if not self.is_active:
            return False
        today = timezone.now().date()
        if self.valid_from and today < self.valid_from:
            return False
        if self.valid_to and today > self.valid_to:
            return False
        return True


class Theme(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    theme_directory = models.CharField(
        max_length=100,
        help_text="Folder name under templates/themes/ (e.g., 'classic', 'elegant')"
    )
    base_style = models.ForeignKey(
        ThemeStyle,
        on_delete=models.PROTECT,
        related_name='themes',
        null=True, blank=True,
        help_text="Base font style for this theme"
    )
    preview_image = models.ImageField(upload_to='theme_previews/', blank=True, null=True)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Theme'
        verbose_name_plural = 'Themes'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.is_active:
            Theme.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_active_theme(cls):
        return cls.objects.filter(is_active=True).select_related('base_style').first()

    def resolve_style_vars(self):
        resolved = {}
        if self.base_style:
            resolved.update(self.base_style.to_css_vars())
        settings = SiteSettings.load()
        if settings.active_overlay and settings.active_overlay.is_currently_active:
            resolved.update(settings.active_overlay.style.to_css_vars())
        return resolved

    def get_google_fonts_url(self):
        font_families = set()
        if self.base_style:
            font_families.update(self.base_style.get_google_fonts())
        settings = SiteSettings.load()
        if settings.active_overlay and settings.active_overlay.is_currently_active:
            font_families.update(settings.active_overlay.style.get_google_fonts())
        if not font_families:
            return None
        families_param = '&family='.join(sorted(font_families))
        return f"https://fonts.googleapis.com/css2?family={families_param}&display=swap"


class SiteSettings(models.Model):
    """Singleton (pk=1 always) — global site settings."""
    restaurant_name = models.CharField(max_length=200, default="Your Restaurant")
    tagline = models.CharField(max_length=300, blank=True)
    description = CKEditor5Field(blank=True)

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

    hours_text = CKEditor5Field(blank=True)
    short_about_text = CKEditor5Field(blank=True)
    catering_text = CKEditor5Field(blank=True)

    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    yelp_url = models.URLField(blank=True)

    active_theme = models.ForeignKey(
        Theme, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='site_settings'
    )
    active_overlay = models.ForeignKey(
        ThemeOverlay, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='site_settings',
        help_text="Optional seasonal font overlay applied on top of the active theme"
    )

    meta_description = models.TextField(blank=True, max_length=160)
    meta_keywords = models.CharField(max_length=255, blank=True)

    logo = models.ImageField(upload_to='site/', blank=True, null=True)
    favicon = models.ImageField(upload_to='site/', blank=True, null=True)

    maintenance_mode = models.BooleanField(default=False)
    maintenance_message = models.TextField(blank=True)

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
