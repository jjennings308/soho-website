# core/mixins.py
from django.core.exceptions import ImproperlyConfigured
from .models import SiteSettings
from .utils import get_themed_template

class ThemedTemplateMixin:
    page_type = None
    fallback_template = None

    def get_site_settings(self):
        if not hasattr(self, '_site_settings'):
            self._site_settings = SiteSettings.objects.select_related(
                'active_theme',
                f'{self.page_type}_template'
            ).first()
        return self._site_settings

    def get_template_names(self):
        if not self.page_type or not self.fallback_template:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} requires `page_type` and `fallback_template`."
            )
        site_settings = self.get_site_settings()
        if site_settings:
            return [get_themed_template(site_settings, self.page_type, self.fallback_template)]
        return [self.fallback_template]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['site_settings'] = self.get_site_settings()
        return context