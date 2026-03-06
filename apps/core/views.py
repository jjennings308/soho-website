# core/views.py
from django.shortcuts import render
#from django.template.loader import select_template
from django.views.generic import TemplateView
from .mixins import ThemedTemplateMixin
from .models import SiteSettings
from .utils import get_active_template


class HomeView(ThemedTemplateMixin, TemplateView):
    """
    CBV — ThemedTemplateMixin.get_template_names() returns a list of strings.
    Django's TemplateView handles resolution automatically.
    """
    page_type = 'home'
    fallback_template = 'pages/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        settings = SiteSettings.load()
        context['hero_banner'] = {
            'title': 'Welcome to Soho',
            'content': 'Craft cocktails and seasonal plates.',
            'bg_color': 'bg-primary',
            'text_color': 'text-primary',
        }
        context['grubhub_banner'] = {
            'title': 'Order Grub Hub',
            'content': '',
            'button': {
                'label': 'Order Grubhub Directly from SoHo',
                'href': 'http://menus.fyi/11489616',
                'bg_color': 'bg-secondary',
                'text_color': 'gold-bright',
            }
        }
        context['left_about'] = {
            'full_img': {
                'img_src': '/static/img/front_door.webp',
                'alt': 'Entrance',
                'bg_color': 'bg-secondary',
            }
        }
        context['right_about'] = {
            'title': '',
            'content': settings.short_about_text,
            'bg_color': 'bg-secondary',
            'text_color': 'text-secondary',
            'button': {
                'label': 'More About US',
                'href': '/about',
                'bg_color': 'steeler-gold',
                'text_color': 'steeler-black',
            }
        }
        context['left_cater'] = {
            'title': '',
            'content': settings.catering_text,
            'bg_color': 'bg-primary',
            'text_color': 'text-primary',
            'button': {
                'label': 'Call Now!',
                'href': 'tel:(412) 321-7646',
                'bg_color': 'bg-secondary',
                'text_color': 'text-secondary',
            }
        }
        context['right_cater'] = {
            'full_img': {
                'img_src': '/static/img/front_door.webp',
                'alt': 'Entrance',
                'bg_color': 'bg-secondary',
            }
        }
        context['left_gday'] = {
            'full_img': {
                'img_src': '/static/img/steelers_game.png',
                'alt': "Bar for Steelers' Game",
                'bg_color': 'bg-secondary',
            }
        }
        context['right_gday'] = {
            'title': '',
            'content': 'WHAT TO EXPECT ON EVENT AND GAME DAYS <p>Join us on event and game days for quick service and a limited selection of your favorite menu items. Reservations are not accepted on event or game days—show up early to avoid the waitlist. Our kitchen and bar serve expanded hours to best serve the crowds before, during and after the memorable events in Pittsburgh.',
            'bg_color': 'steeler-black',
            'text_color': 'text-secondary',
       }
        return context


def about(request):
    # FBV — render() needs a single Template object, so we use select_template()
    # to pick the first existing path from the list get_active_template() returns.
    return render(request, get_active_template('about'))


def contact(request):
    return render(request, get_active_template('contact'))


def theme_test(request):
    return render(request, 'core/theme_test.html')
