import smtplib
from unittest import mock

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

    def test_invalid_email_rejected_without_creating_member(self):
        response = self.client.post(self.url, {'first_name': 'Pat', 'email': 'not an email'})
        self.assertIn('valid email', response.context['error'])
        self.assertFalse(SoHoMember.objects.exists())

    def test_retry_for_unconfirmed_address_updates_first_name(self):
        SoHoMember.objects.create(email='pat@example.com', first_name='Patt')
        self.client.post(self.url, {'first_name': 'Pat', 'email': 'pat@example.com'})
        self.assertEqual(SoHoMember.objects.get().first_name, 'Pat')
        self.assertEqual(len(mail.outbox), 1)

    def test_confirmed_member_told_already_subscribed_without_email(self):
        SoHoMember.objects.create(email='pat@example.com', first_name='Pat', is_active=True)
        response = self.client.post(self.url, {'first_name': 'Someone', 'email': 'pat@example.com'})
        self.assertTrue(response.context['already_subscribed'])
        self.assertEqual(SoHoMember.objects.get().first_name, 'Pat')
        self.assertEqual(len(mail.outbox), 0)

    def test_smtp_failure_shows_friendly_error_not_500(self):
        with mock.patch('apps.members.views.send_mail', side_effect=smtplib.SMTPServerDisconnected()), \
                self.assertLogs('apps.members.views', level='ERROR'):
            response = self.client.post(self.url, {'first_name': 'Pat', 'email': 'pat@example.com'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('try again', response.context['error'])

    def test_after_smtp_failure_retry_sends_immediately(self):
        with mock.patch('apps.members.views.send_mail', side_effect=ConnectionRefusedError()), \
                self.assertLogs('apps.members.views', level='ERROR'):
            self.client.post(self.url, {'first_name': 'Pat', 'email': 'pat@example.com'})
        self.client.post(self.url, {'first_name': 'Pat', 'email': 'pat@example.com'})
        self.assertEqual(len(mail.outbox), 1)


class SubscribeThrottleTests(TestCase):
    url = reverse('members:subscribe')

    def test_repeat_signup_for_same_address_sends_one_email(self):
        for _ in range(3):
            response = self.client.post(self.url, {'first_name': 'Pat', 'email': 'pat@example.com'})
            self.assertTrue(response.context['success'])
        self.assertEqual(len(mail.outbox), 1)

    def test_ip_limited_to_three_confirmation_emails_per_hour(self):
        for i in range(3):
            self.client.post(self.url, {'first_name': 'Pat', 'email': f'pat{i}@example.com'})
        response = self.client.post(self.url, {'first_name': 'Pat', 'email': 'pat9@example.com'})
        self.assertIn('try again later', response.context['error'])
        self.assertEqual(len(mail.outbox), 3)


class UnsubscribeTests(TestCase):
    def setUp(self):
        self.member = SoHoMember.objects.create(
            email='pat@example.com', first_name='Pat', is_active=True, is_email_subscribed=True,
        )
        self.url = reverse('members:unsubscribe', kwargs={'token': self.member.unsubscribe_token})

    def test_get_only_shows_confirmation(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'Unsubscribe from SoHo emails?')
        self.member.refresh_from_db()
        self.assertTrue(self.member.is_email_subscribed)

    def test_post_unsubscribes_and_retires_confirmation_link(self):
        old_confirm_token = self.member.confirmation_token
        self.client.post(self.url)
        self.member.refresh_from_db()
        self.assertFalse(self.member.is_email_subscribed)
        self.assertNotEqual(self.member.confirmation_token, old_confirm_token)
        response = self.client.get(reverse('members:confirm', kwargs={'token': old_confirm_token}))
        self.assertEqual(response.status_code, 404)

    def test_one_click_post_works_without_csrf_token(self):
        client = self.client_class(enforce_csrf_checks=True)
        response = client.post(self.url, {'List-Unsubscribe': 'One-Click'})
        self.assertEqual(response.status_code, 200)
        self.member.refresh_from_db()
        self.assertFalse(self.member.is_email_subscribed)


class ResubscribeTests(TestCase):
    url = reverse('members:subscribe')

    def test_unsubscribed_member_can_resubscribe_via_confirmation(self):
        member = SoHoMember.objects.create(
            email='pat@example.com', first_name='Pat', is_active=True, is_email_subscribed=False,
        )
        response = self.client.post(self.url, {'first_name': 'Pat', 'email': 'pat@example.com'})
        self.assertTrue(response.context['success'])
        member.refresh_from_db()
        self.assertFalse(member.is_email_subscribed)  # not until they confirm
        self.assertEqual(len(mail.outbox), 1)

        self.client.get(reverse('members:confirm', kwargs={'token': member.confirmation_token}))
        member.refresh_from_db()
        self.assertTrue(member.is_email_subscribed)
