import time

from django.core import mail
from django.test import TestCase
from django.urls import reverse

from apps.core.models import EventInquiry, SiteSettings
from apps.core.spam import form_started_token

# A form "loaded" a minute ago, so the minimum-fill-time spam check passes.
FORM_LOADED = form_started_token(time.time() - 60)

VALID_INQUIRY = {
    'name': 'Pat Doe',
    'email': 'pat@example.com',
    'phone': '412-555-0100',
    'preferred_contact': 'email',
    'event_type': 'birthday',
    'guest_count': '30',
    'preferred_date': '2026-12-05',
    'menu_preference': 'full',
    'message': 'Back room if possible.',
    'ft': FORM_LOADED,
}

VALID_CONTACT = {
    'name': 'Pat Doe',
    'email': 'pat@example.com',
    'phone': '',
    'message': 'Do you have gluten-free options?',
    'ft': FORM_LOADED,
}


class PublicFormTestCase(TestCase):
    def setUp(self):
        site = SiteSettings.load()
        site.notification_email = 'staff@example.com'
        site.save()


class EventInquiryFormTests(PublicFormTestCase):
    url = reverse('core:event_inquiry')

    def test_valid_inquiry_saves_and_sends_two_emails(self):
        response = self.client.post(self.url, VALID_INQUIRY)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['success'])
        inquiry = EventInquiry.objects.get()
        self.assertEqual(inquiry.guest_count, 30)
        self.assertEqual(str(inquiry.preferred_date), '2026-12-05')
        self.assertEqual(
            sorted(m.to[0] for m in mail.outbox),
            ['pat@example.com', 'staff@example.com'],
        )

    def test_non_numeric_guest_count_shows_error_instead_of_500(self):
        response = self.client.post(self.url, {**VALID_INQUIRY, 'guest_count': 'abc'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('guest_count', response.context['errors'])
        self.assertFalse(EventInquiry.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_date_shows_error_instead_of_500(self):
        response = self.client.post(self.url, {**VALID_INQUIRY, 'preferred_date': 'not-a-date'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('preferred_date', response.context['errors'])
        self.assertFalse(EventInquiry.objects.exists())

    def test_invalid_email_rejected(self):
        response = self.client.post(self.url, {**VALID_INQUIRY, 'email': 'not-an-email'})
        self.assertIn('email', response.context['errors'])
        self.assertFalse(EventInquiry.objects.exists())

    def test_unknown_event_type_rejected(self):
        response = self.client.post(self.url, {**VALID_INQUIRY, 'event_type': 'x' * 50})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(EventInquiry.objects.exists())

    def test_missing_selects_fall_back_to_model_defaults(self):
        data = {k: v for k, v in VALID_INQUIRY.items()
                if k not in ('preferred_contact', 'event_type', 'menu_preference')}
        self.client.post(self.url, data)
        inquiry = EventInquiry.objects.get()
        self.assertEqual(inquiry.preferred_contact, 'email')
        self.assertEqual(inquiry.event_type, 'private_party')
        self.assertEqual(inquiry.menu_preference, 'not_sure')

    def test_blank_optional_fields_accepted(self):
        self.client.post(self.url, {**VALID_INQUIRY, 'guest_count': '', 'preferred_date': ''})
        inquiry = EventInquiry.objects.get()
        self.assertIsNone(inquiry.guest_count)
        self.assertIsNone(inquiry.preferred_date)

    def test_newline_in_name_is_collapsed(self):
        self.client.post(self.url, {**VALID_INQUIRY, 'name': 'Pat\nBcc: victim@example.com'})
        self.assertEqual(EventInquiry.objects.get().name, 'Pat Bcc: victim@example.com')


class ContactFormTests(PublicFormTestCase):
    url = reverse('core:contact_form')

    def test_valid_message_emails_restaurant_only(self):
        response = self.client.post(self.url, VALID_CONTACT)
        self.assertTrue(response.context['success'])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['staff@example.com'])

    def test_missing_fields_show_errors(self):
        response = self.client.post(self.url, {})
        self.assertEqual(set(response.context['errors']), {'name', 'email', 'message'})
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_email_rejected(self):
        response = self.client.post(self.url, {**VALID_CONTACT, 'email': 'nope'})
        self.assertIn('email', response.context['errors'])
        self.assertEqual(len(mail.outbox), 0)


class SpamProtectionTests(PublicFormTestCase):
    def test_inquiry_confirmation_does_not_echo_message(self):
        spam = 'Buy cheap watches at spam.example'
        self.client.post(reverse('core:event_inquiry'), {**VALID_INQUIRY, 'message': spam})
        confirmation = next(m for m in mail.outbox if m.to == ['pat@example.com'])
        self.assertNotIn(spam, confirmation.body)
        self.assertNotIn(spam, confirmation.alternatives[0][0])
        # Staff still get the full message.
        notification = next(m for m in mail.outbox if m.to == ['staff@example.com'])
        self.assertIn(spam, notification.body)

    def test_inquiry_honeypot_fakes_success_without_acting(self):
        response = self.client.post(reverse('core:event_inquiry'), {**VALID_INQUIRY, 'hp_check': 'x'})
        self.assertTrue(response.context['success'])
        self.assertFalse(EventInquiry.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_contact_honeypot_fakes_success_without_acting(self):
        response = self.client.post(reverse('core:contact_form'), {**VALID_CONTACT, 'hp_check': 'x'})
        self.assertTrue(response.context['success'])
        self.assertEqual(len(mail.outbox), 0)

    def test_forms_render_honeypot_field(self):
        response = self.client.post(reverse('core:contact_form'), {})
        self.assertContains(response, 'name="hp_check"')
