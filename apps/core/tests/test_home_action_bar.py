from django.test import TestCase
from django.urls import reverse

from apps.core.models import SiteSettings


class HomeActionBarTests(TestCase):
    def bar(self):
        html = self.client.get(reverse('core:home')).content.decode()
        start = html.index('bg-[var(--color-bg-secondary)]')
        return html[start:html.index('</div>', start)]

    def test_all_three_buttons_when_links_are_set(self):
        site = SiteSettings.load()
        site.reservations_url = 'https://reserve.example/soho'
        site.doordash_url = 'https://doordash.example/soho'
        site.save()
        bar = self.bar()
        self.assertIn('Reserve a Table', bar)
        self.assertIn(f'href="{reverse("core:online_delivery")}"', bar)
        self.assertIn(f'href="{reverse("menu:full")}"', bar)
        # Reserve on the left, menu in the middle, delivery on the right.
        self.assertLess(bar.index('Reserve a Table'), bar.index('View Menu'))
        self.assertLess(bar.index('View Menu'), bar.index('Online Delivery'))

    def test_order_online_needs_a_delivery_link_and_reserve_needs_its_url(self):
        site = SiteSettings.load()
        site.reservations_url = ''
        site.doordash_url = site.grubhub_url = site.ubereats_url = ''
        site.save()
        bar = self.bar()
        self.assertNotIn('Reserve a Table', bar)
        self.assertNotIn('Online Delivery', bar)
        self.assertIn('View Menu', bar)  # the bar always shows the menu button
