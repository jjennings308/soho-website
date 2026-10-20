import logging
import smtplib
import uuid

from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views import View

from apps.core.utils import clear_throttle, client_ip, honeypot_tripped, is_throttled

from .models import SoHoMember

logger = logging.getLogger(__name__)

# Confirmation emails allowed per visitor IP per hour, and the minimum gap
# between confirmation emails to any one address.
SUBSCRIBE_EMAILS_PER_IP_PER_HOUR = 3
SUBSCRIBE_EMAIL_RESEND_SECONDS = 15 * 60


class SubscribeView(View):
    def post(self, request):
        if honeypot_tripped(request):
            return render(request, 'members/partials/subscribe_form.html', {'success': True})

        email = request.POST.get('email', '').strip().lower()
        first_name = request.POST.get('first_name', '').strip()

        if not email or not first_name:
            return render(request, 'members/partials/subscribe_form.html', {
                'error': 'Please provide your first name and email address.',
            })
        try:
            validate_email(email)
        except ValidationError:
            return render(request, 'members/partials/subscribe_form.html', {
                'error': 'Please enter a valid email address.',
            })
        first_name = first_name[:SoHoMember._meta.get_field('first_name').max_length]

        member, created = SoHoMember.objects.get_or_create(
            email=email,
            defaults={'first_name': first_name},
        )

        if member.is_active and member.is_email_subscribed:
            return render(request, 'members/partials/subscribe_form.html', {
                'already_subscribed': True,
            })

        if not created:
            # Unconfirmed sign-up being retried, or a past subscriber who
            # unsubscribed coming back. Either way they re-confirm by email.
            member.first_name = first_name
            member.save(update_fields=['first_name'])

        if is_throttled(f'subscribe-ip:{client_ip(request)}', SUBSCRIBE_EMAILS_PER_IP_PER_HOUR, 3600):
            return render(request, 'members/partials/subscribe_form.html', {
                'error': 'Too many sign-up attempts. Please try again later.',
            })
        address_key = f'subscribe-email:{member.email}'
        if is_throttled(address_key, 1, SUBSCRIBE_EMAIL_RESEND_SECONDS):
            # A confirmation went to this address recently. Don't send
            # another, and don't reveal that to whoever is submitting.
            return render(request, 'members/partials/subscribe_form.html', {'success': True})

        # (Re-)send the confirmation email whether new or previously unconfirmed
        confirm_url = request.build_absolute_uri(
            reverse('members:confirm', kwargs={'token': member.confirmation_token})
        )
        html_body = render_to_string('members/emails/confirm_subscription.html', {
            'member': member,
            'confirm_url': confirm_url,
        })
        plain_body = render_to_string('members/emails/confirm_subscription.txt', {
            'member': member,
            'confirm_url': confirm_url,
        })
        try:
            send_mail(
                subject='Confirm your subscription to SoHo Pittsburgh',
                message=plain_body,
                from_email=None,  # uses DEFAULT_FROM_EMAIL
                recipient_list=[member.email],
                html_message=html_body,
                fail_silently=False,
            )
        except (smtplib.SMTPException, OSError):
            logger.exception('Subscription confirmation email failed for member %s', member.pk)
            # Nothing was sent, so let the visitor retry straight away
            clear_throttle(address_key)
            return render(request, 'members/partials/subscribe_form.html', {
                'error': "We couldn't send your confirmation email just now. Please try again in a few minutes.",
            })

        return render(request, 'members/partials/subscribe_form.html', {
            'success': True,
        })


class ConfirmView(View):
    def get(self, request, token):
        member = get_object_or_404(SoHoMember, confirmation_token=token)
        if not member.is_active or not member.is_email_subscribed:
            member.is_active = True
            member.is_email_subscribed = True
            member.confirmed_at = timezone.now()
            member.save(update_fields=['is_active', 'is_email_subscribed', 'confirmed_at'])
        return render(request, 'members/confirm_success.html', {'member': member})


@method_decorator(csrf_exempt, name='dispatch')
class UnsubscribeView(View):
    """
    GET shows a confirmation page; POST unsubscribes. GET must not act, because
    mail security scanners fetch every link in an email. POST is CSRF-exempt so
    mail clients can use RFC 8058 one-click unsubscribe (List-Unsubscribe-Post);
    the secret token in the URL is the authorization.
    """

    def get(self, request, token):
        member = get_object_or_404(SoHoMember, unsubscribe_token=token)
        return render(request, 'members/unsubscribe_confirm.html', {'member': member})

    def post(self, request, token):
        member = get_object_or_404(SoHoMember, unsubscribe_token=token)
        if member.is_email_subscribed:
            member.is_email_subscribed = False
            # Retire the old confirmation link so it can't silently re-subscribe them
            member.confirmation_token = uuid.uuid4()
            member.save(update_fields=['is_email_subscribed', 'confirmation_token'])
        return render(request, 'members/unsubscribe_success.html', {'member': member})
