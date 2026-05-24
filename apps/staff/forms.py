from django import forms
from django_ckeditor_5.widgets import CKEditor5Widget

from apps.core.models import SitePopup
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


class PopupForm(forms.ModelForm):
    class Meta:
        model = SitePopup
        fields = [
            'title', 'heading', 'body',
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
