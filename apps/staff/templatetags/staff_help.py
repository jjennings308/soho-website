from django import template
from django.urls import reverse

from apps.staff.help import PAGE_TIPS

register = template.Library()


@register.simple_tag(takes_context=True)
def staff_page_tip(context):
    """The current portal page's tip, as {'text', 'url'}, or None."""
    match = getattr(context.get('request'), 'resolver_match', None)
    if not match or match.namespace != 'staff' or match.url_name not in PAGE_TIPS:
        return None
    topic, text = PAGE_TIPS[match.url_name]
    return {'text': text, 'url': f"{reverse('staff:help')}#{topic}"}
