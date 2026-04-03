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
    """
    from apps.core.models import SiteSettings
    theme = SiteSettings.load().active_theme
    if theme and theme.theme_directory:
        return [
            f"themes/{theme.theme_directory}/pages/{page}.html",
            f"pages/{page}.html",
        ]
    return [f"pages/{page}.html"]

def get_banner(slug):
    """
    Fetch an active Banner by slug and return its context dict,
    with any active seasonal ContentBlock overlaid on the content field.
    Returns an empty dict if the banner doesn't exist, so templates
    degrade gracefully rather than raising.
    """
    from apps.core.models import Banner

    try:
        banner = Banner.objects.get(slug=slug, is_active=True)
    except Banner.DoesNotExist:
        return {}

    seasonal = get_block_body(f'banner_{slug}_seasonal')
    seasonal_body = seasonal.body if seasonal else None

    return banner.as_context(seasonal_body=seasonal_body)

def get_panel_side(slug):
    """
    Fetch an active PanelSide by slug and return its context dict.
    Returns an empty dict if the slug doesn't exist, so the template
    degrades gracefully rather than raising.
    """
    from apps.core.models import PanelSide

    try:
        panel = PanelSide.objects.select_related(
            'image', 'content_slot'
        ).get(slug=slug, is_active=True)
        return panel.as_dict()
    except PanelSide.DoesNotExist:
        return {}