from django import template
from apps.content.models import ContentSlot, ContentGroup

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


@register.simple_tag
def get_content_group(slug):
    """
    Returns a ContentGroup with all its slots and blocks prefetched, or None.

    Fetches the group in 3 queries (group, slots, blocks) regardless of how
    many slots or blocks the group contains. The group's slot accessor
    properties (title_slots, body_slots, etc.) then filter in Python with
    no further DB hits.

    Usage:
        {% load content_tags %}
        {% get_content_group 'hero_banner' as group %}
        {% if group %}

            {% for slot in group.title_slots %}
                {% with block=slot.get_active_block %}
                    {% if block %}<h1>{{ block.body|safe }}</h1>{% endif %}
                {% endwith %}
            {% endfor %}

            {% for slot in group.subtitle_slots %}
                {% with block=slot.get_active_block %}
                    {% if block %}<p class="subtitle">{{ block.body|safe }}</p>{% endif %}
                {% endwith %}
            {% endfor %}

            {% for slot in group.body_slots %}
                {% with block=slot.get_active_block %}
                    {% if block %}
                        <div class="body body--{{ slot.slug }}">{{ block.body|safe }}</div>
                    {% endif %}
                {% endwith %}
            {% endfor %}

            {% for slot in group.image_slots %}
                {% with block=slot.get_active_block %}
                    {% if block and block.image %}
                        <img src="{{ block.image.url }}" alt="{{ slot.label }}">
                    {% endif %}
                {% endwith %}
            {% endfor %}

            {% for slot in group.button_slots %}
                {% with block=slot.get_active_block %}
                    {% if block and block.button_url %}
                        <a href="{{ block.button_url }}" class="btn">{{ block.button_label }}</a>
                    {% endif %}
                {% endwith %}
            {% endfor %}

            {% for slot in group.footer_slots %}
                {% with block=slot.get_active_block %}
                    {% if block %}<footer>{{ block.body|safe }}</footer>{% endif %}
                {% endwith %}
            {% endfor %}

        {% endif %}

    Note: slot.slug is available inside loops and can be used to drive
    per-slot CSS classes or data attributes without any extra queries.
    """
    try:
        return (
            ContentGroup.objects
            .prefetch_related(
                'slots',
                'slots__blocks',
            )
            .get(slug=slug)
        )
    except ContentGroup.DoesNotExist:
        return None
