from django.shortcuts import render
from django.http import HttpResponse
from .models import SiteSettings


def _get_template(settings, page_type, fallback):
    """
    Resolve the template path for a given page type from SiteSettings.
    Falls back to the hardcoded path if no PageTemplate is assigned or
    if the assigned template's file path is blank.

    Args:
        settings:   SiteSettings singleton (already loaded)
        page_type:  one of 'home', 'menu', 'promotions'
        fallback:   hardcoded template path string, used as a safety net

    Returns:
        A template path string ready to pass to render().
    """
    template_fk = getattr(settings, f'{page_type}_template', None)
    if template_fk and template_fk.template_file:
        theme = settings.active_theme
        if theme and theme.theme_directory:
            return f"{theme.theme_directory}/{template_fk.template_file}"
        return template_fk.template_file
    return fallback


def home(request):
    settings = SiteSettings.load()
    template = _get_template(settings, 'home', 'core/home.html')

    context = {
        'hero_banner': {
            'title': 'Welcome to Soho',
            'content': 'Craft cocktails and seasonal plates.',
            'style': 'background-color: var(--color-bg-primary); color: var(--color-text-primary);',
        }
    }
    return render(request, template, context)


def about(request):
    settings = SiteSettings.load()
    # About doesn't have a PageTemplate FK yet, so we fall back directly.
    # Add an about_template field to SiteSettings later if needed.
    return render(request, 'core/about.html')


def contact(request):
    settings = SiteSettings.load()
    # Same as above for contact.
    return render(request, 'core/contact.html')

def theme_test(request):
    return render(request, 'core/theme_test.html')