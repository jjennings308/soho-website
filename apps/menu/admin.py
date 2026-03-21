from django.contrib import admin
from django.utils.html import format_html
from .models import (
    MenuType, MenuCategory, MenuSubCategory,
    MenuItem, MenuItemVariation, MenuItemAddon, MenuItemImage,
    PromoColorScheme, PromoSettings, MenuPromotion, MenuPromotionItem,
)


# =============================================================================
# MENU STRUCTURE
# =============================================================================

class MenuCategoryInline(admin.TabularInline):
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
    readonly_fields = ('created_at', 'updated_at')
    inlines = [MenuCategoryInline]

    fieldsets = (
        ('Basic Information', {'fields': ('name', 'slug', 'description')}),
        ('Display Settings', {'fields': ('order', 'is_active')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def category_count(self, obj):
        return obj.categories.count()
    category_count.short_description = 'Categories'


@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'menu_type', 'order', 'is_active', 'item_count', 'created_at')
    list_filter = ('menu_type', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['menu_type__order', 'order', 'name']
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Basic Information', {'fields': ('menu_type', 'name', 'slug', 'description', 'icon')}),
        ('Display Settings', {'fields': ('order', 'is_active')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = 'Items'


@admin.register(MenuSubCategory)
class MenuSubCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'get_menu_type', 'order', 'is_active', 'item_count', 'created_at')
    list_filter = ('category__menu_type', 'category', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['category__menu_type__order', 'category__order', 'order', 'name']
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Basic Information', {'fields': ('category', 'name', 'slug', 'description')}),
        ('Display Settings', {'fields': ('order', 'is_active')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def get_menu_type(self, obj):
        return obj.category.menu_type.name
    get_menu_type.short_description = 'Type'
    get_menu_type.admin_order_field = 'category__menu_type__name'

    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = 'Items'


# =============================================================================
# MENU ITEMS
# =============================================================================

class MenuItemVariationInline(admin.TabularInline):
    model = MenuItemVariation
    extra = 1
    fields = ('name', 'price', 'quantity', 'size', 'order', 'is_default', 'is_available')
    ordering = ['order', 'price']


class MenuItemAddonInline(admin.TabularInline):
    model = MenuItemAddon
    extra = 1
    fields = ('name', 'price', 'order', 'is_default', 'is_available')
    ordering = ['order', 'price']


class MenuItemImageInline(admin.TabularInline):
    model = MenuItemImage
    extra = 1
    fields = ('image', 'alt_text', 'caption', 'order')
    ordering = ['order']


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'get_menu_type', 'category', 'price_display',
        'get_price_display', 'has_variations', 'has_addons',
        'is_featured', 'is_available', 'dietary_type', 'order'
    )
    list_filter = (
        'category__menu_type', 'category', 'is_featured', 'is_chef_special',
        'is_available', 'dietary_type', 'has_addons', 'created_at'
    )
    search_fields = ('name', 'description', 'short_description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['category__menu_type__order', 'category__order', 'order', 'name']
    readonly_fields = ('created_at', 'updated_at')
    inlines = [MenuItemVariationInline, MenuItemAddonInline, MenuItemImageInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('category', 'subcategory', 'name', 'slug', 'description', 'short_description')
        }),
        ('Pricing', {
            'fields': ('price_display', 'price', 'sale_price', 'has_variations', 'has_addons')
        }),
        ('Images', {
            'fields': ('image', 'image_alt_text')
        }),
        ('Dietary & Allergen Information', {
            'fields': (
                'dietary_type', 'is_gluten_free', 'is_vegan', 'is_dairy_free',
                'is_nut_free', 'contains_shellfish', 'allergen_info'
            ),
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
        ('Display Order', {'fields': ('order',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    actions = ['mark_as_featured', 'mark_as_available', 'mark_as_unavailable']

    def get_menu_type(self, obj):
        return obj.category.menu_type.name
    get_menu_type.short_description = 'Type'
    get_menu_type.admin_order_field = 'category__menu_type__name'

    def get_price_display(self, obj):
        if obj.price_display == 'market':
            return "MP"
        if obj.price_display == 'hidden':
            return "—"
        if obj.has_variations:
            return obj.price_range or "See Options"
        if obj.sale_price is not None:
            return f"${obj.sale_price} (sale)"
        return f"${obj.price}" if obj.price is not None else "—"
    get_price_display.short_description = 'Price'
    get_price_display.admin_order_field = 'price'

    def mark_as_featured(self, request, queryset):
        queryset.update(is_featured=True)
    mark_as_featured.short_description = 'Mark selected as featured'

    def mark_as_available(self, request, queryset):
        queryset.update(is_available=True)
    mark_as_available.short_description = 'Mark selected as available'

    def mark_as_unavailable(self, request, queryset):
        queryset.update(is_available=False)
    mark_as_unavailable.short_description = 'Mark selected as unavailable'

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(MenuItemVariation)
class MenuItemVariationAdmin(admin.ModelAdmin):
    list_display = ('get_item_name', 'name', 'price', 'quantity', 'size', 'is_default', 'is_available', 'order')
    list_filter = ('menu_item__category__menu_type', 'menu_item__category', 'is_default', 'is_available')
    search_fields = ('menu_item__name', 'name', 'description')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Menu Item', {'fields': ('menu_item',)}),
        ('Variation Details', {'fields': ('name', 'description', 'price')}),
        ('Size/Quantity', {'fields': ('quantity', 'size')}),
        ('Settings', {'fields': ('order', 'is_default', 'is_available')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def get_item_name(self, obj):
        return obj.menu_item.name
    get_item_name.short_description = 'Menu Item'
    get_item_name.admin_order_field = 'menu_item__name'


@admin.register(MenuItemAddon)
class MenuItemAddonAdmin(admin.ModelAdmin):
    list_display = ('get_item_name', 'name', 'price', 'is_default', 'is_available', 'order')
    list_filter = ('menu_item__category__menu_type', 'menu_item__category', 'is_default', 'is_available')
    search_fields = ('menu_item__name', 'name', 'description')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Menu Item', {'fields': ('menu_item',)}),
        ('Add-on Details', {'fields': ('name', 'description', 'price')}),
        ('Settings', {'fields': ('order', 'is_default', 'is_available')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def get_item_name(self, obj):
        return obj.menu_item.name
    get_item_name.short_description = 'Menu Item'
    get_item_name.admin_order_field = 'menu_item__name'


@admin.register(MenuItemImage)
class MenuItemImageAdmin(admin.ModelAdmin):
    list_display = ('get_item_name', 'image', 'caption', 'order', 'created_at')
    list_filter = ('menu_item__category__menu_type', 'menu_item__category', 'created_at')
    search_fields = ('menu_item__name', 'alt_text', 'caption')
    readonly_fields = ('created_at',)

    fieldsets = (
        ('Menu Item', {'fields': ('menu_item',)}),
        ('Image', {'fields': ('image', 'alt_text', 'caption')}),
        ('Display Order', {'fields': ('order',)}),
        ('Timestamp', {'fields': ('created_at',), 'classes': ('collapse',)}),
    )

    def get_item_name(self, obj):
        return obj.menu_item.name
    get_item_name.short_description = 'Menu Item'
    get_item_name.admin_order_field = 'menu_item__name'


# =============================================================================
# PROMOTIONAL MENU SYSTEM — HELPERS
# =============================================================================

def _color_swatch(hex_value, label):
    """Renders a small labeled color swatch. Returns em-dash if no value."""
    if not hex_value:
        return "—"
    return format_html(
        '<span style="display:inline-flex;align-items:center;gap:6px;">'
        '<span style="display:inline-block;width:20px;height:20px;border-radius:3px;'
        'background:{};border:1px solid rgba(0,0,0,.2);flex-shrink:0;"></span>'
        '<code style="font-size:11px;">{}</code>'
        '</span>',
        hex_value,
        hex_value,
    )


def _palette_preview(primary, accent, text, bg):
    """
    Renders a compact four-slot palette preview strip.
    Each slot is a labeled swatch. Used in list_display and readonly_fields.
    """
    slots = [
        ("Primary", primary),
        ("Accent",  accent),
        ("Text",    text),
        ("BG",      bg),
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
    return format_html(
        '<span style="display:inline-flex;align-items:flex-end;">{}</span>',
        format_html("".join(str(p) for p in parts)),
    )


# =============================================================================
# PROMO COLOR SCHEME
# =============================================================================

@admin.register(PromoColorScheme)
class PromoColorSchemeAdmin(admin.ModelAdmin):
    list_display  = ('name', 'palette_preview', 'is_default', 'promo_count', 'updated_at')
    list_editable = ('is_default',)
    readonly_fields = ('palette_detail', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'is_default'),
        }),
        ('Colors', {
            'fields': (
                'palette_detail',
                'primary_color',
                'accent_color',
                'text_color',
                'bg_color',
            ),
            'description': (
                'Enter hex values (e.g. <code>#ffb612</code>). '
                'The preview above updates after saving.'
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

    @admin.display(description='Promos using this')
    def promo_count(self, obj):
        count = obj.promotions.count()
        return count if count else "—"

    @admin.display(description='Preview')
    def palette_detail(self, obj):
        """
        Full-size palette card shown inside the change form.
        Renders a mock promo banner so you can see how the colors work together.
        """
        primary = obj.primary_color or '#cccccc'
        accent  = obj.accent_color  or '#999999'
        text    = obj.text_color    or '#333333'
        bg      = obj.bg_color      or '#f5f5f5'

        return format_html(
            '<div style="margin-bottom:12px;">'

            '<div style="'
            'background:{bg};'
            'border:2px solid {primary};'
            'border-radius:6px;'
            'padding:16px 20px;'
            'max-width:420px;'
            'font-family:sans-serif;'
            '">'

            '<div style="'
            'display:flex;align-items:center;gap:10px;margin-bottom:8px;'
            '">'
            '<span style="'
            'display:inline-block;width:12px;height:12px;'
            'border-radius:50%;background:{accent};'
            '"></span>'
            '<strong style="color:{primary};font-size:15px;">Promo Heading</strong>'
            '</div>'

            '<p style="color:{text};font-size:13px;margin:0 0 10px;">Sample promo description text.</p>'

            '<span style="'
            'display:inline-block;'
            'background:{primary};color:{bg};'
            'padding:6px 14px;border-radius:4px;'
            'font-size:12px;font-weight:bold;'
            '">Order Now</span>'

            '</div>'

            '<div style="margin-top:10px;display:flex;gap:6px;align-items:center;">'
            '{swatches}'
            '</div>'

            '</div>',

            bg=bg, primary=primary, accent=accent, text=text,
            swatches=format_html(
                '{} {} {} {}',
                _color_swatch(obj.primary_color, 'Primary'),
                _color_swatch(obj.accent_color,  'Accent'),
                _color_swatch(obj.text_color,     'Text'),
                _color_swatch(obj.bg_color,       'BG'),
            ),
        )


# =============================================================================
# PROMO SETTINGS (singleton — legacy fallback)
# =============================================================================

@admin.register(PromoSettings)
class PromoSettingsAdmin(admin.ModelAdmin):
    """
    Singleton admin — only one record ever exists.
    Legacy last-resort fallback when no PromoColorScheme is assigned or flagged default.
    """
    def has_add_permission(self, request):
        return not PromoSettings.objects.exists()

    fieldsets = (
        ('Global Promo Color Defaults', {
            'description': (
                'Last-resort fallback colors used when a promotion has no color scheme assigned '
                'and no scheme is flagged as the default. '
                'Leave blank to fall back to the theme.css defaults (transparent/inherit).'
            ),
            'fields': ('promo_primary_color', 'promo_accent_color', 'promo_text_color', 'promo_bg_color'),
        }),
    )


# =============================================================================
# MENU PROMOTIONS
# =============================================================================

class MenuPromotionItemInline(admin.StackedInline):
    model = MenuPromotionItem
    extra = 0
    can_delete = True  # keep True so removal is possible
    show_change_link = False
    autocomplete_fields = ['menu_item']
    ordering = ['order']
    fields = (
        'menu_item',
        'name',
        'description',
        'promo_price',
        'note',
        'order',
    )

    def get_fieldsets(self, request, obj=None):
        return [
            (None, {
                'fields': ('menu_item',),
                'description': (
                    'Link to an existing menu item to pre-fill name/description/price, '
                    'or leave blank to enter a standalone promo item below.'
                ),
            }),
            ('Item Details', {
                'fields': ('name', 'description', 'promo_price', 'note', 'order'),
            }),
        ]

    class Media:
        js = ('admin/js/promo_item_autofill.js',)


@admin.register(MenuPromotion)
class MenuPromotionAdmin(admin.ModelAdmin):
    list_display  = ('title', 'scheme_preview', 'show_on_homepage', 'is_active', 'start_date', 'end_date', 'is_currently_active', 'item_count')
    list_editable = ('show_on_homepage',)
    list_filter   = ('show_on_homepage', 'is_active', 'color_scheme', 'start_date')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('resolved_palette_preview', 'is_currently_active', 'created_at', 'updated_at')
    inlines = [MenuPromotionItemInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'description'),
        }),
        ('Color Scheme', {
            'fields': ('color_scheme', 'resolved_palette_preview'),
            'description': (
                'Assign a color scheme or leave blank to use the default. '
                'The preview shows the colors that will actually be applied to this promotion.'
            ),
        }),
        ('Scheduling', {
            'fields': ('show_on_homepage', 'is_active', 'is_currently_active', 'start_date', 'end_date'),
            'description': (
                'Set dates to activate/deactivate automatically. '
                'Leave blank for no date restriction. '
                'The master Is Active switch overrides dates if unchecked.'
            ),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Scheme')
    def scheme_preview(self, obj):
        scheme = obj.color_scheme
        if scheme is None:
            scheme = PromoColorScheme.objects.filter(is_default=True).first()
        if scheme is None:
            return "—"
        preview = _palette_preview(
            scheme.primary_color, scheme.accent_color,
            scheme.text_color, scheme.bg_color,
        )
        label = f"{scheme.name} (default)" if obj.color_scheme is None else scheme.name
        return format_html(
            '{}<br><span style="font-size:11px;color:#666;">{}</span>',
            preview, label,
        )

    @admin.display(boolean=True, description='Active Now?')
    def is_currently_active(self, obj):
        return obj.is_currently_active

    @admin.display(description='Resolved palette')
    def resolved_palette_preview(self, obj):
        """Shows the palette that will actually be used — scheme, default, or legacy fallback."""
        colors = obj.resolve_colors()
        if obj.color_scheme_id:
            source = obj.color_scheme.name
        else:
            default_scheme = PromoColorScheme.objects.filter(is_default=True).first()
            source = f"{default_scheme.name} (default)" if default_scheme else "legacy PromoSettings fallback"
        return format_html(
            '{}<div style="margin-top:4px;font-size:11px;color:#666;">Source: {}</div>',
            _palette_preview(
                colors['primary'], colors['accent'],
                colors['text'],    colors['bg'],
            ),
            source,
        )

    def item_count(self, obj):
        return obj.promotion_items.count()
    item_count.short_description = 'Items'
