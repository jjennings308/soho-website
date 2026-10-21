import time

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import mail
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.core.models import EventInquiry
from apps.core.spam import MIN_FILL_SECONDS, form_started_token, spam_reasons
from apps.core.views import SITEWIDE_CONTACT_EMAILS_PER_HOUR, SITEWIDE_INQUIRY_EMAILS_PER_HOUR
from apps.staff.permissions import MANAGER_GROUP

from .test_public_forms import VALID_CONTACT, VALID_INQUIRY, PublicFormTestCase


def reasons_for(token=..., *texts):
    data = {} if token is None else {'ft': form_started_token(time.time() - 60) if token is ... else token}
    return spam_reasons(RequestFactory().post('/', data), *texts)


class SpamReasonTests(TestCase):
    def test_normal_submission_is_clean(self):
        self.assertEqual(reasons_for(..., 'Pat Doe', 'Back room for 30, around 7pm? Email pat@gmail.com'), [])

    def test_missing_or_forged_token(self):
        self.assertEqual(reasons_for(None), ['no form token'])
        self.assertEqual(reasons_for('not-a-real-token'), ['no form token'])

    def test_too_fast(self):
        reasons = reasons_for(form_started_token(time.time() - (MIN_FILL_SECONDS - 1)))
        self.assertTrue(reasons and reasons[0].startswith('sent '))

    def test_old_token_is_fine(self):
        self.assertEqual(reasons_for(form_started_token(time.time() - 7 * 86400)), [])

    def test_links_flagged(self):
        for text in ['see https://spam.example', 'visit www.spam.example', '[url=x]y[/url]', '<a href="x">y</a>']:
            with self.subTest(text=text):
                self.assertIn('link in text', reasons_for(..., text))

    def test_mostly_non_latin_flagged_but_accents_fine(self):
        self.assertIn('mostly non-Latin text', reasons_for(..., 'Отличное предложение для вашего бизнеса сегодня'))
        self.assertEqual(reasons_for(..., 'Fête de fin d’année pour l’équipe, environ trente personnes'), [])


class InquirySpamTests(PublicFormTestCase):
    url = reverse('core:event_inquiry')

    def test_flagged_inquiry_saved_as_spam_without_emails(self):
        response = self.client.post(self.url, {**VALID_INQUIRY, 'message': 'Great deal at https://spam.example'})
        self.assertTrue(response.context['success'])
        self.assertFalse(response.context['confirmation_sent'])
        inquiry = EventInquiry.objects.get()
        self.assertEqual(inquiry.status, 'spam')
        self.assertEqual(inquiry.spam_reason, 'link in text')
        self.assertEqual(len(mail.outbox), 0)

    def test_instant_submission_saved_as_spam(self):
        self.client.post(self.url, {**VALID_INQUIRY, 'ft': form_started_token()})
        self.assertEqual(EventInquiry.objects.get().status, 'spam')
        self.assertEqual(len(mail.outbox), 0)

    def test_direct_post_without_token_saved_as_spam(self):
        data = {k: v for k, v in VALID_INQUIRY.items() if k != 'ft'}
        self.client.post(self.url, data)
        self.assertEqual(EventInquiry.objects.get().spam_reason, 'no form token')

    def test_clean_inquiry_reports_confirmation_sent(self):
        response = self.client.post(self.url, VALID_INQUIRY)
        self.assertTrue(response.context['confirmation_sent'])
        self.assertContains(response, 'A confirmation has been sent')
        self.assertEqual(EventInquiry.objects.get().status, 'new')

    def test_rerender_after_error_keeps_original_token(self):
        response = self.client.post(self.url, {**VALID_INQUIRY, 'email': 'typo'})
        self.assertContains(response, f'name="ft" value="{VALID_INQUIRY["ft"]}"')

    def test_honeypot_is_off_screen_not_display_none(self):
        response = self.client.post(self.url, {**VALID_INQUIRY, 'email': 'typo'})
        self.assertContains(response, 'left:-10000px')
        self.assertNotContains(response, 'class="hidden" aria-hidden')


class SitewideCapTests(PublicFormTestCase):
    def test_inquiry_emails_pause_after_cap_and_staff_alerted_once(self):
        url = reverse('core:event_inquiry')
        for i in range(SITEWIDE_INQUIRY_EMAILS_PER_HOUR + 2):
            self.client.post(url, VALID_INQUIRY, HTTP_X_FORWARDED_FOR=f'203.0.113.{i}')

        # Every inquiry is saved...
        self.assertEqual(EventInquiry.objects.filter(status='new').count(), SITEWIDE_INQUIRY_EMAILS_PER_HOUR + 2)
        # ...but only the first N send their two emails, plus one alert.
        alerts = [m for m in mail.outbox if 'paused' in m.subject]
        self.assertEqual(len(alerts), 1)
        self.assertEqual(len(mail.outbox), SITEWIDE_INQUIRY_EMAILS_PER_HOUR * 2 + 1)

    def test_contact_form_tells_visitor_when_busy(self):
        url = reverse('core:contact_form')
        for i in range(SITEWIDE_CONTACT_EMAILS_PER_HOUR):
            self.client.post(url, VALID_CONTACT, HTTP_X_FORWARDED_FOR=f'203.0.113.{i}')
        response = self.client.post(url, VALID_CONTACT, HTTP_X_FORWARDED_FOR='198.51.100.1')
        self.assertContains(response, 'unusual number of messages')
        self.assertEqual(len(mail.outbox), SITEWIDE_CONTACT_EMAILS_PER_HOUR)


class ContactSpamTests(PublicFormTestCase):
    def test_flagged_contact_message_still_delivered_but_tagged(self):
        self.client.post(reverse('core:contact_form'), {**VALID_CONTACT, 'message': 'SEO services https://spam.example'})
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(mail.outbox[0].subject.startswith('[Possible spam] '))
        self.assertIn('Flagged as possible spam: link in text', mail.outbox[0].body)

    def test_clean_contact_message_not_tagged(self):
        self.client.post(reverse('core:contact_form'), VALID_CONTACT)
        self.assertFalse(mail.outbox[0].subject.startswith('[Possible spam]'))


class StaffSpamReviewTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user('mgr', password='x', is_staff=True)
        user.groups.add(Group.objects.get(name=MANAGER_GROUP))
        self.client.force_login(user)
        self.real = EventInquiry.objects.create(name='Pat', email='pat@example.com', phone='1')
        self.spam = EventInquiry.objects.create(name='Bot', email='bot@example.com', phone='1',
                                                status='spam', spam_reason='link in text')

    def test_spam_hidden_from_all_and_shown_under_spam_filter(self):
        url = reverse('staff:inquiries')
        response = self.client.get(url)
        self.assertEqual(list(response.context['inquiries']), [self.real])
        self.assertEqual(response.context['counts']['spam'], 1)
        response = self.client.get(url, {'status': 'spam'})
        self.assertEqual(list(response.context['inquiries']), [self.spam])
        self.assertContains(response, 'Flagged: link in text')

    def test_staff_can_rescue_or_mark_spam(self):
        self.client.post(reverse('staff:inquiry_status', args=[self.spam.pk]), {'status': 'new'})
        self.client.post(reverse('staff:inquiry_status', args=[self.real.pk]), {'status': 'spam'})
        self.spam.refresh_from_db()
        self.real.refresh_from_db()
        self.assertEqual((self.spam.status, self.real.status), ('new', 'spam'))
