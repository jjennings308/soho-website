from django import template
from apps.content.models import ContentSlot

register = template.Library()


@register.simple_tag
def get_active_block(slug):
    """
    Returns the active ContentBlock for a given slot slug, or None.

    Usage (assign to variable):
        {% get_active_block 'about_header' as block %}
        {% if block %}
            <h1>{{ block.body|safe }}</h1>
            {% if block.image %}<img src="{{ block.image.url }}" alt="">{% endif %}
        {% endif %}

    Usage (render immediately, body only):
        {% get_active_block 'about_header' as block %}{{ block.body|safe }}
    """
    try:
        slot = ContentSlot.objects.get(slug=slug)
        return slot.get_active_block()
    except ContentSlot.DoesNotExist:
        return None


@register.inclusion_tag('content/block.html')
def render_content_block(slug, css_class=''):
    """
    Renders a content block using the content/block.html partial.
    Handles the None case gracefully — renders nothing if no active block.

    Usage:
        {% render_content_block 'about_header' %}
        {% render_content_block 'catering_body' css_class='prose text-gold' %}
    """
    try:
        slot = ContentSlot.objects.get(slug=slug)
        block = slot.get_active_block()
    except ContentSlot.DoesNotExist:
        block = None

    return {'block': block, 'css_class': css_class}
