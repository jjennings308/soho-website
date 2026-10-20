from django.core import mail
from django.test import TestCase
from django.urls import reverse

from apps.core.models import EventInquiry, SiteSettings


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
}

VALID_CONTACT = {
    'name': 'Pat Doe',
    'email': 'pat@example.com',
    'phone': '',
    'message': 'Do you have gluten-free options?',
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
