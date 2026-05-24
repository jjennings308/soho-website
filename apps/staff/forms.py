from django import forms
from django_ckeditor_5.widgets import CKEditor5Widget

from apps.core.models import SitePopup, SiteSettings
from apps.menu.models import PromoColorScheme
from apps.events.models import EventDay
from apps.gallery.models import GalleryCategory, GalleryItem
from apps.members.models import Newsletter


class EventForm(forms.ModelForm):
    class Meta:
        model = EventDay
        fields = [
            'date', 'event_type', 'label',
            'team', 'home_away', 'game_time',
            'limited_menu', 'is_active',
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'game_time': forms.TimeInput(attrs={'type': 'time'}),
        }


class GalleryUploadForm(forms.ModelForm):
    class Meta:
        model = GalleryItem
        fields = ['image', 'caption', 'category', 'menu_item', 'display_order']


class NewsletterForm(forms.ModelForm):
    class Meta:
        model = Newsletter
        fields = ['subject', 'body']
        widgets = {
            'body': CKEditor5Widget(config_name='newsletter', attrs={'required': True}),
        }


class SiteSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = [
            'notification_email',
            'email',
            'phone',
            'reservations_url',
        ]
        labels = {
            'notification_email': 'Internal notification email',
            'email':              'Public contact email',
            'phone':              'Phone number',
            'reservations_url':   'Reservations URL',
        }
        help_texts = {
            'notification_email': 'Where inquiry and contact-form alerts are sent (staff only — not shown on site).',
            'email':              'Displayed on the site and in the footer.',
            'reservations_url':   'Link shown on the homepage reservation bar.',
        }


class ColorSchemeForm(forms.ModelForm):
    class Meta:
        model = PromoColorScheme
        fields = ['name', 'primary_color', 'accent_color', 'text_color', 'bg_color', 'is_default']
        widgets = {
            'primary_color': forms.TextInput(attrs={'type': 'color'}),
            'accent_color':  forms.TextInput(attrs={'type': 'color'}),
            'text_color':    forms.TextInput(attrs={'type': 'color'}),
            'bg_color':      forms.TextInput(attrs={'type': 'color'}),
        }


class PopupForm(forms.ModelForm):
    class Meta:
        model = SitePopup
        fields = [
            'title', 'heading', 'body',
            'show_subscribe_form',
            'cta_label', 'cta_url',
            'image',
            'bg_color', 'text_color', 'accent_color',
            'show_delay',
        ]
        widgets = {
            'body':         forms.Textarea(attrs={'rows': 4}),
            'bg_color':     forms.TextInput(attrs={'type': 'color'}),
            'text_color':   forms.TextInput(attrs={'type': 'color'}),
            'accent_color': forms.TextInput(attrs={'type': 'color'}),
        }
