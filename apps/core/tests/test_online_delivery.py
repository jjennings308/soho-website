from django.test import TestCase
from django.urls import reverse

from apps.core.models import SiteSettings


class OnlineDeliveryPageTests(TestCase):
    url = reverse('core:online_delivery')

    def test_only_configured_services_shown(self):
        site = SiteSettings.load()
        site.doordash_url = 'https://doordash.example/soho'
        site.save()
        response = self.client.get(self.url)
        self.assertContains(response, 'Enjoy Your Favorite Items at Home')
        self.assertContains(response, 'href="https://doordash.example/soho"')
        self.assertNotContains(response, 'delivery-card--grubhub"')
        self.assertNotContains(response, 'delivery-card--ubereats"')
