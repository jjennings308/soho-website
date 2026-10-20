from django.core import mail
from django.test import TestCase
from django.urls import reverse

from apps.members.models import SoHoMember


class SubscribeTests(TestCase):
    url = reverse('members:subscribe')

    def test_new_subscriber_gets_confirmation_email(self):
        response = self.client.post(self.url, {'first_name': 'Pat', 'email': 'Pat@Example.com'})
        self.assertTrue(response.context['success'])
        member = SoHoMember.objects.get()
        self.assertEqual(member.email, 'pat@example.com')
        self.assertFalse(member.is_active)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(str(member.confirmation_token), mail.outbox[0].body)

    def test_honeypot_fakes_success_without_acting(self):
        response = self.client.post(self.url, {'first_name': 'Pat', 'email': 'pat@example.com', 'hp_check': 'x'})
        self.assertTrue(response.context['success'])
        self.assertFalse(SoHoMember.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_subscribe_form_renders_honeypot_field(self):
        response = self.client.post(self.url, {})
        self.assertContains(response, 'name="hp_check"')
