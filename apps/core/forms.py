from django import forms
from .models import EventInquiry
from .widgets import DaysOfWeekWidget


def _single_line(value):
    """Collapse whitespace so a name can't inject email header lines."""
    return ' '.join(value.split())


class ContactForm(forms.Form):
    name = forms.CharField(max_length=200, error_messages={'required': 'Please enter your name.'})
    email = forms.EmailField(error_messages={
        'required': 'Please enter your email.',
        'invalid': 'Please enter a valid email address.',
    })
    phone = forms.CharField(max_length=30, required=False)
    message = forms.CharField(max_length=5000, error_messages={'required': 'Please enter a message.'})

    def clean_name(self):
        return _single_line(self.cleaned_data['name'])


class EventInquiryForm(forms.ModelForm):
    # Select fields fall back to the model default when omitted, since the
    # partial has no place to show an error for them.
    OPTIONAL_CHOICE_FIELDS = ('preferred_contact', 'event_type', 'menu_preference')

    guest_count = forms.IntegerField(
        required=False, min_value=1, max_value=10000,
        error_messages={'invalid': 'Please enter a number of guests.'},
    )
    message = forms.CharField(required=False, max_length=5000)

    class Meta:
        model = EventInquiry
        fields = [
            'name', 'email', 'phone', 'preferred_contact', 'event_type',
            'guest_count', 'preferred_date', 'menu_preference', 'message',
        ]
        error_messages = {
            'name':           {'required': 'Please enter your name.'},
            'email':          {'required': 'Please enter your email.',
                               'invalid': 'Please enter a valid email address.'},
            'phone':          {'required': 'Please enter your phone number.'},
            'preferred_date': {'invalid': 'Please enter a valid date.'},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in self.OPTIONAL_CHOICE_FIELDS:
            self.fields[name].required = False

    def clean_name(self):
        return _single_line(self.cleaned_data['name'])

    def clean(self):
        cleaned = super().clean()
        for name in self.OPTIONAL_CHOICE_FIELDS:
            if not cleaned.get(name):
                cleaned[name] = EventInquiry._meta.get_field(name).default
        return cleaned


class DaysOfWeekField(forms.Field):
    """
    Form field for days_of_week JSONField.
    Converts checkbox POST values (list of strings) to a list of integers,
    and back again for rendering.
    """
    widget = DaysOfWeekWidget

    def prepare_value(self, value):
        if isinstance(value, list):
            return value
        return []

    def to_python(self, value):
        if not value:
            return []
        try:
            return sorted(set(int(v) for v in value if str(v).isdigit()))
        except (ValueError, TypeError):
            raise forms.ValidationError('Invalid day selection.')

    def validate(self, value):
        super().validate(value)
        valid = {0, 1, 2, 3, 4, 5, 6}
        if not all(v in valid for v in value):
            raise forms.ValidationError('Invalid day value.')