from django.db import models
from django.core.validators import RegexValidator
from django_ckeditor_5.fields import CKEditor5Field


class Theme(models.Model):
    """
    Defines available themes for the restaurant website.
    Each theme has a name, directory path, and preview image.
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
        # Ensure only one theme is active at a time
        if self.is_active:
            Theme.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_active_theme(cls):
        """Get the currently active theme"""
        return cls.objects.filter(is_active=True).first()


class PageTemplate(models.Model):
    """
    Defines different page templates that can be assigned to pages.
    Templates control the layout and structure of pages.
    """
    PAGE_TYPES = [
        ('home', 'Home Page'),
        ('menu', 'Menu Page'),
        ('events', 'Events Page'),
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
    events_template = models.ForeignKey(
        PageTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='events_pages',
        limit_choices_to={'page_type': 'events', 'is_active': True}
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
        # Ensure only one instance exists
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        """Load the singleton instance"""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
