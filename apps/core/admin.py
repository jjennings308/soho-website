from django.contrib import admin
from .models import Theme, ThemeStyle, ThemeOverlay, PageTemplate, SiteSettings


@admin.register(ThemeStyle)
class ThemeStyleAdmin(admin.ModelAdmin):
    list_display = ['name', 'primary_font', 'primary_bg_color', 'accent_text_color', 'updated_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description')
        }),
        ('Typography', {
            'fields': ('primary_font', 'secondary_font', 'accent_font'),
            'description': 'Fonts used for headings, body text, and accents.'
        }),
        ('Text Colors', {
            'fields': ('primary_text_color', 'secondary_text_color', 'tertiary_text_color', 'accent_text_color', 'heading_text_color'),
        }),
        ('Background Colors', {
            'fields': ('primary_bg_color', 'secondary_bg_color', 'tertiary_bg_color', 'accent_bg_color', 'nav_bg_color'),
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ThemeOverlay)
class ThemeOverlayAdmin(admin.ModelAdmin):
    list_display = ['name', 'style', 'valid_from', 'valid_to', 'is_active', 'is_currently_active']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'is_currently_active']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'style')
        }),
        ('Activation', {
            'fields': ('valid_from', 'valid_to', 'is_active'),
            'description': (
                'Set a date range to activate this overlay automatically. '
                'If no dates are set, use the Is Active toggle for manual control.'
            )
        }),
        ('Status', {
            'fields': ('is_currently_active',),
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(boolean=True, description='Active Right Now?')
    def is_currently_active(self, obj):
        return obj.is_currently_active


@admin.register(Theme)
class ThemeAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'theme_directory', 'base_style', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description')
        }),
        ('Theme Settings', {
            'fields': ('theme_directory', 'base_style', 'preview_image', 'is_active'),
            'description': (
                'theme_directory should match the folder name under your templates/themes/ directory. '
                'base_style defines the fonts and colors for this theme.'
            )
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PageTemplate)
class PageTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'page_type', 'template_file', 'is_active', 'created_at']
    list_filter = ['page_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'page_type', 'description')
        }),
        ('Template Settings', {
            'fields': ('template_file', 'preview_image', 'is_active'),
            'description': (
                'template_file is the path relative to the theme directory, '
                'e.g. "pages/home_v2.html".'
            )
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    fieldsets = (
        ('Restaurant Information', {
            'fields': ('restaurant_name', 'tagline', 'description', 'logo', 'favicon')
        }),
        ('Contact Information', {
            'fields': ('phone', 'email', 'address_line1', 'address_line2', 'city', 'state', 'zip_code', 'country')
        }),
        ('Hours of Operation', {
            'fields': ('hours_text',)
        }),
        ('Social Media', {
            'fields': ('facebook_url', 'instagram_url', 'twitter_url', 'yelp_url'),
            'classes': ('collapse',)
        }),
        ('Theme & Overlay', {
            'fields': ('active_theme', 'active_overlay'),
            'description': (
                'active_theme sets the base look of the site. '
                'active_overlay applies a seasonal or promotional style on top — '
                'only activates if its date range is current or Is Active is checked.'
            )
        }),
        ('Page Templates', {
            'fields': ('home_template', 'menu_template', 'promotions_template'),
            'description': 'Select which layout template to use for each page type.',
        }),
        ('SEO Settings', {
            'fields': ('meta_description', 'meta_keywords'),
            'classes': ('collapse',)
        }),
        ('Maintenance', {
            'fields': ('maintenance_mode', 'maintenance_message'),
            'classes': ('collapse',)
        }),
    )
