from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.utils.html import format_html, mark_safe
from media_manager.models import Media

from .models import (
    MenuCategory, MenuSubCategory,
    MenuItem, MenuItemVariation, MenuItemAddon,
    MenuItemCategoryAssignment,
    Menu, MenuCategoryAssignment,
    PromoColorScheme, PromoSettings,
)


# =============================================================================
# SHARED HELPERS
# =============================================================================

class MenuMediaInline(GenericTabularInline):
    model = Media
    ct_field = 'content_type'
    ct_fk_field = 'object_id'
    extra = 1
    fields = ['file', 'title', 'alt_text', 'is_featured', 'display_order', 'category']


def _save_media_formset(request, formset):
    """Shared helper — stamps uploaded_by on new Media instances."""
    instances = formset.save(commit=False)
    for instance in instances:
        if isinstance(instance, Media) and not instance.pk:
            instance.uploaded_by = request.user
            instance.is_user_generated = False
        instance.save()
    formset.save_m2m()


def _color_swatch(hex_value):
    """Small color swatch for list_display."""
    if not hex_value:
        return "—"
    return format_html(
        '<span style="display:inline-flex;align-items:center;gap:6px;">'
        '<span style="display:inline-block;width:20px;height:20px;border-radius:3px;'
        'background:{};border:1px solid rgba(0,0,0,.2);flex-shrink:0;"></span>'
        '<code style="font-size:11px;">{}</code>'
        '</span>',
        hex_value, hex_value,
    )


def _palette_preview(primary, accent, text, bg):
    """Four-slot palette strip for list_display and readonly_fields."""
    slots = [
        ('Primary', primary),
        ('Accent',  accent),
        ('Text',    text),
        ('BG',      bg),
    ]
    parts = []
    for label, val in slots:
        if val:
            parts.append(format_html(
                '<span style="display:inline-flex;flex-direction:column;'
                'align-items:center;gap:3px;margin-right:10px;">'
                '<span style="display:inline-block;width:32px;height:32px;'
                'border-radius:4px;background:{};border:1px solid rgba(0,0,0,.2);"></span>'
                '<span style="font-size:10px;color:#666;">{}</span>'
                '</span>',
                val, label,
            ))
        else:
            parts.append(format_html(
                '<span style="display:inline-flex;flex-direction:column;'
                'align-items:center;gap:3px;margin-right:10px;">'
                '<span style="display:inline-block;width:32px;height:32px;'
                'border-radius:4px;background:#f0f0f0;border:1px dashed #ccc;"></span>'
                '<span style="font-size:10px;color:#aaa;">{}</span>'
                '</span>',
                label,
            ))
    return mark_safe(
        '<span style="display:inline-flex;align-items:flex-end;">'
        + ''.join(str(p) for p in parts)
        + '</span>'
    )


# =============================================================================
# MENU CATEGORY
# =============================================================================


class CategoryItemAssignmentInline(admin.TabularInline):
    """
    Used inside MenuCategoryAdmin — shows which items are assigned to this
    category and lets staff add, reorder, and configure them directly.
    """
    model = MenuItemCategoryAssignment
    extra = 1
    fields = [
        'menu_item', 'subcategory', 'order',
        'override_price', 'available_game_day', 'note', 'is_active',
    ]
    autocomplete_fields = ['menu_item', 'subcategory']
    ordering = ['subcategory__order', 'order']
    verbose_name = 'Item'
    verbose_name_plural = 'Items in this Category'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'menu_item', 'subcategory'
        )

@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    list_display  = ['name', 'category_type', 'order', 'is_active', 'assigned_menu_count', 'item_count']
    list_editable = ['order', 'is_active']
    list_filter   = ['category_type', 'is_active']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [CategoryItemAssignmentInline, MenuMediaInline]

    def save_formset(self, request, form, formset, change):
        _save_media_formset(request, formset)

    @admin.display(description='Menus using this')
    def assigned_menu_count(self, obj):
        count = obj.menus.count()
        return count if count else '—'

    @admin.display(description='Items')
    def item_count(self, obj):
        count = obj.item_assignments.filter(is_active=True).count()
        return count if count else '—'


# =============================================================================
# MENU SUB-CATEGORY
# =============================================================================

@admin.register(MenuSubCategory)
class MenuSubCategoryAdmin(admin.ModelAdmin):
    list_display  = ['name', 'category', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter   = ['category__category_type', 'category']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}


# =============================================================================
# MENU ITEM
# =============================================================================

class MenuItemVariationInline(admin.TabularInline):
    model = MenuItemVariation
    extra = 0
    fields = ['name', 'price', 'size', 'quantity', 'is_default', 'is_available', 'order']


class MenuItemAddonInline(admin.TabularInline):
    model = MenuItemAddon
    extra = 0
    fields = ['name', 'price', 'is_default', 'is_available', 'order']


