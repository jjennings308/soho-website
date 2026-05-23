from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views import View

from .models import SoHoMember


class SubscribeView(View):
    def post(self, request):
        email = request.POST.get('email', '').strip().lower()
        first_name = request.POST.get('first_name', '').strip()

        if not email or not first_name:
            return render(request, 'members/partials/subscribe_form.html', {
                'error': 'Please provide your first name and email address.',
            })

        member, created = SoHoMember.objects.get_or_create(
            email=email,
            defaults={'first_name': first_name},
        )

        if not created and member.is_active:
            return render(request, 'members/partials/subscribe_form.html', {
                'already_subscribed': True,
            })

        if created:
            member.first_name = first_name

        if not member.is_active:
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
            send_mail(
                subject='Confirm your subscription to SoHo Pittsburgh',
                message=plain_body,
                from_email=None,  # uses DEFAULT_FROM_EMAIL
                recipient_list=[member.email],
                html_message=html_body,
                fail_silently=False,
            )
            member.save()

        return render(request, 'members/partials/subscribe_form.html', {
            'success': True,
        })


class ConfirmView(View):
    def get(self, request, token):
        member = get_object_or_404(SoHoMember, confirmation_token=token)
        if not member.is_active:
            member.is_active = True
            member.confirmed_at = timezone.now()
            member.save(update_fields=['is_active', 'confirmed_at'])
        return render(request, 'members/confirm_success.html', {'member': member})


class UnsubscribeView(View):
    def get(self, request, token):
        member = get_object_or_404(SoHoMember, unsubscribe_token=token)
        if member.is_email_subscribed:
            member.is_email_subscribed = False
            member.save(update_fields=['is_email_subscribed'])
        return render(request, 'members/unsubscribe_success.html', {'member': member})
