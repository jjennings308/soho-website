# core/mixins.py
from django.core.exceptions import ImproperlyConfigured
from .models import SiteSettings
from .utils import get_active_template


class ThemedTemplateMixin:
    """
    Resolves the correct template for a class-based view using the active theme's
    directory convention. Falls back to pages/{page_type}.html if no theme is active
    or no theme-specific template exists for this page.

    Usage:
        class HomeView(ThemedTemplateMixin, TemplateView):
            page_type = 'home'
            fallback_template = 'pages/home.html'
    """
    page_type = None
    fallback_template = None

    def get_template_names(self):
        if not self.page_type or not self.fallback_template:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} requires both `page_type` and `fallback_template`."
            )
        # get_active_template returns a list of strings — return it directly.
        # Django's TemplateView.render_to_response() calls get_template_names()
        # and expects a list of strings, trying each until one is found.
        return get_active_template(self.page_type)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['site_settings'] = SiteSettings.load()
        return context