class MenuItemCategoryAssignmentInline(admin.TabularInline):
    """
    Used inside MenuItemAdmin — shows which categories this item is placed in.
    """
    model = MenuItemCategoryAssignment
    extra = 0
    fields = [
        'category', 'subcategory', 'order',
        'override_price', 'available_game_day', 'note', 'is_active',
    ]
    autocomplete_fields = ['category', 'subcategory']
    verbose_name = 'Category Placement'
    verbose_name_plural = 'Category Placements'



@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display  = [
        'name', 'display_price', 'is_available', 'is_featured',
        'is_chef_special', 'placement_summary',
    ]
    list_editable = ['is_available', 'is_featured']
    list_filter   = [
        'is_available', 'is_featured', 'is_chef_special',
        'is_seasonal', 'dietary_type',
        'category_assignments__category__category_type',
    ]
    search_fields = ['name', 'short_description']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [
        MenuItemVariationInline,
        MenuItemAddonInline,
        MenuItemCategoryAssignmentInline,
        MenuMediaInline,
    ]

    def save_formset(self, request, form, formset, change):
        _save_media_formset(request, formset)

    fieldsets = (
        ('Identity', {
            'fields': ('name', 'slug', 'short_description', 'description'),
        }),
        ('Pricing', {
            'fields': ('price_display', 'price', 'sale_price', 'has_variations', 'has_addons'),
        }),
        ('Dietary & Allergens', {
            'fields': (
                'dietary_type',
                'is_gluten_free', 'is_vegan', 'is_dairy_free',
                'is_nut_free', 'contains_shellfish',
                'allergen_info',
            ),
            'classes': ('collapse',),
        }),
        ('Details', {
            'fields': ('spice_level', 'calories', 'preparation_time'),
            'classes': ('collapse',),
        }),
        ('Features', {
            'fields': ('is_featured', 'is_chef_special', 'is_new', 'is_seasonal'),
        }),
        ('Availability', {
            'fields': ('is_available', 'available_from', 'available_until'),
        }),
    )

    @admin.display(description='Placed in')
    def placement_summary(self, obj):
        names = list(
            obj.category_assignments
            .filter(is_active=True)
            .select_related('category')
            .values_list('category__name', flat=True)
        )
        if not names:
            return format_html('<span style="color:#aaa;">—unassigned—</span>')
        return ', '.join(names)


# =============================================================================
# COLOR SCHEME
# =============================================================================

