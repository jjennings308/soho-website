from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.utils.html import format_html
from media_manager.models import Media
from .models import SiteSettings, Banner, BannerButton, PanelSide


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
            'fields': ('phone', 'email', 'address_line1', 'address_line2', 'city', 'state', 'zip_code', 'country', 'reservations_url')
        }),
        ('Social Media', {
            'fields': ('facebook_url', 'instagram_url', 'twitter_url', 'yelp_url'),
            'classes': ('collapse',)
        }),
        ('SEO Settings', {
            'fields': ('meta_description', 'meta_keywords'),
            'classes': ('collapse',)
        }),
        ('Maintenance', {
            'fields': ('maintenance_mode',),
            'classes': ('collapse',)
        }),
        ('Event Day / Game Day Overrides', {
            'fields': ('force_game_day_mode', 'force_full_menu'),
            'classes': ('collapse',),
            'description': (
                'Manual overrides for the event calendar. '
                '<strong>force_full_menu takes precedence over force_game_day_mode.</strong> '
                'Remember to uncheck these after the situation passes — '
                'they are not cleared automatically.'
            ),
        }),
    )
    
class BannerButtonInline(admin.TabularInline):
    model = BannerButton
    extra = 1
    fields = ['label', 'href', 'bg_color', 'text_color', 'order', 'is_active']
    ordering = ['order']


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ['label', 'slug', 'bg_color', 'image_only', 'is_active']
    list_editable = ['is_active']
    list_filter = ['is_active', 'image_only']
    search_fields = ['label', 'slug']
    readonly_fields = ['slug']
    inlines = [BannerButtonInline]

    fieldsets = (
        ('Identity', {
            'fields': ('slug', 'label', 'is_active'),
            'description': 'Slug is set on creation and cannot be changed — templates reference it by slug.'
        }),
        ('Content', {
            'fields': ('title', 'content'),
            'description': (
                'Boilerplate copy. Override per-season via the ContentBlock '
                'with slug <code>banner_{slug}_seasonal</code> in the Content admin.'
            )
        }),
        ('Appearance', {
            'fields': ('bg_color', 'text_color', 'image', 'image_opacity', 'image_only'),
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields
        return []
    
@admin.register(PanelSide)
class PanelSideAdmin(admin.ModelAdmin):
    list_display = ['label', 'slug', 'mode', 'bg_color', 'is_active']
    list_editable = ['is_active']
    list_filter = ['mode', 'is_active']
    search_fields = ['label', 'slug']
    readonly_fields = ['slug']

    fieldsets = (
        ('Identity', {
            'fields': ('slug', 'label', 'mode', 'is_active'),
            'description': 'Slug is set on creation and cannot be changed.'
        }),
        ('Image Mode', {
            'fields': ('image', 'image_fallback_url', 'bg_color'),
            'description': 'Used when mode is set to Full Image.',
            'classes': ('collapse',),
        }),
        ('Text Mode', {
            'fields': ('title', 'content_slot', 'text_color', 'vertical_align', 'horizontal_align'),
            'description': 'Used when mode is set to Text & Button.',
            'classes': ('collapse',),
        }),
        ('Button', {
            'fields': ('button_label', 'button_href', 'button_bg_color', 'button_text_color'),
            'description': 'Optional. Only renders if both label and href are set.',
            'classes': ('collapse',),
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields
        return []