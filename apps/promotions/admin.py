from django.contrib import admin
from django.utils import timezone
from adminsortable2.admin import SortableAdminBase, SortableAdminMixin, SortableInlineAdminMixin
from .models import PromotionCategory, Promotion, PromotionImage


@admin.register(PromotionCategory)
class PromotionCategoryAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ['name', 'slug', 'color_code', 'order', 'is_active', 'promotion_count']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description')
        }),
        ('Display Settings', {
            'fields': ('color_code', 'icon', 'order', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def promotion_count(self, obj):
        return obj.promotions.count()
    promotion_count.short_description = 'Number of Promotions'


class PromotionImageInline(SortableInlineAdminMixin, admin.TabularInline):
    model = PromotionImage
    extra = 0
    fields = ['image', 'alt_text', 'caption', 'order']


@admin.register(Promotion)
class PromotionAdmin(SortableAdminBase, admin.ModelAdmin):
    list_display = [
        'title', 'category', 'start_date', 'start_time',
        'status', 'is_featured', 'promotion_status_indicator'
    ]
    list_filter = [
        'status', 'category', 'is_featured', 'is_special',
        'has_registration', 'is_free', 'start_date', 'created_at'
    ]
    search_fields = ['title', 'description', 'short_description']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = [
        'created_at', 'updated_at', 'published_date',
        'promotion_status_indicator', 'spots_remaining_display'
    ]
    inlines = [PromotionImageInline]
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'category', 'short_description', 'description')
        }),
        ('Images', {
            'fields': ('featured_image', 'image_alt_text')
        }),
        ('Date & Time', {
            'fields': (
                'start_date', 'start_time', 'end_date', 'end_time',
                'recurrence_type', 'recurrence_end_date'
            )
        }),
        ('Registration & Capacity', {
            'fields': (
                'has_registration', 'max_capacity', 'current_registrations',
                'spots_remaining_display', 'registration_deadline'
            ),
            'classes': ('collapse',)
        }),
        ('Pricing', {
            'fields': ('is_free', 'price')
        }),
        ('Contact Information', {
            'fields': ('contact_email', 'contact_phone', 'external_url'),
            'classes': ('collapse',)
        }),
        ('Features', {
            'fields': ('is_featured', 'is_special')
        }),
        ('Publishing', {
            'fields': ('status', 'published_date')
        }),
        ('SEO', {
            'fields': ('meta_description',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def promotion_status_indicator(self, obj):
        if obj.is_past:
            return '🔴 Past'
        elif obj.is_ongoing:
            return '🟢 Ongoing'
        elif obj.is_upcoming:
            return '🟡 Upcoming'
        return '⚪ Unknown'
    promotion_status_indicator.short_description = 'Time Status'
    
    def spots_remaining_display(self, obj):
        if not obj.has_registration:
            return 'N/A'
        if not obj.max_capacity:
            return 'Unlimited'
        remaining = obj.spots_remaining
        if remaining == 0:
            return '🔴 FULL'
        elif remaining <= 5:
            return f'⚠️ {remaining} spots left'
        return f'✅ {remaining} spots available'
    spots_remaining_display.short_description = 'Availability'
    
    actions = [
        'publish_promotions', 'unpublish_promotions', 'mark_as_featured',
        'unmark_as_featured', 'mark_as_completed'
    ]
    
    def publish_promotions(self, request, queryset):
        count = queryset.filter(status='draft').update(
            status='published',
            published_date=timezone.now()
        )
        self.message_user(request, f'{count} promotions published.')
    publish_promotions.short_description = 'Publish selected promotions'
    
    def unpublish_promotions(self, request, queryset):
        count = queryset.filter(status='published').update(status='draft')
        self.message_user(request, f'{count} promotions unpublished.')
    unpublish_promotions.short_description = 'Unpublish selected promotions'
    
    def mark_as_featured(self, request, queryset):
        count = queryset.update(is_featured=True)
        self.message_user(request, f'{count} promotions marked as featured.')
    mark_as_featured.short_description = 'Mark as featured'
    
    def unmark_as_featured(self, request, queryset):
        count = queryset.update(is_featured=False)
        self.message_user(request, f'{count} promotions unmarked as featured.')
    unmark_as_featured.short_description = 'Remove featured status'
    
    def mark_as_completed(self, request, queryset):
        count = queryset.update(status='completed')
        self.message_user(request, f'{count} promotions marked as completed.')
    mark_as_completed.short_description = 'Mark as completed'
