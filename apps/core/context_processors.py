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



def site_version(request):
    return {'VERSION': getattr(settings, 'VERSION', '')}
