from django import forms
from django.db.models import Max, Q
from django_ckeditor_5.widgets import CKEditor5Widget

from apps.core.models import SitePopup, SiteSettings
from apps.core.models import ColorScheme
from apps.events.models import EventDay
from apps.media.models import MediaCategory, MediaItem
from apps.members.models import Newsletter
from apps.menu.models import (
    Menu, MenuCategory, MenuItem, MenuItemAddon, MenuItemCategoryAssignment, MenuItemVariation, MenuSubCategory,
)


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
        help_texts = {
            'available_from': 'Eastern time. Customers only see the item during these hours. Leave blank for no start time.',
            'available_until': 'A time earlier than the start runs past midnight (22:00 until 02:00). Leave blank for no end time.',
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


class _OptionForm(forms.ModelForm):
    """One size or add-on row on the item page."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault('class', 'sp-input')


class VariationForm(_OptionForm):
    class Meta:
        model = MenuItemVariation
        fields = ['name', 'size', 'quantity', 'price', 'description', 'order', 'is_default', 'is_available']
        labels = {'size': 'Size note', 'order': 'Position', 'is_default': 'Default',
                  'is_available': 'Available'}


class AddonForm(_OptionForm):
    class Meta:
        model = MenuItemAddon
        fields = ['name', 'price', 'description', 'order', 'is_default', 'is_available']
        labels = {'order': 'Position', 'is_default': 'Default', 'is_available': 'Available'}


# Sizes and add-ons on the item page: no blank rows — "Add a size" adds one in the browser.
VariationFormSet = forms.inlineformset_factory(
    MenuItem, MenuItemVariation, form=VariationForm, extra=0, can_delete=True)
AddonFormSet = forms.inlineformset_factory(
    MenuItem, MenuItemAddon, form=AddonForm, extra=0, can_delete=True)


class PlacementForm(forms.ModelForm):
    """One saved placement on the item page's On menus tab (the category is fixed)."""

    class Meta:
        model = MenuItemCategoryAssignment
        fields = ['subcategory', 'order', 'override_price', 'note', 'is_active']
        labels = {'order': 'Position', 'override_price': 'Special price', 'is_active': 'Shown'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['order'].required = False
        self.fields['subcategory'].empty_label = 'None'
        subcategories = MenuSubCategory.objects.filter(
            Q(is_active=True) | Q(pk=self.instance.subcategory_id))
        if self.instance.category_id:
            subcategories = subcategories.filter(category_id=self.instance.category_id)
        self.fields['subcategory'].queryset = subcategories.select_related('category').order_by('order', 'name')
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault('class', 'sp-select')
            elif not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault('class', 'sp-input')

    def clean(self):
        cleaned = super().clean()
        category = cleaned.get('category') or (self.instance.category if self.instance.category_id else None)
        subcategory = cleaned.get('subcategory')
        if subcategory and category and subcategory.category_id != category.pk:
            self.add_error('subcategory', f'That subcategory isn\'t part of {category.name}.')
        # Blank position: keep it, or go to the end of the category.
        if cleaned.get('order') is None and 'order' not in self.errors:
            if self.instance.pk:
                cleaned['order'] = self.instance.order
            elif category:
                last = category.item_assignments.aggregate(last=Max('order'))['last']
                cleaned['order'] = (last or 0) + 1
        return cleaned


class _CategoryChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, category):
        menus = sorted(a.menu.title for a in category.menu_assignments.all())
        return f"{category.name} — {', '.join(menus) if menus else 'not on a menu'}"


class PlacementAddForm(PlacementForm):
    """Put the item in another category: only categories it isn't already in are offered."""

    category = _CategoryChoiceField(
        queryset=MenuCategory.objects.none(),
        error_messages={'invalid_choice': "Choose a category this item isn't already in."},
    )
    field_order = ['category', 'subcategory', 'order', 'override_price', 'note', 'is_active']

    class Meta(PlacementForm.Meta):
        fields = ['category', 'subcategory', 'order', 'override_price', 'note', 'is_active']

    def __init__(self, *args, item, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.menu_item = item
        self.fields['category'].widget.attrs.setdefault('class', 'sp-select')
        self.fields['category'].queryset = (
            MenuCategory.objects.filter(is_active=True)
            .exclude(item_assignments__menu_item=item)
            .prefetch_related('menu_assignments__menu')
            .order_by('name')
        )


# (heading, field names, menu types it applies to or None for all) of the menu Settings form.
MENU_GROUPS = [
    ('Basics', ['title', 'display_name', 'description', 'menu_type'], None),
    ('Where it shows', ['role', 'is_active', 'active_from', 'active_until', 'days_of_week'], None),
    ('Weekly specials', ['valid_from', 'valid_until'], 'weekly_specials'),
    ('Promotion', ['color_scheme', 'homepage_slot'], 'promo'),
]


class MenuForm(forms.ModelForm):
    """
    Settings of a menu. Slug and the legacy is_default are left out. Taking a live
    role or homepage slot, or leaving a role empty, must be confirmed (confirm_live).
    The help texts say what each setting really does on the public site.
    """
    days_of_week = forms.TypedMultipleChoiceField(
        choices=Menu.DAYS_OF_WEEK, coerce=int, required=False,
        widget=forms.CheckboxSelectMultiple, label='Days of the week',
        help_text='Promotions, their homepage slot and the menu\'s own page show on these days only '
                  '(Eastern time). None ticked means every day. A live role isn\'t affected.',
    )
    confirm_live = forms.BooleanField(required=False, label='Yes, change the live site')

    class Meta:
        model = Menu
        fields = [name for _, names, _types in MENU_GROUPS for name in names]
        labels = {
            'display_name': 'Display name', 'menu_type': 'Type', 'role': 'Live menu role',
            'is_active': 'Active', 'active_from': 'Active from', 'active_until': 'Active until',
            'valid_from': 'Valid from', 'valid_until': 'Valid until',
            'color_scheme': 'Color scheme', 'homepage_slot': 'Homepage slot',
        }
        help_texts = {
            'title': 'For staff.',
            'display_name': 'What customers see. Blank uses the title.',
            'role': 'Sets which menu customers get on the menu pages. Only one menu can hold each role.',
            'is_active': "Off hides a promotion, its homepage slot and the menu's own page. "
                         'A menu holding a live role still shows: change its role first.',
            'active_from': "Applies to promotions and the menu's own page, not to a live role or homepage slot.",
            'active_until': "Applies to promotions and the menu's own page, not to a live role or homepage slot.",
            'valid_from': 'The menu shows as this week\'s specials from this day.',
            'valid_until': 'Last day it shows.',
            'color_scheme': 'Blank uses the default scheme.',
            'homepage_slot': 'Only one menu can be in each slot. Shows while the menu is Active.',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
            'active_from': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'active_until': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'valid_from': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'valid_until': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    def __init__(self, *args, read_only=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.needs_confirm = False
        if self.instance.menu_type not in dict(Menu.MENU_TYPE_CHOICES):
            del self.fields['menu_type']        # legacy type (soho-menu): keep it as it is
        elif not self.instance.pk:
            self.fields['menu_type'].choices = [('', 'Choose a type…')] + Menu.MENU_TYPE_CHOICES
            self.initial['menu_type'] = ''
        self.fields['color_scheme'].empty_label = 'Default scheme'
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
                pass
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault('class', 'sp-select')
            elif isinstance(widget, forms.Textarea):
                widget.attrs.setdefault('class', 'sp-textarea')
            else:
                widget.attrs.setdefault('class', 'sp-input')
            if read_only:
                field.disabled = True

    def clean(self):
        cleaned = super().clean()
        menu_type = cleaned.get('menu_type', self.instance.menu_type)
        # Hidden sections don't apply to other types (only promos may have custom colors).
        if menu_type != 'promo':
            cleaned['color_scheme'], cleaned['homepage_slot'] = None, 'none'
        if menu_type != 'weekly_specials':
            cleaned['valid_from'], cleaned['valid_until'] = None, None
        warnings = self._live_changes(cleaned)
        if warnings and not cleaned.get('confirm_live'):
            self.needs_confirm = True
            for warning in warnings:
                self.add_error(None, warning)
        return cleaned

    def _live_changes(self, cleaned):
        menus = Menu.objects.exclude(pk=self.instance.pk)
        roles = dict(Menu.ROLE_CHOICES)
        role, old_role = cleaned.get('role'), self.instance.role if self.instance.pk else 'none'
        slot, old_slot = cleaned.get('homepage_slot'), self.instance.homepage_slot if self.instance.pk else 'none'
        warnings = []
        if role and role != old_role:
            holder = menus.filter(role=role).first() if role != 'none' else None
            if holder:
                warnings.append(f'"{holder.title}" is the {roles[role]} now. Saving replaces it, and customers '
                                'see this menu straight away.')
            if old_role != 'none':
                warnings.append(f'This menu is the {roles[old_role]} now. Nothing will replace it, so customers '
                                'see "coming soon" there.')
        if slot and slot not in ('none', old_slot):
            holder = menus.filter(homepage_slot=slot).first()
            if holder:
                warnings.append(f'"{holder.title}" is in that homepage slot now. Saving takes it out.')
        return warnings

    def save(self, commit=True):
        menu = super().save(commit=commit)
        if commit and menu.homepage_slot != 'none':
            Menu.objects.filter(homepage_slot=menu.homepage_slot).exclude(pk=menu.pk).update(homepage_slot='none')
        return menu

    @property
    def selected_type(self):
        return self['menu_type'].value() or '' if 'menu_type' in self.fields else self.instance.menu_type

    def groups(self):
        """[(heading, menu type or None, [bound fields])] for the template."""
        return [(title, only_for, [self[name] for name in names if name in self.fields])
                for title, names, only_for in MENU_GROUPS]


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
