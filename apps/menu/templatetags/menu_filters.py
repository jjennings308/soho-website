# apps/menu/templatetags/menu_filters.py
from django import template

register = template.Library()

@register.filter
def currency(value):
    try:
        amount = float(value)
        if amount == 0:
            return ""
        # If it's a whole number, show no decimals
        if amount == int(amount):
            return f"{int(amount):,}"
        # If it ends in a zero (e.g. 13.50), strip trailing zero
        formatted = f"{amount:,.2f}".rstrip('0')
        return formatted
    except (ValueError, TypeError):
        return value

@register.filter
def with_subcategory(items):
    """Return only items that have a subcategory assigned."""
    return [item for item in items if item.subcategory_id]

@register.filter
def without_subcategory(items):
    """Return only items that have no subcategory assigned."""
    return [item for item in items if not item.subcategory_id]