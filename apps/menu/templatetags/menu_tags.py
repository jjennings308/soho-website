# apps/menu/templatetags/menu_tags.py
import json
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django import template
from django.db.models import Prefetch

register = template.Library()


# =============================================================================
# INTERNAL HELPERS
# =============================================================================


def _get_item_primary_image(item):
    """
    Returns the MenuItemImage for a MenuItem that should be used as the
    primary display image, or None if the item has no images.

    Priority: is_primary=True first, then lowest display_order.

    Uses '_prefetched_images' (to_attr from get_category_assignments) when
    available to avoid per-item DB queries in list views.
    """
    from apps.menu.models import MenuItemImage
    images = getattr(item, '_prefetched_images', None)
    if images is None:
        images = list(
            item.images
            .select_related('media_item')
            .order_by('-is_primary', 'display_order')[:1]
        )
    return images[0] if images else None

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

    # Images — primary MenuItemImage through-model
    gallery = []
    primary_img = _get_item_primary_image(item)
    if primary_img and primary_img.media_item and primary_img.media_item.file:
        mi = primary_img.media_item
        gallery.append({'url': mi.file.url, 'alt': mi.alt_text or item.name})

    primary_url = gallery[0]['url'] if gallery else None

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

        # Images — primary MenuItemImage through-model
        'primary_image':     primary_url,
        'has_image':         bool(primary_url),
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
    json_str = json.dumps(data, ensure_ascii=False)
    # Escape single quotes so they don't break data-item='...'
    json_str = json_str.replace("'", "&#39;")
    return mark_safe(json_str)


# =============================================================================
# SIMPLE TAGS
# =============================================================================

@register.simple_tag
def get_primary_media(obj):
    """
    Returns the primary MediaItem for a MenuItem, or None.

    Looks up the is_primary=True MenuItemImage first; falls back to the
    first image by display_order if none is marked primary.

    Usage:
        {% get_primary_media assignment.menu_item as primary_image %}
        {% if primary_image %}
            <img src="{{ primary_image.file.url }}" alt="{{ primary_image.alt_text }}">
        {% endif %}
    """
    img = _get_item_primary_image(obj)
    return img.media_item if img else None


@register.simple_tag
def get_active_menus(menu_type=None, homepage_only=False, limit=None):
    """
    Returns currently active Menu records with their category assignments
    and item assignments prefetched.

    Args:
        menu_type:     Filter by menu_type ('food', 'drinks', 'promo').
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
def get_category_assignments(category):
    """
    Returns active MenuItemCategoryAssignment records for a category,
    with menu_item, subcategory, and media prefetched.

    Item visibility is now controlled entirely by which menu is active
    (role-based switching via get_active_menus()). No per-item filtering
    is applied here.

    Usage:
        {% get_category_assignments category as assignments %}
    """
    from apps.menu.models import MenuItemCategoryAssignment

    from apps.menu.models import MenuItemVariation, MenuItemAddon, MenuItemImage

    return MenuItemCategoryAssignment.objects.filter(
        category=category,
        is_active=True,
        menu_item__is_available=True,
    ).select_related(
        'menu_item',
        'subcategory',
    ).prefetch_related(
        Prefetch(
            'menu_item__images',
            queryset=MenuItemImage.objects.select_related(
                'media_item'
            ).order_by('-is_primary', 'display_order'),
            to_attr='_prefetched_images',
        ),
        Prefetch(
            'menu_item__variations',
            queryset=MenuItemVariation.objects.filter(
                is_available=True
            ).order_by('order', 'price'),
        ),
        Prefetch(
            'menu_item__addons',
            queryset=MenuItemAddon.objects.filter(
                is_available=True
            ).order_by('order', 'price'),
        ),
    ).order_by('subcategory__order', 'order')


@register.simple_tag
def get_menu_by_role(role):
    """
    Returns the active Menu holding the given role, or None.

    Args:
        role: 'default_food', 'default_drinks', 'event_food', or 'event_drinks'.

    Usage:
        {% get_menu_by_role 'default_food' as food_menu %}
        {% get_menu_by_role 'event_food' as event_food_menu %}
    """
    from apps.menu.models import Menu
    return Menu.objects.filter(role=role, is_active=True).first()
