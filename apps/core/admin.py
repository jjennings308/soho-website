from django.contrib import admin
from django.utils.html import format_html
from .models import EventInquiry, Review, SitePopup, SiteSettings, Banner, BannerImage, PanelSide


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
            'fields': ('phone', 'email', 'address_line1', 'address_line2', 'city', 'state', 'zip_code', 'country', 'reservations_url', 'map_embed_url')
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
        ('Online Delivery', {
            'fields': ('doordash_url', 'grubhub_url', 'ubereats_url'),
            'classes': ('collapse',),
            'description': 'Store page URLs for each delivery platform. Leave blank to hide that card on the delivery page.',
        }),
        ('Review Platform Links', {
            'fields': ('google_review_url', 'yelp_review_url', 'opentable_review_url', 'rewardsnetwork_review_url'),
            'classes': ('collapse',),
            'description': 'Links shown on the Reviews page so visitors can leave a review.',
        }),
    )
    
class BannerImageInline(admin.TabularInline):
    model = BannerImage
    extra = 1
    fields = ['media_item', 'is_active', 'display_order']
    ordering = ['display_order']


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ['label', 'slug', 'bg_color', 'image_only', 'is_active']
    list_editable = ['is_active']
    list_filter = ['is_active', 'image_only']
    search_fields = ['label', 'slug']
    readonly_fields = ['slug']
    inlines = [BannerImageInline]

    fieldsets = (
        ('Identity', {
            'fields': ('slug', 'label', 'is_active'),
            'description': 'Slug is set on creation and cannot be changed — templates reference it by slug.'
        }),
        ('Content', {
            'fields': ('content_group',),
            'description': (
                'Assign a ContentGroup to supply title, body, and button slots. '
                'When set, the ContentGroup takes precedence over the legacy Title/Body fields below.'
            )
        }),
        ('Legacy Content (used until ContentGroup is assigned)', {
            'fields': ('title', 'content'),
            'classes': ('collapse',),
        }),
        ('Appearance', {
            'fields': ('bg_color', 'text_color', 'image_alt', 'image_opacity', 'image_only'),
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields
        return []
    
@admin.register(PanelSide)
class PanelSideAdmin(admin.ModelAdmin):
    list_display = ['label', 'slug', 'component', 'bg_color', 'is_active']
    list_editable = ['is_active']
    list_filter = ['component', 'is_active']
    search_fields = ['label', 'slug']
    readonly_fields = ['slug']

    fieldsets = (
        ('Identity', {
            'fields': ('slug', 'label', 'is_active'),
            'description': 'Slug is set on creation and cannot be changed.'
        }),
        ('Component', {
            'fields': ('component',),
            'description': (
                'Controls what this panel renders. '
                '<strong>Content</strong> — assign a ContentGroup below. '
                '<strong>Map</strong> — uses the Google Maps embed URL from Site Settings. '
                '<strong>Full-bleed Image</strong> — select an image from the media library.'
            )
        }),
        ('Content (component = Content)', {
            'fields': ('content_group',),
            'classes': ('collapse',),
        }),
        ('Image (component = Full-bleed Image)', {
            'fields': ('image',),
            'classes': ('collapse',),
        }),
        ('Appearance', {
            'fields': ('bg_color', 'text_color', 'vertical_align', 'horizontal_align'),
        }),
        ('Image / Fallback', {
            'fields': ('image_alt', 'image_fallback_url'),
            'classes': ('collapse',),
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields
        return []

@admin.register(EventInquiry)
class EventInquiryAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'event_type', 'preferred_date', 'menu_preference', 'status', 'created_at']
    list_filter = ['status', 'event_type', 'menu_preference']
    search_fields = ['name', 'email', 'phone']
    list_editable = ['status']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(SitePopup)
class SitePopupAdmin(admin.ModelAdmin):
    list_display = ['title', 'heading', 'is_active', 'show_delay', 'created_at']
    list_filter = ['is_active']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['reviewer_name', 'rating', 'source', 'is_featured', 'is_active', 'display_order', 'created_at']
    list_editable = ['is_featured', 'is_active', 'display_order']
    list_filter = ['source', 'is_featured', 'is_active', 'rating']
    search_fields = ['reviewer_name', 'reviewer_location', 'body']
    readonly_fields = ['created_at', 'updated_at']
