from .models import SiteSettings, Theme


def site_settings(request):
    """
    Make site settings available in all templates
    """
    settings = SiteSettings.load()
    return {
        'site_settings': settings,
        'restaurant_name': settings.restaurant_name,
        'restaurant_phone': settings.phone,
        'restaurant_email': settings.email,
        'restaurant_address': f"{settings.address_line1}, {settings.city}, {settings.state} {settings.zip_code}".strip(', '),
    }


def active_theme(request):
    """
    Make active theme and resolved style variables available in all templates.
    Resolves base style + any active overlay into a single set of CSS variables.
    """
    theme = Theme.get_active_theme()
    style_vars = theme.resolve_style_vars() if theme else {}

    return {
        'active_theme': theme,
        'theme_name': theme.name if theme else 'default',
        'theme_directory': theme.theme_directory if theme else 'default',
        'theme_style_vars': style_vars,  # dict of CSS var name -> value
    }
