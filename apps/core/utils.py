# core/utils.py

from apps.content.models import ContentBlock, ContentSlot

def get_block_body(slug):
    try:
        return ContentSlot.objects.get(slug=slug).get_active_block()
    except ContentSlot.DoesNotExist:
        return None

def get_active_template(page):
    """
    Returns a list of template path strings in priority order.

    Django will try each path and use the first one that exists:
        1. themes/{theme_directory}/pages/{page}.html  (theme-specific)
        2. pages/{page}.html                           (default fallback)

    CBVs:  return this list directly from get_template_names()
    FBVs:  pass to select_template() to get a single resolved Template object
    """
    from apps.core.models import Theme
    theme = Theme.get_active_theme()
    if theme and theme.theme_directory:
        return [
            f"themes/{theme.theme_directory}/pages/{page}.html",
            f"pages/{page}.html",
        ]
    return [f"pages/{page}.html"]
