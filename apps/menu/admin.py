from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from media_manager.models import Media
from .models import (
    MenuType, MenuCategory, MenuSubCategory,
    MenuItem, MenuItemVariation, MenuItemAddon,
    PromoColorScheme, PromoSettings, MenuPromotion, MenuPromotionItem,
)


# ---------------------------------------------------------------------------
# Shared Media Inline
# ---------------------------------------------------------------------------

class MenuMediaInline(GenericTabularInline):
    model = Media
    ct_field = 'content_type'
    ct_fk_field = 'object_id'
    extra = 1
    fields = ['file', 'title', 'alt_text', 'is_featured', 'display_order', 'category']


# ---------------------------------------------------------------------------
# Menu Type
# ---------------------------------------------------------------------------

@admin.register(MenuType)
class MenuTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'order']
    list_editable = ['is_active', 'order']
    prepopulated_fields = {'slug': ('name',)}


# ---------------------------------------------------------------------------
# Menu Category
# ---------------------------------------------------------------------------

@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'menu_type', 'is_active', 'order']
    list_editable = ['is_active', 'order']
    list_filter = ['menu_type']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [MenuMediaInline]

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, Media) and not instance.pk:
                instance.uploaded_by = request.user
                instance.is_user_generated = False
            instance.save()
        formset.save_m2m()


# ---------------------------------------------------------------------------
# Menu SubCategory
# ---------------------------------------------------------------------------

@admin.register(MenuSubCategory)
class MenuSubCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_active', 'order']
    list_editable = ['is_active', 'order']
    list_filter = ['category__menu_type', 'category']
    prepopulated_fields = {'slug': ('name',)}


# ---------------------------------------------------------------------------
# Menu Item
# ---------------------------------------------------------------------------

class MenuItemVariationInline(admin.TabularInline):
    model = MenuItemVariation
    extra = 0
    fields = ['name', 'price', 'size', 'quantity', 'is_default', 'is_available', 'order']


class MenuItemAddonInline(admin.TabularInline):
    model = MenuItemAddon
    extra = 0
    fields = ['name', 'price', 'is_default', 'is_available', 'order']


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'subcategory', 'display_price', 'is_available', 'is_featured', 'is_chef_special', 'order']
    list_editable = ['is_available', 'is_featured', 'order']
    list_filter = ['category__menu_type', 'category', 'is_available', 'is_featured', 'is_chef_special', 'is_seasonal', 'dietary_type']
    search_fields = ['name', 'short_description']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [MenuItemVariationInline, MenuItemAddonInline, MenuMediaInline]

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, Media) and not instance.pk:
                instance.uploaded_by = request.user
                instance.is_user_generated = False
            instance.save()
        formset.save_m2m()

    fieldsets = (
        ('Basic Information', {
            'fields': ('category', 'subcategory', 'name', 'slug', 'short_description', 'description')
        }),
        ('Pricing', {
            'fields': ('price_display', 'price', 'sale_price', 'has_variations', 'has_addons')
        }),
        ('Dietary & Allergens', {
            'fields': (
                'dietary_type',
                'is_gluten_free', 'is_vegan', 'is_dairy_free', 'is_nut_free', 'contains_shellfish',
                'allergen_info',
            ),
            'classes': ('collapse',)
        }),
        ('Details', {
            'fields': ('spice_level', 'calories', 'preparation_time'),
            'classes': ('collapse',)
        }),
        ('Features', {
            'fields': ('is_featured', 'is_chef_special', 'is_new','is_seasonal')
        }),
        ('Availability', {
            'fields': ('is_available', 'available_from', 'available_until', 'order'),
        }),
    )


# ---------------------------------------------------------------------------
# Promotional Menu
# ---------------------------------------------------------------------------

class MenuPromotionItemInline(admin.TabularInline):
    model = MenuPromotionItem
    extra = 0
    fields = ['menu_item', 'name', 'promo_price', 'note', 'order']
    autocomplete_fields = ['menu_item']


@admin.register(PromoColorScheme)
class PromoColorSchemeAdmin(admin.ModelAdmin):
    list_display = ['name', 'primary_color', 'accent_color', 'bg_color', 'is_default']
    list_editable = ['is_default']


@admin.register(PromoSettings)
class PromoSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not PromoSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    fieldsets = (
        ('Global Promo Color Fallback', {
            'description': 'Used only when a promotion has no color scheme and no default scheme exists.',
            'fields': ('promo_primary_color', 'promo_accent_color', 'promo_text_color', 'promo_bg_color')
        }),
    )


@admin.register(MenuPromotion)
class MenuPromotionAdmin(admin.ModelAdmin):
    list_display = ['title', 'color_scheme', 'is_active', 'show_on_homepage', 'start_date', 'end_date']
    list_editable = ['is_active', 'show_on_homepage']
    list_filter = ['is_active', 'show_on_homepage']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [MenuPromotionItemInline, MenuMediaInline]

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, Media) and not instance.pk:
                instance.uploaded_by = request.user
                instance.is_user_generated = False
            instance.save()
        formset.save_m2m()

    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'description', 'color_scheme')
        }),
        ('Schedule', {
            'fields': ('start_date', 'end_date'),
            'classes': ('collapse',)
        }),
        ('Display', {
            'fields': ('is_active', 'show_on_homepage')
        }),
    )