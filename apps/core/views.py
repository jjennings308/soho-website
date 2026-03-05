from django.shortcuts import render
from django.views.generic import TemplateView
from .mixins import ThemedTemplateMixin
from .models import SiteSettings


class HomeView(ThemedTemplateMixin, TemplateView):
    page_type = 'home'
    fallback_template = 'core/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hero_banner'] ={
            'title': 'Welcome to Soho',
            'content': 'Craft cocktails and seasonal plates.',
            'style': 'background-color: var(--color-bg-primary); color: var(--color-text-primary);',
        }      
        context['grubhub_banner'] ={
            'title': 'Order Grub Hub',
            'content': '',
            'style': 'background-color: var(--color-bg-primary); color: var(--color-text-primary);',
            'button': {
                'label': 'Order Grubhub Directly from SoHo',
                'href': 'http://menus.fyi/11489616',
                'bg_color': 'bg-yellow-500',
                'text_color': 'text-black',
            }
        }
        context['right'] ={
            'content': '<img src="/static/img/front_door.webp" alt="Entrance" class="w-full h-full object-cover">',
        }      
        return context

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