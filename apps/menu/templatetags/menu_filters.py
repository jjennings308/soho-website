# apps/menu/templatetags/menu_filters.py
from django import template

register = template.Library()


@register.filter
def currency(value):
    """
    Formats a numeric value as a price string.
    Strips trailing zeros: 13.50 → '13.5', 14.00 → '14'.
    Returns empty string for zero or non-numeric values.
    """
    try:
        amount = float(value)
        if amount == 0:
            return ""
        if amount == int(amount):
            return f"{int(amount):,}"
        formatted = f"{amount:,.2f}".rstrip('0')
        return formatted
    except (ValueError, TypeError):
        return value


@register.filter
def with_subcategory(assignments):
    """
    Filters a list of MenuItemCategoryAssignment objects to those
    that have a subcategory assigned.

    Usage:
        {% with subcat_items=assignments|with_subcategory %}
    """
    return [a for a in assignments if a.subcategory_id]


@register.filter
def without_subcategory(assignments):
    """
    Filters a list of MenuItemCategoryAssignment objects to those
    that have no subcategory assigned.

    Usage:
        {% with plain_items=assignments|without_subcategory %}
    """
    return [a for a in assignments if not a.subcategory_id]

@register.filter
def section_color_key(counter):
    if counter % 3 == 0:
        return "tertiary"
    if counter % 2 == 0:
        return "secondary"
    return "primary"