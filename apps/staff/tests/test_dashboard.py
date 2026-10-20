from datetime import timedelta
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.core.models import SiteSettings
from apps.staff.views import _with_freshness_badge


class FreshnessBadgeTests(TestCase):
    def badge(self, days_ago):
        menu = SimpleNamespace(updated_at=timezone.now() - timedelta(days=days_ago, hours=1))
        return _with_freshness_badge(menu)['badge_class']

    def test_thresholds(self):
        self.assertEqual(self.badge(7), 'sp-pill--green')
        self.assertEqual(self.badge(8), 'sp-pill--gold')
        self.assertEqual(self.badge(14), 'sp-pill--gold')
        self.assertEqual(self.badge(15), 'sp-pill--red')


class StaffPagesTests(TestCase):
    def setUp(self):
        staff = get_user_model().objects.create_user('staff', password='x', is_staff=True)
        self.client.force_login(staff)

    def test_dashboard_renders(self):
        self.assertEqual(self.client.get(reverse('staff:dashboard')).status_code, 200)

    def test_settings_page_works_with_no_settings_row(self):
        self.client.force_login(get_user_model().objects.create_superuser('root', 'root@example.com', 'x'))
        SiteSettings.objects.all().delete()
        self.assertEqual(self.client.get(reverse('staff:settings')).status_code, 200)

    def test_non_staff_user_gets_403(self):
        self.client.force_login(get_user_model().objects.create_user('guest', password='x'))
        self.assertEqual(self.client.get(reverse('staff:dashboard')).status_code, 403)
