from .models import SiteSettings, Theme


def site_settings(request):
    """
    Injects restaurant info from SiteSettings into every template.

    Available in templates as:
        {{ site_settings }}           — full SiteSettings object
        {{ restaurant_name }}         — shortcut
        {{ restaurant_phone }}        — shortcut
        {{ restaurant_email }}        — shortcut
        {{ restaurant_address }}      — formatted single-line address
    """
    settings = SiteSettings.load()
    address_parts = filter(None, [
        settings.address_line1,
        settings.city,
        f"{settings.state} {settings.zip_code}".strip(),
    ])
    return {
        'site_settings': settings,
        'restaurant_name': settings.restaurant_name,
        'restaurant_phone': settings.phone,
        'restaurant_email': settings.email,
        'restaurant_address': ', '.join(address_parts),
    }


def active_theme(request):
    """
    Resolves the active theme + any currently active overlay into CSS variables
    and a Google Fonts URL. Everything needed to render the <head> of base.html.

    Available in templates as:
        {{ active_theme }}            — Theme object (or None)
        {{ theme_directory }}         — e.g. 'classic', used in template paths
        {{ theme_style_vars }}        — dict of CSS var name → value
        {{ google_fonts_url }}        — single combined Google Fonts <link> URL (or None)

    Usage in base.html:

        {% if google_fonts_url %}
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="{{ google_fonts_url }}" rel="stylesheet">
        {% endif %}

        <style>
          :root {
            {% for var, val in theme_style_vars.items %}
            --{{ var }}: {{ val }};
            {% endfor %}
          }
        </style>
    """
    theme = Theme.get_active_theme()

    if theme:
        style_vars = theme.resolve_style_vars()
        google_fonts_url = theme.get_google_fonts_url()
        theme_directory = theme.theme_directory
    else:
        style_vars = {}
        google_fonts_url = None
        theme_directory = 'default'

    return {
        'active_theme': theme,
        'theme_directory': theme_directory,
        'theme_style_vars': style_vars,
        'google_fonts_url': google_fonts_url,
    }
