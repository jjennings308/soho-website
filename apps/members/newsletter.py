"""
Newsletter sending — the single send path used by the staff portal and the
Django admin action.
"""
import logging
import re
import smtplib
from dataclasses import dataclass
from html import unescape

from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags

from .models import Newsletter, SoHoMember

logger = logging.getLogger(__name__)


@dataclass
class SendResult:
    sent: int
    failed: int


def prepare_newsletter_html(html, base_url):
    """Make newsletter HTML safe for email clients."""
    # Relative media URLs → absolute so email clients can load images
    html = html.replace('src="/media/', f'src="{base_url}media/')
    html = html.replace('href="/media/', f'href="{base_url}media/')

    # CKEditor5 wraps resized images in <figure style="width:X%">.
    # Email clients ignore figure styles, so move width onto the img tag.
    def unwrap_figure(m):
        figure_attrs = m.group(1)
        content = m.group(2)
        w = re.search(r'width\s*:\s*([\d.]+%)', figure_attrs)
        width_style = f'width:{w.group(1)};' if w else ''
        content = re.sub(
            r'<img\b',
            f'<img style="{width_style}max-width:100%;height:auto;"',
            content,
            count=1,
        )
        return content

    html = re.sub(r'<figure\b([^>]*)>(.*?)</figure>', unwrap_figure, html, flags=re.DOTALL | re.IGNORECASE)
    return html


def html_to_text(html):
    """Rough plain-text version of rich-text HTML for the text/plain part."""
    text = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
    text = re.sub(r'</(p|div|h[1-6]|li|blockquote)>', '\n\n', text, flags=re.IGNORECASE)
    text = unescape(strip_tags(text)).replace('\xa0', ' ')
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _build_message(newsletter, member, base_url):
    unsubscribe_url = base_url.rstrip('/') + reverse(
        'members:unsubscribe', kwargs={'token': member.unsubscribe_token}
    )
    context = {
        'newsletter': newsletter,
        'member': member,
        'unsubscribe_url': unsubscribe_url,
        'site_url': base_url,
    }
    html_body = prepare_newsletter_html(
        render_to_string('members/emails/newsletter.html', context), base_url
    )
    text_body = render_to_string('members/emails/newsletter.txt', {
        **context, 'body_text': html_to_text(newsletter.body),
    })
    msg = EmailMultiAlternatives(
        subject=newsletter.subject,
        body=text_body,
        from_email=None,  # uses DEFAULT_FROM_EMAIL
        to=[member.email],
        headers={
            # RFC 8058 one-click unsubscribe, expected by Gmail/Yahoo for bulk mail.
            # The URL accepts POST without CSRF (see UnsubscribeView).
            'List-Unsubscribe': f'<{unsubscribe_url}>',
            'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click',
        },
    )
    msg.attach_alternative(html_body, 'text/html')
    return msg


def send_newsletter(newsletter, *, sent_by, base_url):
    """
    Send `newsletter` to every confirmed, subscribed member, one email each.

    The newsletter is claimed by an atomic update before anything is sent, so
    a double-click or a second staff member can never send it twice. Returns
    None if it had already been claimed, otherwise a SendResult.

    If nothing was sent (no subscribers, or the mail server is down), the
    claim is released so the newsletter stays a draft and can be retried.
    `base_url` is the site root with a trailing slash, e.g. from
    request.build_absolute_uri('/').
    """
    claimed = Newsletter.objects.filter(pk=newsletter.pk, sent_at__isnull=True).update(
        sent_at=timezone.now(), sent_by=sent_by,
    )
    if not claimed:
        return None
    newsletter.refresh_from_db()

    members = list(SoHoMember.objects.filter(is_active=True, is_email_subscribed=True))
    sent = failed = 0
    connection = get_connection()
    try:
        for member in members:
            try:
                connection.send_messages([_build_message(newsletter, member, base_url)])
                sent += 1
            except (smtplib.SMTPException, OSError):
                failed += 1
                logger.exception('Newsletter %s failed for member %s', newsletter.pk, member.pk)
                # Drop a possibly broken connection; the next send reopens it.
                connection.close()
    finally:
        connection.close()
        if sent == 0:
            Newsletter.objects.filter(pk=newsletter.pk).update(sent_at=None, sent_by=None)
            newsletter.refresh_from_db()
        else:
            newsletter.recipient_count = sent
            newsletter.save(update_fields=['recipient_count'])

    return SendResult(sent=sent, failed=failed)
