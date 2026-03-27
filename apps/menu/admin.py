from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.utils.html import format_html, mark_safe
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
            'fields': ('is_featured', 'is_chef_special', 'is_new', 'is_seasonal')
        }),
        ('Availability', {
            'fields': ('is_available', 'available_from', 'available_until', 'order'),
        }),
    )


# ---------------------------------------------------------------------------
# Promotional Menu — Helpers
# ---------------------------------------------------------------------------

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
    # parts contains format_html output (already SafeString) — join and wrap with mark_safe
    return mark_safe(
        '<span style="display:inline-flex;align-items:flex-end;">'
        + "".join(str(p) for p in parts)
        + '</span>'
    )


# ---------------------------------------------------------------------------
# Promo Color Scheme
# ---------------------------------------------------------------------------

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
            'background:{bg};border:2px solid {primary};border-radius:6px;'
            'padding:16px 20px;max-width:420px;font-family:sans-serif;">'

            '<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">'
            '<span style="display:inline-block;width:12px;height:12px;'
            'border-radius:50%;background:{accent};"></span>'
            '<strong style="color:{primary};font-size:15px;">Promo Heading</strong>'
            '</div>'

            '<p style="color:{text};font-size:13px;margin:0 0 10px;">Sample promo description text.</p>'

            '<span style="display:inline-block;background:{primary};color:{bg};'
            'padding:6px 14px;border-radius:4px;font-size:12px;font-weight:bold;">'
            'Order Now</span>'

            '</div>'

            '<div style="margin-top:10px;display:flex;gap:6px;align-items:center;">'
            '{swatches}'
            '</div>'

            '</div>',

            bg=bg, primary=primary, accent=accent, text=text,
            swatches=mark_safe(
                "".join([
                    str(_color_swatch(obj.primary_color, 'Primary')),
                    str(_color_swatch(obj.accent_color,  'Accent')),
                    str(_color_swatch(obj.text_color,    'Text')),
                    str(_color_swatch(obj.bg_color,      'BG')),
                ])
            ),
        )


# ---------------------------------------------------------------------------
# Promo Settings (singleton — legacy fallback)
# ---------------------------------------------------------------------------

@admin.register(PromoSettings)
class PromoSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not PromoSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    fieldsets = (
        ('Global Promo Color Fallback', {
            'description': (
                'Last-resort fallback colors used when a promotion has no color scheme assigned '
                'and no scheme is flagged as the default. '
                'Leave blank to fall back to theme.css defaults (transparent/inherit).'
            ),
            'fields': ('promo_primary_color', 'promo_accent_color', 'promo_text_color', 'promo_bg_color'),
        }),
    )


# ---------------------------------------------------------------------------
# Menu Promotions
# ---------------------------------------------------------------------------

class MenuPromotionItemInline(admin.TabularInline):
    model = MenuPromotionItem
    extra = 0
    fields = ['menu_item', 'name', 'promo_price', 'note', 'order']
    autocomplete_fields = ['menu_item']


@admin.register(MenuPromotion)
class MenuPromotionAdmin(admin.ModelAdmin):
    list_display  = ('title', 'scheme_preview', 'is_active', 'show_on_homepage', 'start_date', 'end_date')
    list_editable = ('is_active', 'show_on_homepage')
    list_filter   = ('is_active', 'show_on_homepage', 'color_scheme')
    search_fields = ('title',)
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('resolved_palette_preview',)
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
            'fields': ('title', 'slug', 'description'),
        }),
        ('Color Scheme', {
            'fields': ('color_scheme', 'resolved_palette_preview'),
            'description': (
                'Assign a color scheme or leave blank to use the default. '
                'The preview shows the colors that will actually be applied.'
            ),
        }),
        ('Schedule', {
            'fields': ('start_date', 'end_date'),
            'classes': ('collapse',),
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
