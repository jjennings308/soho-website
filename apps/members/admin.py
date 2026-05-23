import csv

from django.contrib import admin, messages
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone

from .models import Newsletter, SoHoMember


@admin.register(SoHoMember)
class SoHoMemberAdmin(admin.ModelAdmin):
    list_display = ['email', 'first_name', 'last_name', 'is_active', 'is_email_subscribed', 'confirmed_at', 'created_at']
    list_filter = ['is_active', 'is_email_subscribed']
    search_fields = ['email', 'first_name', 'last_name']
    readonly_fields = ['confirmation_token', 'unsubscribe_token', 'confirmed_at', 'created_at', 'updated_at']
    actions = ['mark_active', 'mark_inactive', 'unsubscribe_selected', 'export_active_csv']

    @admin.action(description='Mark selected members as active')
    def mark_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} member(s) marked active.")

    @admin.action(description='Mark selected members as inactive')
    def mark_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} member(s) marked inactive.")

    @admin.action(description='Unsubscribe selected members')
    def unsubscribe_selected(self, request, queryset):
        updated = queryset.update(is_email_subscribed=False)
        self.message_user(request, f"{updated} member(s) unsubscribed.")

    @admin.action(description='Export active subscribers as CSV')
    def export_active_csv(self, request, queryset):
        active = queryset.filter(is_active=True, is_email_subscribed=True)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="active_subscribers.csv"'
        writer = csv.writer(response)
        writer.writerow(['email', 'first_name', 'last_name', 'confirmed_at'])
        for member in active:
            writer.writerow([member.email, member.first_name, member.last_name, member.confirmed_at])
        return response


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ['subject', 'sent_at', 'recipient_count', 'sent_by', 'created_at']
    readonly_fields = ['sent_at', 'recipient_count', 'sent_by', 'created_at', 'updated_at']
    actions = ['send_to_subscribers']

    @admin.action(description='Send to all active subscribers')
    def send_to_subscribers(self, request, queryset):
        for newsletter in queryset:
            if not newsletter.is_draft:
                self.message_user(
                    request,
                    f'"{newsletter.subject}" has already been sent — skipped.',
                    level=messages.WARNING,
                )
                continue

            recipients = list(
                SoHoMember.objects.filter(is_active=True, is_email_subscribed=True)
                .values_list('email', flat=True)
            )
            if not recipients:
                self.message_user(request, 'No active subscribers to send to.', level=messages.WARNING)
                continue

            html_body = render_to_string('members/emails/newsletter.html', {'newsletter': newsletter})

            email = EmailMessage(
                subject=newsletter.subject,
                body=html_body,
                from_email=None,  # uses DEFAULT_FROM_EMAIL
                bcc=recipients,
            )
            email.content_subtype = 'html'
            email.send()

            newsletter.sent_at = timezone.now()
            newsletter.recipient_count = len(recipients)
            newsletter.sent_by = request.user
            newsletter.save(update_fields=['sent_at', 'recipient_count', 'sent_by'])

            self.message_user(
                request,
                f'"{newsletter.subject}" sent to {len(recipients)} subscriber(s).',
            )
