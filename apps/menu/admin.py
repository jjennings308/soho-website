from django.contrib import admin
from adminsortable2.admin import SortableAdminMixin, SortableInlineAdminMixin
from .models import MenuCategory, MenuItem, MenuItemImage


@admin.register(MenuCategory)
class MenuCategoryAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ['name', 'slug', 'order', 'is_active', 'item_count']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'icon')
        }),
        ('Display Settings', {
            'fields': ('order', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = 'Number of Items'


class MenuItemImageInline(SortableInlineAdminMixin, admin.TabularInline):
    model = MenuItemImage
    extra = 0
    fields = ['image', 'alt_text', 'caption', 'order']


@admin.register(MenuItem)
class MenuItemAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = [
        'name', 'category', 'current_price', 'is_available', 
        'is_featured', 'dietary_type', 'order'
    ]
    list_filter = [
        'category', 'is_available', 'is_featured', 'is_chef_special',
        'dietary_type', 'is_gluten_free', 'is_vegan', 'created_at'
    ]
    search_fields = ['name', 'description', 'short_description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at', 'current_price_display']
    inlines = [MenuItemImageInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('category', 'name', 'slug', 'short_description', 'description')
        }),
        ('Pricing', {
            'fields': ('price', 'sale_price', 'current_price_display')
        }),
        ('Images', {
            'fields': ('image', 'image_alt_text')
        }),
        ('Dietary Information', {
            'fields': (
                'dietary_type', 'is_gluten_free', 'is_dairy_free', 
                'is_nut_free', 'contains_shellfish', 'allergen_info'
            ),
            'classes': ('collapse',)
        }),
        ('Additional Details', {
            'fields': ('spice_level', 'calories', 'preparation_time'),
            'classes': ('collapse',)
        }),
        ('Features & Highlights', {
            'fields': (
                'is_featured', 'is_chef_special', 'is_new', 'is_seasonal'
            )
        }),
        ('Availability', {
            'fields': ('is_available', 'available_from', 'available_until')
        }),
        ('Display Order', {
            'fields': ('order',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def current_price_display(self, obj):
        if obj.is_on_sale:
            return f"${obj.current_price} (Sale from ${obj.price})"
        return f"${obj.current_price}"
    current_price_display.short_description = 'Current Price'
    
    actions = ['make_available', 'make_unavailable', 'mark_as_featured', 'unmark_as_featured']
    
    def make_available(self, request, queryset):
        count = queryset.update(is_available=True)
        self.message_user(request, f'{count} items marked as available.')
    make_available.short_description = 'Mark selected items as available'
    
    def make_unavailable(self, request, queryset):
        count = queryset.update(is_available=False)
        self.message_user(request, f'{count} items marked as unavailable.')
    make_unavailable.short_description = 'Mark selected items as unavailable'
    
    def mark_as_featured(self, request, queryset):
        count = queryset.update(is_featured=True)
        self.message_user(request, f'{count} items marked as featured.')
    mark_as_featured.short_description = 'Mark as featured'
    
    def unmark_as_featured(self, request, queryset):
        count = queryset.update(is_featured=False)
        self.message_user(request, f'{count} items unmarked as featured.')
    unmark_as_featured.short_description = 'Remove featured status'
