from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from django_ckeditor_5.fields import CKEditor5Field


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
        help_text="Main text color (e.g., #1a1a1a)"
    )
    secondary_text_color = models.CharField(
        max_length=20,
        blank=True,
        help_text="Secondary/muted text color"
    )
    accent_text_color = models.CharField(
        max_length=20,
        blank=True,
        help_text="Accent color for prices, highlights"
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
        help_text="Main page background color"
    )
    secondary_bg_color = models.CharField(
        max_length=20,
        blank=True,
        help_text="Card/section background color"
    )
    accent_bg_color = models.CharField(
        max_length=20,
        blank=True,
        help_text="Accent background (buttons, badges, highlights)"
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
        Returns a dict of CSS variable name -> value for all non-blank fields.
        Used when merging base + overlay styles.
        """
        mapping = {
            'primary-font': self.primary_font,
            'secondary-font': self.secondary_font,
            'accent-font': self.accent_font,
            'primary-text-color': self.primary_text_color,
            'secondary-text-color': self.secondary_text_color,
            'accent-text-color': self.accent_text_color,
            'heading-text-color': self.heading_text_color,
            'primary-bg-color': self.primary_bg_color,
            'secondary-bg-color': self.secondary_bg_color,
            'accent-bg-color': self.accent_bg_color,
            'nav-bg-color': self.nav_bg_color,
        }
        # Only return fields that have a value set
        return {k: v for k, v in mapping.items() if v}


class ThemeOverlay(models.Model):
    """
    A seasonal or promotion-based style overlay that sits on top of the base theme style.
    Only the fields set here will override the base — everything else falls through.
    Examples: Christmas, Valentine's Day, Pittsburgh (Black & Gold), Mardi Gras
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
    Defines available themes for the restaurant website.
    Each theme has a name, directory path, and preview image.
    A theme pairs a base style with an optional overlay style.
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    theme_directory = models.CharField(
        max_length=100,
        help_text="Directory name in themes/ folder (e.g., 'classic', 'modern')"
    )
    preview_image = models.ImageField(
        upload_to='theme_previews/',
        blank=True,
        null=True,
        help_text="Screenshot or preview of the theme"
    )

    # Style layers
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
        if self.is_active:
            Theme.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_active_theme(cls):
        """Get the currently active theme"""
        return cls.objects.filter(is_active=True).select_related('base_style').first()

    def resolve_style_vars(self):
        """
        Merge base style + any active overlay into a single dict of CSS variables.
        Overlay values win over base values for any overlapping keys.
        """
        resolved = {}

        # Start with base style
        if self.base_style:
            resolved.update(self.base_style.to_css_vars())

        # Apply active overlay from SiteSettings if one exists
        from .models import SiteSettings
        settings = SiteSettings.load()
        if settings.active_overlay and settings.active_overlay.is_currently_active:
            resolved.update(settings.active_overlay.style.to_css_vars())

        return resolved


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
    Global site settings for the restaurant.
    Singleton model - only one instance should exist.
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
        """Load the singleton instance"""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
