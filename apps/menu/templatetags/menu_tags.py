import json
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


def _currency(value):
    """Mirrors the currency filter logic for use in item_to_json."""
    try:
        amount = float(value)
        if amount == 0:
            return ""
        if amount == int(amount):
            return f"{int(amount):,}"
        formatted = f"{amount:,.2f}".rstrip('0')
        return formatted
    except (ValueError, TypeError):
        return str(value)


@register.simple_tag
def get_primary_media(obj):
    """
    Returns the first approved image attached via the media manager.

    Usage:
        {% get_primary_media item as primary_image %}
        {% if primary_image %}
            <img src="{{ primary_image.file.url }}" alt="{{ primary_image.alt_text|default:item.name }}">
        {% endif %}
    """
    return obj.media.filter(
        media_type='image',
        is_approved=True
    ).order_by('display_order').first()


@register.filter(is_safe=True)
def item_to_json(item):
    """
    Serialize a MenuItem instance to a JSON string safe for
    inline use in an Alpine x-on:click attribute.

    Usage in template:
        x-on:click="$dispatch('open-menu-modal', {{ item|item_to_json }})"
    """
    # Gallery images via media manager
    gallery = [
        {
            'url': m.file.url,
            'alt': m.alt_text or '',
        }
        for m in item.media.filter(media_type='image', is_approved=True).order_by('display_order')
    ]

    # Primary image — first featured, or first approved image
    primary = item.media.filter(
        media_type='image', is_approved=True
    ).order_by('-is_featured', 'display_order').first()

    # Variations
    variations = [
        {
            'name': v.name,
            'price': _currency(v.price),
            'size': v.size or '',
            'quantity': v.quantity,
            'is_default': v.is_default,
        }
        for v in item.variations.all()
    ]

    # Add-ons
    addons = [
        {
            'name': a.name,
            'price': _currency(a.price),
            'is_default': a.is_default,
        }
        for a in item.addons.all()
    ]

    dietary_labels = item.dietary_labels
    display_price = item.display_price

    data = {
        # Identity
        'id':                item.pk,
        'name':              item.name,

        # Description
        'description':       item.description or '',
        'short_description': item.short_description or '',

        # Images
        'primary_image':     primary.file.url if primary else None,
        'has_image':         primary is not None,
        'gallery':           gallery,

        # Pricing
        'price_display':     item.price_display,
        'display_price':     display_price,
        'is_on_sale':        item.is_on_sale,

        # Variations & add-ons
        'has_variations':    item.has_variations,
        'variations':        variations,
        'has_addons':        item.has_addons,
        'addons':            addons,

        # Dietary & allergens
        'dietary_labels':    dietary_labels,
        'allergen_info':     item.allergen_info or '',

        # Feature flags
        'is_featured':       item.is_featured,
        'is_chef_special':   item.is_chef_special,
        'is_new':            item.is_new,
        'is_seasonal':       item.is_seasonal,
    }

    return mark_safe(json.dumps(data, ensure_ascii=False))


@register.simple_tag
def get_active_promotions(limit=None, homepage_only=False):
    """
    Returns all currently active promotions with items prefetched.

    Usage:
        {% get_active_promotions as promotions %}
        {% get_active_promotions limit=3 as promotions %}
    """
    from apps.menu.models import MenuPromotion, MenuPromotionItem
    from django.db.models import Prefetch

    qs = MenuPromotion.objects.filter(is_active=True)

    if homepage_only:
        qs = qs.filter(show_on_homepage=True)

    qs = qs.prefetch_related(
        Prefetch(
            'promotion_items',
            queryset=MenuPromotionItem.objects.select_related('menu_item').order_by('order'),
        )
    )

    active = [p for p in qs if p.is_currently_active]

    if limit:
        active = active[:limit]

    return active


@register.filter(is_safe=True)
def promo_item_to_json(entry):
    """
    Serialize a MenuPromotionItem for the lightweight promo modal.
    Only used for standalone items (no source MenuItem).
    """
    data = {
        'name':        entry.resolved_name(),
        'description': entry.resolved_description() or '',
        'promo_price': str(entry.promo_price) if entry.promo_price else None,
        'note':        entry.note or '',
    }
    return mark_safe(json.dumps(data, ensure_ascii=False))
