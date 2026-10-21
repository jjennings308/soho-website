from django import template

from apps.core.spam import FORM_TOKEN_FIELD, form_started_at, form_started_token

register = template.Library()


@register.simple_tag(takes_context=True)
def form_started_input_value(context):
    """
    Value for the hidden page-load timestamp. When a form is re-rendered
    after a validation error, keep the original token so the visitor isn't
    judged on how fast they fixed one field.
    """
    data = context.get('data')
    existing = data.get(FORM_TOKEN_FIELD) if hasattr(data, 'get') else None
    if existing and form_started_at(existing) is not None:
        return existing
    return form_started_token()
