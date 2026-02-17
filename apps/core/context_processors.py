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
    Make active theme available in all templates
    """
    theme = Theme.get_active_theme()
    return {
        'active_theme': theme,
        'theme_name': theme.name if theme else 'default',
        'theme_directory': theme.theme_directory if theme else 'default',
    }
