from django import forms

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
        fields = ['image', 'caption', 'category', 'display_order']


class NewsletterForm(forms.ModelForm):
    class Meta:
        model = Newsletter
        fields = ['subject', 'body']
        widgets = {
            'body': forms.Textarea(attrs={'rows': 16, 'placeholder': 'Write your newsletter here…'}),
        }
