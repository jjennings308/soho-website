from django import forms
from django_ckeditor_5.widgets import CKEditor5Widget

from apps.core.models import SitePopup, SiteSettings
from apps.core.models import ColorScheme
from apps.events.models import EventDay
from apps.media.models import MediaCategory, MediaItem
from apps.members.models import Newsletter
from apps.menu.models import MenuItem


class EventForm(forms.ModelForm):
    class Meta:
        model = EventDay
        fields = [
            'date', 'event_type', 'label',
            'team', 'home_away', 'game_time',
            'limited_menu', 'is_active',
        ]
        widgets = {
            'date':      forms.DateInput(attrs={'type': 'date', 'class': 'sp-input'}),
            'game_time': forms.TimeInput(attrs={'type': 'time', 'class': 'sp-input'}),
        }



# (heading, fields) of the item page's Details section, in page order.
MENU_ITEM_GROUPS = [
    ('Basics', ['name', 'short_description', 'description']),
    ('Price', ['price_display', 'price', 'sale_price']),
    ('Dietary & allergens', ['dietary_type', 'is_gluten_free', 'is_vegan', 'is_dairy_free',
                             'is_nut_free', 'contains_shellfish', 'allergen_info',
                             'spice_level', 'calories']),
    ('Labels', ['is_featured', 'is_chef_special', 'is_new', 'is_seasonal']),
    ('Availability', ['is_available', 'available_from', 'available_until']),
]


class MenuItemForm(forms.ModelForm):
    """Details section of the staff item page. Slug, has_variations / has_addons,
    preparation_time and recurrence fields are deliberately left out."""

    class Meta:
        model = MenuItem
        fields = [name for _, names in MENU_ITEM_GROUPS for name in names]
        labels = {
            'price_display': 'Show price as',
            'sale_price': 'Sale price',
            'dietary_type': 'Dietary type',
            'is_gluten_free': 'Gluten free',
            'is_vegan': 'Vegan',
            'is_dairy_free': 'Dairy free',
            'is_nut_free': 'Nut free',
            'contains_shellfish': 'Contains shellfish',
            'allergen_info': 'Allergen info',
            'is_featured': 'Featured',
            'is_chef_special': "Chef's special",
            'is_new': 'New',
            'is_seasonal': 'Seasonal',
            'is_available': 'Available',
            'available_from': 'Available from',
            'available_until': 'Available until',
        }
        widgets = {
            'description': CKEditor5Widget(config_name='default'),
            'allergen_info': forms.Textarea(attrs={'rows': 2}),
            'available_from': forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
            'available_until': forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
        }

    def __init__(self, *args, read_only=False, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput) or name == 'description':
                pass
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault('class', 'sp-select')
            elif isinstance(widget, forms.Textarea):
                widget.attrs.setdefault('class', 'sp-textarea')
            else:
                widget.attrs.setdefault('class', 'sp-input')
            if read_only:
                field.disabled = True

    def groups(self):
        """[(heading, [bound fields])] for the template."""
        return [(title, [self[name] for name in names]) for title, names in MENU_ITEM_GROUPS]


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
        model = ColorScheme
        fields = ['name', 'primary_color', 'accent_color', 'text_color', 'bg_color', 'is_default']
        widgets = {
            'primary_color': forms.TextInput(attrs={'type': 'color'}),
            'accent_color':  forms.TextInput(attrs={'type': 'color'}),
            'text_color':    forms.TextInput(attrs={'type': 'color'}),
            'bg_color':      forms.TextInput(attrs={'type': 'color'}),
        }


class MediaItemUploadForm(forms.ModelForm):
    """Form for uploading a new image to the media library."""
    class Meta:
        model = MediaItem
        fields = ['file', 'name', 'category', 'alt_text', 'caption', 'is_published']
        widgets = {
            'alt_text': forms.TextInput(attrs={'placeholder': 'Describe the image for accessibility'}),
            'caption':  forms.TextInput(attrs={'placeholder': 'Public caption shown in gallery lightbox'}),
        }
        labels = {
            'file':       'Image file',
            'is_published': 'Publish immediately',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = MediaCategory.objects.order_by('display_order', 'name')
        self.fields['category'].required = False
        self.fields['alt_text'].required = False
        self.fields['caption'].required = False


class MediaItemEditForm(forms.ModelForm):
    """Form for editing an existing MediaItem's metadata."""
    class Meta:
        model = MediaItem
        fields = ['name', 'category', 'alt_text', 'caption', 'display_order', 'is_published']
        widgets = {
            'alt_text':      forms.TextInput(attrs={'placeholder': 'Describe the image for accessibility'}),
            'caption':       forms.TextInput(attrs={'placeholder': 'Public caption shown in gallery lightbox'}),
            'display_order': forms.NumberInput(attrs={'min': 0}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = MediaCategory.objects.order_by('display_order', 'name')
        self.fields['category'].required = False
        self.fields['alt_text'].required = False
        self.fields['caption'].required = False


class PopupForm(forms.ModelForm):
    class Meta:
        model = SitePopup
        fields = [
            'title', 'heading', 'body',
            'show_subscribe_form',
            'cta_label', 'cta_url',
            # 'image' omitted — will be a media picker in Step 5 of the media migration
            'bg_color', 'text_color', 'primary_color', 'accent_color',
            'show_delay',
        ]
        widgets = {
            'body':          forms.Textarea(attrs={'rows': 4}),
            'bg_color':      forms.TextInput(attrs={'type': 'color'}),
            'text_color':    forms.TextInput(attrs={'type': 'color'}),
            'primary_color': forms.TextInput(attrs={'type': 'color'}),
            'accent_color':  forms.TextInput(attrs={'type': 'color'}),
        }
