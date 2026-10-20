from django.test import TestCase

from apps.core.models import ColorScheme


class ColorSchemeDefaultTests(TestCase):
    def test_only_one_default(self):
        first = ColorScheme.objects.create(name='Black & Gold', is_default=True)
        second = ColorScheme.objects.create(name='Holiday Red', is_default=True)
        first.refresh_from_db()
        self.assertFalse(first.is_default)
        self.assertTrue(second.is_default)

    def test_saving_non_default_keeps_existing_default(self):
        default = ColorScheme.objects.create(name='Black & Gold', is_default=True)
        ColorScheme.objects.create(name='Holiday Red')
        default.refresh_from_db()
        self.assertTrue(default.is_default)
