from unittest import mock

from django.core import mail
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.core.models import EventInquiry
from apps.core.utils import client_ip, is_throttled
from apps.core.views import FORM_SUBMISSIONS_PER_HOUR

from .test_public_forms import VALID_CONTACT, VALID_INQUIRY, PublicFormTestCase


class ThrottleHelperTests(TestCase):
    def test_allows_up_to_limit_then_blocks(self):
        results = [is_throttled('t', 3, 60) for _ in range(4)]
        self.assertEqual(results, [False, False, False, True])

    def test_keys_are_independent(self):
        is_throttled('a', 1, 60)
        self.assertFalse(is_throttled('b', 1, 60))

    def test_window_resets_after_expiry(self):
        with mock.patch('apps.core.utils._clock', return_value=1000.0):
            is_throttled('t', 1, 60)
            self.assertTrue(is_throttled('t', 1, 60))
        with mock.patch('apps.core.utils._clock', return_value=1061.0):
            self.assertFalse(is_throttled('t', 1, 60))

    def test_later_hits_do_not_extend_window(self):
        with mock.patch('apps.core.utils._clock', return_value=1000.0):
            is_throttled('t', 1, 60)
        with mock.patch('apps.core.utils._clock', return_value=1050.0):
            self.assertTrue(is_throttled('t', 1, 60))
        with mock.patch('apps.core.utils._clock', return_value=1061.0):
            self.assertFalse(is_throttled('t', 1, 60))


class ClientIpTests(TestCase):
    def test_uses_rightmost_forwarded_for_entry(self):
        request = RequestFactory().get('/', HTTP_X_FORWARDED_FOR='6.6.6.6, 203.0.113.9',
                                       REMOTE_ADDR='127.0.0.1')
        self.assertEqual(client_ip(request), '203.0.113.9')

    def test_falls_back_to_remote_addr(self):
        request = RequestFactory().get('/', REMOTE_ADDR='198.51.100.4')
        self.assertEqual(client_ip(request), '198.51.100.4')


class FormThrottleTests(PublicFormTestCase):
    def test_inquiry_blocked_after_hourly_limit(self):
        url = reverse('core:event_inquiry')
        for _ in range(FORM_SUBMISSIONS_PER_HOUR):
            self.client.post(url, VALID_INQUIRY)
        mail.outbox.clear()
        response = self.client.post(url, VALID_INQUIRY)
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context['errors'])
        self.assertEqual(EventInquiry.objects.count(), FORM_SUBMISSIONS_PER_HOUR)
        self.assertEqual(len(mail.outbox), 0)

    def test_inquiry_limit_is_per_ip(self):
        url = reverse('core:event_inquiry')
        for _ in range(FORM_SUBMISSIONS_PER_HOUR):
            self.client.post(url, VALID_INQUIRY, HTTP_X_FORWARDED_FOR='203.0.113.1')
        response = self.client.post(url, VALID_INQUIRY, HTTP_X_FORWARDED_FOR='203.0.113.2')
        self.assertTrue(response.context['success'])

    def test_invalid_submissions_do_not_count(self):
        url = reverse('core:event_inquiry')
        for _ in range(FORM_SUBMISSIONS_PER_HOUR + 2):
            self.client.post(url, {**VALID_INQUIRY, 'email': 'typo'})
        response = self.client.post(url, VALID_INQUIRY)
        self.assertTrue(response.context['success'])

    def test_contact_blocked_after_hourly_limit(self):
        url = reverse('core:contact_form')
        for _ in range(FORM_SUBMISSIONS_PER_HOUR):
            self.client.post(url, VALID_CONTACT)
        mail.outbox.clear()
        response = self.client.post(url, VALID_CONTACT)
        self.assertContains(response, "try again later")
        self.assertEqual(len(mail.outbox), 0)
