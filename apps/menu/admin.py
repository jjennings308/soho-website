"""
Django admin configuration for menu models with variations support
Place this in: <your_app>/admin.py
"""

from django.contrib import admin
from .models import MenuType, MenuCategory, MenuItem, MenuItemVariation, MenuItemAddon, MenuItemImage


class MenuCategoryInline(admin.TabularInline):
    """Inline admin for categories within a menu type"""
    model = MenuCategory
    extra = 1
    fields = ('name', 'slug', 'order', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order', 'name']
    show_change_link = True


@admin.register(MenuType)
class MenuTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'is_active', 'category_count', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order', 'name']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description')
        }),
        ('Display Settings', {
            'fields': ('order', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('created_at', 'updated_at')
    inlines = [MenuCategoryInline]

    def category_count(self, obj):
        return obj.categories.count()
    category_count.short_description = 'Categories'


class MenuItemVariationInline(admin.TabularInline):
    """Inline admin for menu item variations"""
    model = MenuItemVariation
    extra = 1
    fields = ('name', 'price', 'quantity', 'size', 'order', 'is_default', 'is_available')
    ordering = ['order', 'price']

class MenuItemAddonInline(admin.TabularInline):
    """Inline admin for menu item add-ons"""
    model = MenuItemAddon
    extra = 1
    fields = ('name', 'price', 'order', 'is_default', 'is_available')
    ordering = ['order', 'price']


class MenuItemImageInline(admin.TabularInline):
    """Inline admin for menu item images"""
    model = MenuItemImage
    extra = 1
    fields = ('image', 'alt_text', 'caption', 'order')
    ordering = ['order']


@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'menu_type', 'order', 'is_active', 'item_count', 'created_at')
    list_filter = ('menu_type', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['menu_type__order', 'order', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('menu_type', 'name', 'slug', 'description', 'icon')
        }),
        ('Display Settings', {
            'fields': ('order', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def item_count(self, obj):
        """Display count of items in this category"""
        return obj.items.count()
    item_count.short_description = 'Items'


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_menu_type', 'category', 'get_price_display', 'has_variations',
                    'has_addons', 'is_featured', 'is_available', 'dietary_type', 'order')
    list_filter = ('category__menu_type', 'category', 'is_featured', 'is_chef_special',
                   'is_available', 'dietary_type', 'has_variations', 'has_addons', 'created_at')
    search_fields = ('name', 'description', 'short_description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['category__menu_type__order', 'category__order', 'order', 'name']
    
    inlines = [MenuItemVariationInline, MenuItemAddonInline, MenuItemImageInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('category', 'name', 'slug', 'description', 'short_description')
        }),
        ('Pricing', {
            'fields': ('price', 'sale_price', 'has_variations', 'has_addons')
        }),
        ('Images', {
            'fields': ('image', 'image_alt_text')
        }),
        ('Dietary & Allergen Information', {
            'fields': ('dietary_type', 'is_gluten_free', 'is_vegan', 'is_dairy_free', 
                      'is_nut_free', 'contains_shellfish', 'allergen_info'),
            'classes': ('collapse',)
        }),
        ('Additional Details', {
            'fields': ('spice_level', 'calories', 'preparation_time'),
            'classes': ('collapse',)
        }),
        ('Features', {
            'fields': ('is_featured', 'is_chef_special', 'is_new', 'is_seasonal')
        }),
        ('Availability', {
            'fields': ('is_available', 'available_from', 'available_until')
        }),
        ('Display Order', {
            'fields': ('order',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')

    def get_menu_type(self, obj):
        return obj.category.menu_type.name
    get_menu_type.short_description = 'Type'
    get_menu_type.admin_order_field = 'category__menu_type__name'
    
    def get_price_display(self, obj):
        """Display price or price range"""
        if obj.has_variations:
            price_range = obj.price_range
            return f"{price_range} (varies)" if price_range else f"${obj.price} (varies)"
        elif obj.sale_price:
            return f"${obj.sale_price} (was ${obj.price})"
        return f"${obj.price}"
    get_price_display.short_description = 'Price'
    get_price_display.admin_order_field = 'price'
    
    actions = ['mark_as_featured', 'mark_as_available', 'mark_as_unavailable']
    
    def mark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} item(s) marked as featured.')
    mark_as_featured.short_description = 'Mark selected as featured'
    
    def mark_as_available(self, request, queryset):
        updated = queryset.update(is_available=True)
        self.message_user(request, f'{updated} item(s) marked as available.')
    mark_as_available.short_description = 'Mark selected as available'
    
    def mark_as_unavailable(self, request, queryset):
        updated = queryset.update(is_available=False)
        self.message_user(request, f'{updated} item(s) marked as unavailable.')
    mark_as_unavailable.short_description = 'Mark selected as unavailable'


@admin.register(MenuItemVariation)
class MenuItemVariationAdmin(admin.ModelAdmin):
    list_display = ('get_item_name', 'name', 'price', 'quantity', 'size', 
                   'is_default', 'is_available', 'order')
    list_filter = ('menu_item__category__menu_type', 'menu_item__category', 'is_default', 'is_available')
    search_fields = ('menu_item__name', 'name', 'description')
    ordering = ['menu_item__category__menu_type__order', 'menu_item__category__order', 'menu_item__order', 'order', 'price']
    
    fieldsets = (
        ('Menu Item', {
            'fields': ('menu_item',)
        }),
        ('Variation Details', {
            'fields': ('name', 'description', 'price')
        }),
        ('Size/Quantity', {
            'fields': ('quantity', 'size')
        }),
        ('Settings', {
            'fields': ('order', 'is_default', 'is_available')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def get_item_name(self, obj):
        return obj.menu_item.name
    get_item_name.short_description = 'Menu Item'
    get_item_name.admin_order_field = 'menu_item__name'


@admin.register(MenuItemAddon)
class MenuItemAddonAdmin(admin.ModelAdmin):
    list_display = ('get_item_name', 'name', 'price',   
                   'is_default', 'is_available', 'order')
    list_filter = ('menu_item__category__menu_type', 'menu_item__category', 'is_default', 'is_available')
    search_fields = ('menu_item__name', 'name', 'description')
    ordering = ['menu_item__category__menu_type__order', 'menu_item__category__order', 'menu_item__order', 'order', 'price']
    
    fieldsets = (
        ('Menu Item', {
            'fields': ('menu_item',)
        }),
        ('Add-on Details', {
            'fields': ('name', 'description', 'price')
        }),
        ('Settings', {
            'fields': ('order', 'is_default', 'is_available')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def get_item_name(self, obj):
        return obj.menu_item.name
    get_item_name.short_description = 'Menu Item'
    get_item_name.admin_order_field = 'menu_item__name'


@admin.register(MenuItemImage)
class MenuItemImageAdmin(admin.ModelAdmin):
    list_display = ('get_item_name', 'image', 'caption', 'order', 'created_at')
    list_filter = ('menu_item__category__menu_type', 'menu_item__category', 'created_at')
    search_fields = ('menu_item__name', 'alt_text', 'caption')
    ordering = ['menu_item__category__menu_type__order', 'menu_item__category__order', 'menu_item__order', 'order']
    
    fieldsets = (
        ('Menu Item', {
            'fields': ('menu_item',)
        }),
        ('Image', {
            'fields': ('image', 'alt_text', 'caption')
        }),
        ('Display Order', {
            'fields': ('order',)
        }),
        ('Timestamp', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at',)
    
    def get_item_name(self, obj):
        return obj.menu_item.name
    get_item_name.short_description = 'Menu Item'
    get_item_name.admin_order_field = 'menu_item__name'
