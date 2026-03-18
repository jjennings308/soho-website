from django.contrib import admin
from .models import Theme, ThemeStyle, ThemeOverlay, SiteSettings


@admin.register(ThemeStyle)
class ThemeStyleAdmin(admin.ModelAdmin):
    list_display = ['name', 'primary_font', 'secondary_font', 'accent_font', 'updated_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description')
        }),
        ('Typography', {
            'fields': ('primary_font', 'secondary_font', 'accent_font'),
            'description': (
                'Fonts used for headings, body text, and accents. '
                'All colors are brand constants defined in theme.css — not configurable here.'
            )
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
                'base_style defines the fonts for this theme. '
                'Colors are brand constants in theme.css.'
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
            'fields': ('restaurant_name', 'logo', 'favicon')
        }),
        ('Contact Information', {
            'fields': ('phone', 'email', 'address_line1', 'address_line2', 'city', 'state', 'zip_code', 'country')
        }),
        ('Social Media', {
            'fields': ('facebook_url', 'instagram_url', 'twitter_url', 'yelp_url'),
            'classes': ('collapse',)
        }),
        ('Theme & Overlay', {
            'fields': ('active_theme', 'active_overlay'),
            'description': (
                'active_theme sets the base fonts for the site. '
                'active_overlay applies a seasonal font style on top — '
                'only activates if its date range is current or Is Active is checked. '
                'Colors are brand constants and are not affected by theme or overlay selection.'
            )
        }),
        ('SEO Settings', {
            'fields': ('meta_description', 'meta_keywords'),
            'classes': ('collapse',)
        }),
        ('Maintenance', {
            'fields': ('maintenance_mode',),
            'classes': ('collapse',)
        }),
    )