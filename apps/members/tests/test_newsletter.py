import smtplib
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from apps.members.models import Newsletter, SoHoMember
from apps.members.newsletter import html_to_text, send_newsletter
from apps.staff.permissions import MANAGER_GROUP

BASE_URL = 'https://soho.example.com/'


def make_member(email, **kwargs):
    defaults = {'first_name': 'Pat', 'is_active': True, 'is_email_subscribed': True}
    return SoHoMember.objects.create(email=email, **{**defaults, **kwargs})


class SendNewsletterTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user('staff', password='x', is_staff=True)
        self.newsletter = Newsletter.objects.create(
            subject='Fall menu', body='<p>New <strong>pumpkin</strong> ale &amp; more</p>',
        )

    def send(self):
        return send_newsletter(self.newsletter, sent_by=self.staff, base_url=BASE_URL)

    def test_sends_one_email_per_confirmed_subscriber(self):
        make_member('a@example.com')
        make_member('b@example.com')
        make_member('unconfirmed@example.com', is_active=False)
        make_member('gone@example.com', is_email_subscribed=False)

        result = self.send()

        self.assertEqual((result.sent, result.failed), (2, 0))
        self.assertEqual(sorted(m.to[0] for m in mail.outbox), ['a@example.com', 'b@example.com'])
        self.newsletter.refresh_from_db()
        self.assertIsNotNone(self.newsletter.sent_at)
        self.assertEqual(self.newsletter.sent_by, self.staff)
        self.assertEqual(self.newsletter.recipient_count, 2)

    def test_second_send_is_refused(self):
        make_member('a@example.com')
        self.send()
        stale_copy = Newsletter.objects.get(pk=self.newsletter.pk)
        stale_copy.sent_at = None  # simulate a second request loaded before the first finished
        self.assertIsNone(send_newsletter(stale_copy, sent_by=self.staff, base_url=BASE_URL))
        self.assertEqual(len(mail.outbox), 1)

    def test_message_has_text_html_and_one_click_unsubscribe(self):
        member = make_member('a@example.com')
        self.send()
        msg = mail.outbox[0]
        unsubscribe_url = f'https://soho.example.com/unsubscribe/{member.unsubscribe_token}/'

        self.assertIn('New pumpkin ale & more', msg.body)
        self.assertIn(unsubscribe_url, msg.body)
        html, mimetype = msg.alternatives[0]
        self.assertEqual(mimetype, 'text/html')
        self.assertIn('<strong>pumpkin</strong>', html)
        self.assertIn(unsubscribe_url, html)
        self.assertEqual(msg.extra_headers['List-Unsubscribe'], f'<{unsubscribe_url}>')
        self.assertEqual(msg.extra_headers['List-Unsubscribe-Post'], 'List-Unsubscribe=One-Click')

    def test_relative_media_urls_made_absolute(self):
        self.newsletter.body = '<p><img src="/media/uploads/a.jpg"></p>'
        self.newsletter.save()
        make_member('a@example.com')
        self.send()
        self.assertIn('src="https://soho.example.com/media/uploads/a.jpg"', mail.outbox[0].alternatives[0][0])

    def test_partial_failure_counts_only_successful_sends(self):
        make_member('a@example.com')
        make_member('b@example.com')
        make_member('c@example.com')
        from django.core.mail.backends.locmem import EmailBackend
        real_send = EmailBackend.send_messages

        def flaky(backend, messages):
            if messages[0].to == ['b@example.com']:
                raise smtplib.SMTPRecipientsRefused({})
            return real_send(backend, messages)

        with mock.patch.object(EmailBackend, 'send_messages', flaky), \
                self.assertLogs('apps.members.newsletter', level='ERROR'):
            result = self.send()

        self.assertEqual((result.sent, result.failed), (2, 1))
        self.newsletter.refresh_from_db()
        self.assertEqual(self.newsletter.recipient_count, 2)
        self.assertFalse(self.newsletter.is_draft)

    def test_total_failure_leaves_newsletter_as_draft(self):
        make_member('a@example.com')
        with mock.patch('django.core.mail.backends.locmem.EmailBackend.send_messages',
                        side_effect=ConnectionRefusedError()), \
                self.assertLogs('apps.members.newsletter', level='ERROR'):
            result = self.send()
        self.assertEqual((result.sent, result.failed), (0, 1))
        self.newsletter.refresh_from_db()
        self.assertTrue(self.newsletter.is_draft)
        self.assertIsNone(self.newsletter.sent_by)

    def test_no_subscribers_leaves_newsletter_as_draft(self):
        result = self.send()
        self.assertEqual((result.sent, result.failed), (0, 0))
        self.newsletter.refresh_from_db()
        self.assertTrue(self.newsletter.is_draft)


class HtmlToTextTests(TestCase):
    def test_paragraphs_and_breaks_become_newlines(self):
        self.assertEqual(html_to_text('<p>One<br>Two</p><p>Three&nbsp;four</p>'), 'One\nTwo\n\nThree four')


class StaffNewsletterSendViewTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user('staff', password='x', is_staff=True)
        self.staff.groups.add(Group.objects.get(name=MANAGER_GROUP))
        self.client.force_login(self.staff)
        self.newsletter = Newsletter.objects.create(subject='Hi', body='<p>Hello</p>')
        self.url = reverse('staff:newsletter_send', args=[self.newsletter.pk])

    def test_double_post_sends_once(self):
        make_member('a@example.com')
        self.client.post(self.url)
        response = self.client.post(self.url, follow=True)
        self.assertEqual(len(mail.outbox), 1)
        self.assertContains(response, 'already been sent')

    def test_reports_no_subscribers(self):
        response = self.client.post(self.url, follow=True)
        self.assertContains(response, 'no active subscribers')
        self.newsletter.refresh_from_db()
        self.assertTrue(self.newsletter.is_draft)


class AdminSendActionTests(TestCase):
    def test_admin_action_sends_individual_emails_with_unsubscribe_links(self):
        admin_user = get_user_model().objects.create_superuser('admin', 'admin@example.com', 'x')
        self.client.force_login(admin_user)
        newsletter = Newsletter.objects.create(subject='Hi', body='<p>Hello</p>')
        make_member('a@example.com')
        make_member('b@example.com')

        self.client.post(reverse('admin:members_newsletter_changelist'), {
            'action': 'send_to_subscribers', '_selected_action': [newsletter.pk],
        })

        self.assertEqual(len(mail.outbox), 2)
        for msg in mail.outbox:
            self.assertEqual(len(msg.to), 1)
            self.assertEqual(msg.bcc, [])
            self.assertIn('List-Unsubscribe', msg.extra_headers)