@admin.register(PromoColorScheme)
class PromoColorSchemeAdmin(admin.ModelAdmin):
    list_display  = ['name', 'palette_preview', 'is_default', 'menu_count', 'updated_at']
    list_editable = ['is_default']
    readonly_fields = ['palette_detail', 'created_at', 'updated_at']

    fieldsets = (
        (None, {
            'fields': ('name', 'is_default'),
        }),
        ('Colors', {
            'fields': (
                'palette_detail',
                'primary_color', 'accent_color', 'text_color', 'bg_color',
            ),
            'description': (
                'Enter hex values (e.g. <code>#ffb612</code>). '
                'The preview updates after saving.'
            ),
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Palette')
    def palette_preview(self, obj):
        return _palette_preview(
            obj.primary_color, obj.accent_color, obj.text_color, obj.bg_color
        )

    @admin.display(description='Menus using this')
    def menu_count(self, obj):
        count = obj.menus.count()
        return count if count else '—'

    @admin.display(description='Preview')
    def palette_detail(self, obj):
        primary = obj.primary_color or '#cccccc'
        accent  = obj.accent_color  or '#999999'
        text    = obj.text_color    or '#333333'
        bg      = obj.bg_color      or '#f5f5f5'
        return format_html(
            '<div style="margin-bottom:12px;">'
            '<div style="background:{bg};border:2px solid {primary};border-radius:6px;'
            'padding:16px 20px;max-width:420px;font-family:sans-serif;">'
            '<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">'
            '<span style="display:inline-block;width:12px;height:12px;border-radius:50%;'
            'background:{accent};"></span>'
            '<strong style="color:{primary};font-size:15px;">Menu Heading</strong>'
            '</div>'
            '<p style="color:{text};font-size:13px;margin:0 0 10px;">Sample menu description text.</p>'
            '<span style="display:inline-block;background:{primary};color:{bg};'
            'padding:6px 14px;border-radius:4px;font-size:12px;font-weight:bold;">'
            'View Menu</span>'
            '</div>'
            '<div style="margin-top:10px;display:flex;gap:6px;align-items:center;">'
            '{swatches}'
            '</div></div>',
            bg=bg, primary=primary, accent=accent, text=text,
            swatches=mark_safe(''.join([
                str(_color_swatch(obj.primary_color)),
                str(_color_swatch(obj.accent_color)),
                str(_color_swatch(obj.text_color)),
                str(_color_swatch(obj.bg_color)),
            ])),
        )


# =============================================================================
# PROMO SETTINGS  (singleton legacy fallback)
# =============================================================================

@admin.register(PromoSettings)
class PromoSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not PromoSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    fieldsets = (
        ('Global Color Fallback', {
            'description': (
                'Last-resort fallback colors when a menu has no color scheme assigned '
                'and no default scheme exists. '
                'Leave blank to fall back to theme.css defaults.'
            ),
            'fields': (
                'promo_primary_color', 'promo_accent_color',
                'promo_text_color', 'promo_bg_color',
            ),
        }),
    )


# =============================================================================
# MENU CATEGORY ASSIGNMENT INLINE
# (used inside MenuAdmin — declares which categories this menu uses)
# =============================================================================

class MenuCategoryAssignmentInline(admin.TabularInline):
    model = MenuCategoryAssignment
    extra = 1
    fields = ['category', 'display_order']
    autocomplete_fields = ['category']
    ordering = ['display_order']
    verbose_name = 'Category'
    verbose_name_plural = 'Categories (declared for this menu)'


# =============================================================================
# MENU ITEM CATEGORY ASSIGNMENT  (standalone admin for bulk management)
# =============================================================================

@admin.register(MenuItemCategoryAssignment)
class MenuItemCategoryAssignmentAdmin(admin.ModelAdmin):
    list_display = [
        'menu_item', 'category', 'subcategory',
        'display_price_col', 'override_price',
        'available_game_day', 'order', 'is_active',
    ]
    list_editable = ['order', 'available_game_day', 'is_active', 'override_price']
    list_filter   = [
        'category__category_type',
        'category',
        'available_game_day',
        'is_active',
    ]
    search_fields = ['menu_item__name', 'category__name']
    autocomplete_fields = ['menu_item', 'category', 'subcategory']

    @admin.display(description='Effective price')
    def display_price_col(self, obj):
        return obj.display_price


# =============================================================================
# MENU
# =============================================================================

@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display  = [
        'title', 'menu_type', 'is_default', 'is_active',
        'show_on_homepage', 'scheme_preview',
        'start_date', 'end_date',
    ]
    list_editable = ['is_active', 'show_on_homepage', 'is_default']
    list_filter   = ['menu_type', 'is_active', 'show_on_homepage', 'is_default']
    search_fields = ['title']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['resolved_palette_preview']
    inlines = [MenuCategoryAssignmentInline, MenuMediaInline]

    def save_formset(self, request, form, formset, change):
        _save_media_formset(request, formset)

    fieldsets = (
        ('Identity', {
            'fields': ('title', 'slug', 'description'),
        }),
        ('Type & Default', {
            'fields': ('menu_type', 'is_default'),
            'description': (
                'Set menu_type to Combined for the main site menu. '
                'One menu per type can be flagged as the default — '
                'this is what renders on the main menu pages.'
            ),
        }),
        ('Color Scheme', {
            'fields': ('color_scheme', 'resolved_palette_preview'),
            'description': (
                'Assign a color scheme or leave blank to use the default. '
                'Primarily useful for promotional menus.'
            ),
        }),
        ('Schedule', {
            'fields': ('start_date', 'end_date'),
            'classes': ('collapse',),
            'description': 'Leave both blank for a permanently active menu.',
        }),
        ('Display', {
            'fields': ('is_active', 'show_on_homepage'),
        }),
    )

    @admin.display(description='Scheme')
    def scheme_preview(self, obj):
        scheme = obj.color_scheme
        if scheme is None:
            scheme = PromoColorScheme.objects.filter(is_default=True).first()
        if scheme is None:
            return '—'
        preview = _palette_preview(
            scheme.primary_color, scheme.accent_color,
            scheme.text_color, scheme.bg_color,
        )
        label = f"{scheme.name} (default)" if obj.color_scheme is None else scheme.name
        return format_html(
            '{}<br><span style="font-size:11px;color:#666;">{}</span>',
            preview, label,
        )

    @admin.display(description='Resolved palette')
    def resolved_palette_preview(self, obj):
        colors = obj.resolve_colors()
        if obj.color_scheme_id:
            source = obj.color_scheme.name
        else:
            default_scheme = PromoColorScheme.objects.filter(is_default=True).first()
            source = (
                f"{default_scheme.name} (default)"
                if default_scheme else
                "legacy PromoSettings fallback"
            )
        return format_html(
            '{}<div style="margin-top:4px;font-size:11px;color:#666;">Source: {}</div>',
            _palette_preview(
                colors['primary'], colors['accent'],
                colors['text'],    colors['bg'],
            ),
            source,
        )
