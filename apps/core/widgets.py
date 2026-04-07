from django import forms
from django.utils.safestring import mark_safe


class DaysOfWeekWidget(forms.Widget):
    """
    Renders a row of checkboxes for day-of-week selection.
    Stores values as a JSON list of integers matching Python's weekday():
        0=Monday, 1=Tuesday, ... 6=Sunday
    """
    DAYS = [
        (0, 'Mon'),
        (1, 'Tue'),
        (2, 'Wed'),
        (3, 'Thu'),
        (4, 'Fri'),
        (5, 'Sat'),
        (6, 'Sun'),
    ]

    def render(self, name, value, attrs=None, renderer=None):
        if isinstance(value, str):
            import json
            try:
                value = json.loads(value)
            except (ValueError, TypeError):
                value = []
        if not isinstance(value, list):
            value = []

        checkboxes = []
        for day_int, day_label in self.DAYS:
            checked = 'checked' if day_int in value else ''
            checkboxes.append(
                f'<label style="margin-right:12px; font-weight:normal;">'
                f'<input type="checkbox" name="{name}" value="{day_int}" {checked} '
                f'style="margin-right:4px;">'
                f'{day_label}</label>'
            )

        return mark_safe(
            '<div style="padding:8px 0;">'
            + ''.join(checkboxes) +
            '<p class="help" style="margin-top:6px; color:#999;">'
            'Leave all unchecked for every day.</p>'
            '</div>'
        )
        
    def value_from_datadict(self, data, files, name):
        return data.getlist(name)