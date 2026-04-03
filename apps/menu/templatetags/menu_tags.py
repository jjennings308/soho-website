# apps/menu/templatetags/menu_tags.py
import json
from django import template
from django.utils.safestring import mark_safe
from django.db.models import Prefetch

register = template.Library()


# =============================================================================
# INTERNAL HELPERS
# =============================================================================

def _currency(value):
    """Mirrors the currency filter for use inside Python tag logic."""
    try:
        amount = float(value)
        if amount == 0:
            return ""
        if amount == int(amount):
            return f"{int(amount):,}"
        return f"{amount:,.2f}".rstrip('0')
    except (ValueError, TypeError):
        return str(value)


def _assignment_to_json_data(assignment):
    """
    Builds the full JSON payload for a MenuItemCategoryAssignment.

    display_price resolution:
        override_price on the assignment takes precedence over the item's
        own price logic — this is how Happy Hour / promo pricing works.

    Called by both item_to_json (filter) and assignment_to_json (tag).
    """
    item = assignment.menu_item

    # Gallery images
    gallery = [
        {'url': m.file.url, 'alt': m.alt_text or ''}
        for m in item.media.filter(
            media_type='image', is_approved=True
        ).order_by('display_order')
    ]

    # Primary image
    primary = item.media.filter(
        media_type='image', is_approved=True
    ).order_by('-is_featured', 'display_order').first()

    # Variations
    variations = [
        {
            'name':       v.name,
            'price':      _currency(v.price),
            'size':       v.size or '',
            'quantity':   v.quantity,
            'is_default': v.is_default,
        }
        for v in item.variations.all()
    ]

    # Add-ons
    addons = [
        {
            'name':       a.name,
            'price':      _currency(a.price),
            'is_default': a.is_default,
        }
        for a in item.addons.all()
    ]

    # Effective display price — assignment override takes precedence
    display_price = assignment.display_price

    # Per-placement note (e.g. 'Half price during Happy Hour')
    note = assignment.note or ''

    return {
        # Identity
        'id':                item.pk,
        'name':              item.name,
        'slug':              item.slug,

        # Descriptions
        'description':       item.description or '',
        'short_description': item.short_description or '',

        # Images
        'primary_image':     primary.file.url if primary else None,
        'has_image':         primary is not None,
        'gallery':           gallery,

        # Pricing — uses assignment override if set
        'price_display':     item.price_display,
        'display_price':     display_price,
        'is_on_sale':        item.is_on_sale,

        # Placement-specific
        'note':              note,

        # Variations & add-ons
        'has_variations':    item.has_variations,
        'variations':        variations,
        'has_addons':        item.has_addons,
        'addons':            addons,

        # Dietary & allergens
        'dietary_labels':    item.dietary_labels,
        'allergen_info':     item.allergen_info or '',

        # Feature flags
        'is_featured':       item.is_featured,
        'is_chef_special':   item.is_chef_special,
        'is_new':            item.is_new,
        'is_seasonal':       item.is_seasonal,
    }


# =============================================================================
# FILTERS
# =============================================================================

@register.filter(is_safe=True)
def item_to_json(assignment):
    """
    Serializes a MenuItemCategoryAssignment to a JSON string safe for
    inline use in Alpine x-on:click / data-item attributes.

    The assignment's override_price is used for display_price when set,
    so promo/happy-hour pricing flows through automatically.

    Usage:
        data-item='{{ assignment|item_to_json }}'
    """
    data = _assignment_to_json_data(assignment)
    return mark_safe(json.dumps(data, ensure_ascii=False))


# =============================================================================
# SIMPLE TAGS
# =============================================================================

@register.simple_tag
def get_primary_media(obj):
    """
    Returns the first approved image attached to any media-manager object
    (MenuItem, MenuCategory, etc.).

    Usage:
        {% get_primary_media assignment.menu_item as primary_image %}
        {% if primary_image %}
            <img src="{{ primary_image.file.url }}" alt="{{ primary_image.alt_text }}">
        {% endif %}
    """
    return obj.media.filter(
        media_type='image',
        is_approved=True,
    ).order_by('display_order').first()


@register.simple_tag
def get_active_menus(menu_type=None, homepage_only=False, limit=None):
    """
    Returns currently active Menu records with their category assignments
    and item assignments prefetched.

    Args:
        menu_type:     Filter by menu_type ('food', 'drinks', 'combined', 'promo').
                       Omit to return all active menus.
        homepage_only: If True, only return menus with show_on_homepage=True.
        limit:         Maximum number of menus to return.

    Usage:
        {% get_active_menus menu_type='promo' homepage_only=True as promos %}
        {% get_active_menus as all_menus %}
    """
    from apps.menu.models import Menu, MenuCategoryAssignment, MenuItemCategoryAssignment

    qs = Menu.objects.filter(is_active=True)

    if menu_type:
        qs = qs.filter(menu_type=menu_type)
    if homepage_only:
        qs = qs.filter(show_on_homepage=True)

    qs = qs.prefetch_related(
        Prefetch(
            'menu_category_assignments',
            queryset=MenuCategoryAssignment.objects.select_related(
                'category'
            ).order_by('display_order'),
        ),
    )

    active = [m for m in qs if m.is_currently_active]

    if limit:
        active = active[:limit]

    return active


@register.simple_tag
def get_category_assignments(category, limited_menu=False):
    """
    Returns active MenuItemCategoryAssignment records for a category,
    with menu_item, subcategory, and media prefetched.

    Args:
        category:     MenuCategory instance.
        limited_menu: If True, only return assignments with available_game_day=True.

    Usage:
        {% get_category_assignments category as assignments %}
        {% get_category_assignments category limited_menu=True as assignments %}
    """
    from apps.menu.models import MenuItemCategoryAssignment

    qs = MenuItemCategoryAssignment.objects.filter(
        category=category,
        is_active=True,
        menu_item__is_available=True,
    ).select_related(
        'menu_item',
        'subcategory',
    ).prefetch_related(
        Prefetch(
            'menu_item__variations',
            queryset=__import__(
                'apps.menu.models', fromlist=['MenuItemVariation']
            ).MenuItemVariation.objects.filter(
                is_available=True
            ).order_by('order', 'price'),
        ),
        Prefetch(
            'menu_item__addons',
            queryset=__import__(
                'apps.menu.models', fromlist=['MenuItemAddon']
            ).MenuItemAddon.objects.filter(
                is_available=True
            ).order_by('order', 'price'),
        ),
        'menu_item__media',
    ).order_by('subcategory__order', 'order')

    if limited_menu:
        qs = qs.filter(available_game_day=True)

    return qs


@register.simple_tag
def get_default_menu(menu_type='combined'):
    """
    Returns the default Menu for the given type, with categories and
    item assignments prefetched.

    Args:
        menu_type: 'combined', 'food', or 'drinks'.

    Usage:
        {% get_default_menu 'combined' as menu %}
        {% get_default_menu 'food' as food_menu %}
    """
    from apps.menu.models import Menu
    return Menu.objects.filter(
        menu_type=menu_type,
        is_default=True,
        is_active=True,
    ).first()
