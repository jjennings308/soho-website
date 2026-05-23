import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field

from apps.core.models import TimeStampedModel

User = get_user_model()


class SoHoMember(TimeStampedModel):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    is_email_subscribed = models.BooleanField(default=True)
    is_active = models.BooleanField(default=False)
    confirmation_token = models.UUIDField(default=uuid.uuid4, unique=True)
    unsubscribe_token = models.UUIDField(default=uuid.uuid4, unique=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'SoHo Member'
        verbose_name_plural = 'SoHo Members'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name} <{self.email}>"


class Newsletter(TimeStampedModel):
    subject = models.CharField(max_length=200)
    body = CKEditor5Field()
    sent_at = models.DateTimeField(null=True, blank=True)
    recipient_count = models.PositiveIntegerField(default=0)
    sent_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='newsletters_sent',
    )

    class Meta:
        verbose_name = 'Newsletter'
        verbose_name_plural = 'Newsletters'
        ordering = ['-created_at']

    def __str__(self):
        status = f"Sent {self.sent_at:%Y-%m-%d}" if self.sent_at else "Draft"
        return f"{self.subject} ({status})"

    @property
    def is_draft(self):
        return self.sent_at is None
