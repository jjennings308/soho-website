from .models import SiteSettings
from django.conf import settings


def site_settings(request):
    """
    Injects restaurant info from SiteSettings into every template.

    Available in templates as:
        {{ site_settings }}           — full SiteSettings object
        {{ restaurant_name }}         — shortcut
        {{ restaurant_phone }}        — shortcut
        {{ restaurant_email }}        — shortcut
        {{ restaurant_address }}      — formatted single-line address
        {{ current_specials }}        — active weekly specials Menu, or None
    """
    from apps.menu.models import Menu
    settings_obj = SiteSettings.load()
    address_parts = filter(None, [
        settings_obj.address_line1,
        settings_obj.city,
        f"{settings_obj.state} {settings_obj.zip_code}".strip(),
    ])
    return {
        'site_settings':      settings_obj,
        'restaurant_name':    settings_obj.restaurant_name,
        'restaurant_phone':   settings_obj.phone,
        'restaurant_email':   settings_obj.email,
        'restaurant_address': ', '.join(address_parts),
        'current_specials':   Menu.get_current_specials(),
    }



def site_version(request):
    return {'VERSION': getattr(settings, 'VERSION', '')}
