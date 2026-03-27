from django import template
from media_manager.models import Media

register = template.Library()


@register.simple_tag
def get_hero_images(theme, limit=None):
    """
    Returns approved images attached to the given Theme via the media manager,
    ordered by display_order. Use is_featured=True on a Media record to mark
    the primary hero.

    Usage:
        {% get_hero_images active_theme as hero_images %}
        {% get_hero_images active_theme limit=1 as primary_hero %}
    """
    if not theme:
        return []

    qs = theme.media.filter(
        media_type='image',
        is_approved=True,
    ).order_by('-is_featured', 'display_order')

    if limit:
        qs = qs[:limit]

    return list(qs)