from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from django_ckeditor_5.fields import CKEditor5Field


# Maps font choice values to their Google Fonts URL parameter
# Used by SiteSettings.get_google_fonts_url() to build a single <link> tag
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
    # Georgia and Courier New are system fonts — no Google Fonts import needed
    'Georgia, serif':               None,
    '"Courier New", monospace':     None,
}


class ThemeStyle(models.Model):
    """
    Defines typography and color settings for a theme or overlay.
    Blank fields mean "inherit from base theme" when used as an overlay.
    """
    FONT_CHOICES = [
        # Serif
        ('Georgia, serif', 'Georgia'),
        ('"Playfair Display", serif', 'Playfair Display'),
        ('"Cormorant Garamond", serif', 'Cormorant Garamond'),
        ('"Libre Baskerville", serif', 'Libre Baskerville'),
        # Sans-serif
        ('"Inter", sans-serif', 'Inter'),
        ('"Lato", sans-serif', 'Lato'),
        ('"Montserrat", sans-serif', 'Montserrat'),
        ('"Open Sans", sans-serif', 'Open Sans'),
        # Display / Decorative
        ('"Cinzel", serif', 'Cinzel (Elegant)'),
        ('"Oswald", sans-serif', 'Oswald'),
        ('"Raleway", sans-serif', 'Raleway'),
        # Monospace
        ('"Courier New", monospace', 'Courier New'),
    ]

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    # Typography
    primary_font = models.CharField(
        max_length=100,
        choices=FONT_CHOICES,
        blank=True,
        help_text="Main font for headings and titles"
    )
    secondary_font = models.CharField(
        max_length=100,
        choices=FONT_CHOICES,
        blank=True,
        help_text="Font for body text and descriptions"
    )
    accent_font = models.CharField(
        max_length=100,
        choices=FONT_CHOICES,
        blank=True,
        help_text="Font for prices, labels, and accents"
    )

    # Colors - Text
    primary_text_color = models.CharField(
        max_length=20,
        blank=True,
        help_text="Main text color (e.g., #f5f0e8)"
    )
    secondary_text_color = models.CharField(
        max_length=20,
        blank=True,
        help_text="Secondary/muted text color"
    )
    accent_text_color = models.CharField(
        max_length=20,
        blank=True,
        help_text="Accent color for prices, highlights (e.g., #c9972a)"
    )
    heading_text_color = models.CharField(
        max_length=20,
        blank=True,
        help_text="Color specifically for headings"
    )

    # Colors - Backgrounds
    primary_bg_color = models.CharField(
        max_length=20,
        blank=True,
        help_text="Main page background color (e.g., #0a0a0a)"
    )
    secondary_bg_color = models.CharField(
        max_length=20,
        blank=True,
        help_text="Card/section background color (e.g., #1a1a1a)"
    )
    accent_bg_color = models.CharField(
        max_length=20,
        blank=True,
        help_text="Accent background — buttons, badges, highlights (e.g., #c9972a)"
    )
    nav_bg_color = models.CharField(
        max_length=20,
        blank=True,
        help_text="Navigation bar background color"
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
        Returns a dict mapping CSS custom property names → values
        for all non-blank fields on this style.

        These names match exactly what theme.css defines in :root {}.
        Used by Theme.resolve_style_vars() to merge base + overlay.
        The template renders them as:
            {% for var, val in theme_style_vars.items %}
                --{{ var }}: {{ val }};
            {% endfor %}
        """
        mapping = {
            # Fonts — match theme.css variables
            'font-primary':   self.primary_font,
            'font-secondary': self.secondary_font,
            'font-accent':    self.accent_font,
            # Text colors
            'color-text-primary':   self.primary_text_color,
            'color-text-secondary': self.secondary_text_color,
            'color-text-accent':    self.accent_text_color,
            'color-text-heading':   self.heading_text_color,
            # Background colors
            'color-bg-primary':   self.primary_bg_color,
            'color-bg-secondary': self.secondary_bg_color,
            'color-bg-accent':    self.accent_bg_color,
            'color-nav-bg':       self.nav_bg_color,
        }
        # Only return fields that have a value set
        return {k: v for k, v in mapping.items() if v}

    def get_google_fonts(self):
        """
        Returns a list of Google Fonts family strings needed for this style.
        Used by SiteSettings.get_google_fonts_url() to build the combined URL.
        Skips system fonts (Georgia, Courier New) which don't need importing.
        """
        fonts = set()
        for field in [self.primary_font, self.secondary_font, self.accent_font]:
            if field and field in GOOGLE_FONTS_MAP and GOOGLE_FONTS_MAP[field]:
                fonts.add(GOOGLE_FONTS_MAP[field])
        return list(fonts)


class ThemeOverlay(models.Model):
    """
    A seasonal or promotion-based style overlay that sits on top of the base theme.
    Only fields set here override the base — everything else falls through.
    Examples: Christmas, Valentine's Day, Pittsburgh Black & Gold, Mardi Gras
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    style = models.ForeignKey(
        ThemeStyle,
        on_delete=models.PROTECT,
        help_text="The style definition for this overlay"
    )

    # Date range for automatic activation/deactivation
    valid_from = models.DateField(
        null=True,
        blank=True,
        help_text="Date this overlay becomes active (leave blank for manual control)"
    )
    valid_to = models.DateField(
        null=True,
        blank=True,
        help_text="Date this overlay expires (leave blank for manual control)"
    )
    is_active = models.BooleanField(
        default=False,
        help_text="Manually force this overlay on/off (date range takes priority if set)"
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
        """Check if this overlay should be applied right now."""
        today = timezone.now().date()
        if self.valid_from and self.valid_to:
            return self.valid_from <= today <= self.valid_to
        return self.is_active


class Theme(models.Model):
    """
    A theme pairs a base ThemeStyle with a directory of HTML templates.
    The active Theme determines which templates are rendered and which
    base CSS variables are set.
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    theme_directory = models.CharField(
        max_length=100,
        help_text="Directory name in themes/ folder (e.g., 'classic', 'modern', 'elegant')"
    )
    preview_image = models.ImageField(
        upload_to='theme_previews/',
        blank=True,
        null=True,
        help_text="Screenshot or preview of this theme"
    )

    # Style layer
    base_style = models.ForeignKey(
        ThemeStyle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='base_themes',
        help_text="The base branding style (fonts, colors) for this theme"
    )

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
        # Enforce only one active theme at a time
        if self.is_active:
            Theme.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_active_theme(cls):
        """Get the currently active theme, with base_style pre-fetched."""
        return cls.objects.filter(is_active=True).select_related('base_style').first()

    def resolve_style_vars(self):
        """
        Merge base style + any currently active overlay into a single CSS var dict.
        Overlay values win over base values for any overlapping keys.

        Returns: dict of { 'color-bg-primary': '#0a0a0a', 'font-primary': '"Playfair Display", serif', ... }
        """
        resolved = {}

        # Layer 1: base style
        if self.base_style:
            resolved.update(self.base_style.to_css_vars())

        # Layer 2: active overlay (if one is set in SiteSettings and currently in-range)
        settings = SiteSettings.load()
        if settings.active_overlay and settings.active_overlay.is_currently_active:
            resolved.update(settings.active_overlay.style.to_css_vars())

        return resolved

    def get_google_fonts_url(self):
        """
        Builds a single Google Fonts URL covering all fonts needed by the
        active base style + active overlay. Returns None if no web fonts needed.

        Usage in base.html:
            {% if google_fonts_url %}
            <link href="{{ google_fonts_url }}" rel="stylesheet">
            {% endif %}
        """
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


class PageTemplate(models.Model):
    """
    Defines different page templates that can be assigned to pages.
    Templates control the layout and structure of pages.
    """
    PAGE_TYPES = [
        ('home', 'Home Page'),
        ('menu', 'Menu Page'),
        ('promotions', 'Promotions Page'),
        ('about', 'About Page'),
        ('contact', 'Contact Page'),
        ('gallery', 'Gallery Page'),
    ]

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    page_type = models.CharField(max_length=20, choices=PAGE_TYPES)
    template_file = models.CharField(
        max_length=200,
        help_text="Template file path relative to theme directory (e.g., 'pages/home_template1.html')"
    )
    description = models.TextField(blank=True)
    preview_image = models.ImageField(
        upload_to='template_previews/',
        blank=True,
        null=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['page_type', 'name']
        verbose_name = 'Page Template'
        verbose_name_plural = 'Page Templates'

    def __str__(self):
        return f"{self.get_page_type_display()} - {self.name}"


class SiteSettings(models.Model):
    """
    Global site settings — singleton (pk=1 always).
    Controls restaurant info, active theme, active overlay, and page templates.
    """
    # Restaurant Information
    restaurant_name = models.CharField(max_length=200, default="Your Restaurant")
    tagline = models.CharField(max_length=300, blank=True)
    description = CKEditor5Field(blank=True)

    # Contact Information
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    email = models.EmailField(blank=True)

    # Address
    address_line1 = models.CharField(max_length=200, blank=True)
    address_line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True, default="USA")

    # Hours
    hours_text = CKEditor5Field(
        blank=True,
        help_text="Restaurant hours (use rich text for formatting)"
    )

    # Social Media
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    yelp_url = models.URLField(blank=True)

    # Theme and Template Settings
    active_theme = models.ForeignKey(
        Theme,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='site_settings'
    )
    active_overlay = models.ForeignKey(
        ThemeOverlay,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='site_settings',
        help_text="Optional seasonal/promotion overlay applied on top of the active theme"
    )
    home_template = models.ForeignKey(
        PageTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='home_pages',
        limit_choices_to={'page_type': 'home', 'is_active': True}
    )
    menu_template = models.ForeignKey(
        PageTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='menu_pages',
        limit_choices_to={'page_type': 'menu', 'is_active': True}
    )
    promotions_template = models.ForeignKey(
        PageTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='promotions_pages',
        limit_choices_to={'page_type': 'promotions', 'is_active': True}
    )

    # SEO
    meta_description = models.TextField(
        blank=True,
        max_length=160,
        help_text="Meta description for search engines (max 160 characters)"
    )
    meta_keywords = models.CharField(
        max_length=255,
        blank=True,
        help_text="Comma-separated keywords"
    )

    # Images
    logo = models.ImageField(upload_to='site/', blank=True, null=True)
    favicon = models.ImageField(upload_to='site/', blank=True, null=True)

    # Maintenance
    maintenance_mode = models.BooleanField(
        default=False,
        help_text="Enable maintenance mode to show 'Coming Soon' page"
    )
    maintenance_message = models.TextField(
        blank=True,
        help_text="Message to display during maintenance"
    )

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
        """Load the singleton instance, creating it with defaults if it doesn't exist."""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
