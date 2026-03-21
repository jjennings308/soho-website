import json
from django import template
from django.utils.safestring import mark_safe
# from django.utils.html import escapejs

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

@register.filter(is_safe=True)
def item_to_json(item):
    """
    Serialize a MenuItem instance to a JSON string safe for
    inline use in an Alpine x-on:click attribute.

    Usage in template:
        x-on:click="$dispatch('open-menu-modal', {{ item|item_to_json }})"
    """
    # Gallery images
    gallery = [
        {
            'url': img.image.url,
            'alt': img.alt_text or '',
        }
        for img in item.gallery_images.all()
    ]

    # Variations (available only)
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

    # Add-ons (available only)
    addons = [
        {
            'name': a.name,
            'price': _currency(a.price),
            'is_default': a.is_default,
        }
        for a in item.addons.all()
    ]

    # Dietary labels via the model property
    dietary_labels = item.dietary_labels  # list of strings from the model property

    display_price = item.display_price

    data = {
        # Identity
        'id':              item.pk,
        'name':            item.name,

        # Description — CKEditor HTML, rendered safely
        'description':     item.description or '',
        'short_description': item.short_description or '',

        # Images
        'primary_image':   item.image.url if item.image else None,
        'has_image':       bool(item.image),
        'gallery':         gallery,

        # Pricing
        'price_display':   item.price_display,
        'display_price':   display_price,
        'is_on_sale':      item.is_on_sale,

        # Variations & add-ons
        'has_variations':  item.has_variations,
        'variations':      variations,
        'has_addons':      item.has_addons,
        'addons':          addons,

        # Dietary & allergens
        'dietary_labels':  dietary_labels,
        'allergen_info':   item.allergen_info or '',

        # Feature flags
        'is_featured':     item.is_featured,
        'is_chef_special': item.is_chef_special,
        'is_new':          item.is_new,
        'is_seasonal':     item.is_seasonal,
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