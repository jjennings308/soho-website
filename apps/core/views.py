# core/views.py
from django.shortcuts import render
from django.views.generic import TemplateView
from .mixins import ThemedTemplateMixin
from .models import SiteSettings
from .utils import get_active_template, get_block_body
from media_manager.models import Media


def get_site_image(theme, title):
    """
    Fetch a single Site Image attached to the active theme by title.
    Returns a Media instance or None.
    """
    if not theme:
        return None
    return theme.media.filter(
        media_type='image',
        is_approved=True,
        category__name='Site Images',
        title=title,
    ).first()


class HomeView(ThemedTemplateMixin, TemplateView):
    page_type = 'home'
    fallback_template = 'pages/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        settings = SiteSettings.load()
        active_theme = settings.active_theme

        # ── Hero images ───────────────────────────────────────────────────────
        hero_images = []
        if active_theme:
            hero_images = list(
                active_theme.media.filter(
                    media_type='image',
                    is_approved=True,
                ).order_by('-is_featured', 'display_order')
            )
        context['hero_images'] = hero_images
        context['hero_image'] = hero_images[0] if hero_images else None

        # ── Site images from media manager ────────────────────────────────────
        front_door   = get_site_image(active_theme, 'front-door')
        cater_img    = get_site_image(active_theme, 'catering')
        gameday_img  = get_site_image(active_theme, 'gameday')
        promo_img    = get_site_image(active_theme, 'promo-sidebar')

        # ── Banners ───────────────────────────────────────────────────────────
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

        # ── About 50/50 ───────────────────────────────────────────────────────
        if front_door:
            context['left_about'] = {
                'full_img': {
                    'img_src': front_door.file.url,
                    'alt': front_door.alt_text or 'Entrance',
                    'bg_color': 'bg-secondary',
                }
            }
        else:
            context['left_about'] = {
                'full_img': {
                    'img_src': '/static/img/front_door.webp',
                    'alt': 'Entrance',
                    'bg_color': 'bg-secondary',
                }
            }

        block = get_block_body('about_short')
        context['right_about'] = {
            'title': '',
            'content': block.body if block else '',
            'bg_color': 'bg-secondary',
            'text_color': 'text-secondary',
            'button': {
                'label': 'More About US',
                'href': '/about',
                'bg_color': 'steeler-gold',
                'text_color': 'steeler-black',
            }
        }

        # ── Catering 50/50 ────────────────────────────────────────────────────
        block = get_block_body('catering_body')
        context['left_cater'] = {
            'title': '',
            'content': block.body if block else '',
            'bg_color': 'bg-primary',
            'text_color': 'text-primary',
            'button': {
                'label': 'Call Now!',
                'href': 'tel:(412) 321-7646',
                'bg_color': 'bg-secondary',
                'text_color': 'text-secondary',
            }
        }

        if cater_img:
            context['right_cater'] = {
                'full_img': {
                    'img_src': cater_img.file.url,
                    'alt': cater_img.alt_text or 'Catering',
                    'bg_color': 'bg-secondary',
                }
            }
        else:
            context['right_cater'] = {
                'full_img': {
                    'img_src': '/static/img/front_door.webp',
                    'alt': 'Catering',
                    'bg_color': 'bg-secondary',
                }
            }

        # ── Game Day 50/50 ────────────────────────────────────────────────────
        if gameday_img:
            context['left_gday'] = {
                'full_img': {
                    'img_src': gameday_img.file.url,
                    'alt': gameday_img.alt_text or "Bar for Steelers' Game",
                    'bg_color': 'bg-secondary',
                }
            }
        else:
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

        # ── Promo sidebar ─────────────────────────────────────────────────────
        context['promo_sidebar_image'] = promo_img

        return context


def about(request):
    return render(request, get_active_template('about'))


def contact(request):
    return render(request, get_active_template('contact'))


def theme_test(request):
    return render(request, 'core/theme_test.html')