from django import forms
from .widgets import DaysOfWeekWidget


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