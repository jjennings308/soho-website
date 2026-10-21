from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import URLPattern, reverse

from apps.staff import urls as staff_urls
from apps.staff.permissions import MANAGER_GROUP

# Pages a read-only (Tier 2) staff user may GET. Everything else is denied.
TIER2_READABLE = {'dashboard', 'menu_mode', 'events', 'menu_item_list', 'colors', 'help'}
SUPERUSER_ONLY = {'settings', 'color_scheme_add', 'color_scheme_edit', 'color_scheme_delete'}
PUBLIC = {'login', 'logout'}


def staff_url_names():
    return [p.name for p in staff_urls.urlpatterns if isinstance(p, URLPattern) and p.name not in PUBLIC]


def url_for(name):
    pattern = next(p for p in staff_urls.urlpatterns if getattr(p, 'name', None) == name)
    route = str(pattern.pattern)
    kwargs = {'pk': 1} if '<int:pk>' in route else {'kind': 'items'} if '<slug:kind>' in route else {}
    return reverse(f'staff:{name}', kwargs=kwargs)


User = get_user_model()


class TierTestCase(TestCase):
    def tier2(self):
        return User.objects.create_user('tier2', password='x', is_staff=True)

    def tier1(self):
        user = User.objects.create_user('tier1', password='x', is_staff=True)
        user.groups.add(Group.objects.get(name=MANAGER_GROUP))
        return user

    def superuser(self):
        return User.objects.create_superuser('root', 'root@example.com', 'x')


class EveryStaffUrlTests(TierTestCase):
    """Guards against a new view being accidentally open to read-only staff."""

    def test_tier2_can_only_get_readable_pages(self):
        self.client.force_login(self.tier2())
        for name in staff_url_names():
            with self.subTest(name=name):
                get_status = self.client.get(url_for(name)).status_code
                if name in TIER2_READABLE:
                    self.assertEqual(get_status, 200)
                else:
                    self.assertEqual(get_status, 403)
                self.assertEqual(self.client.post(url_for(name)).status_code, 403)

    def test_tier1_denied_only_superuser_pages(self):
        self.client.force_login(self.tier1())
        for name in staff_url_names():
            with self.subTest(name=name):
                status = self.client.get(url_for(name)).status_code
                if name in SUPERUSER_ONLY:
                    self.assertEqual(status, 403)
                else:
                    # 404/405 are fine (pk=1 doesn't exist; some views are POST-only);
                    # 302: the import preview redirects when nothing is uploaded
                    self.assertIn(status, (200, 302, 404, 405))

    def test_superuser_reaches_settings(self):
        self.client.force_login(self.superuser())
        for name in SUPERUSER_ONLY:
            with self.subTest(name=name):
                self.assertIn(self.client.get(url_for(name)).status_code, (200, 404, 405))


class TierActionTests(TierTestCase):
    def test_tier2_cannot_change_menu_mode(self):
        self.client.force_login(self.tier2())
        self.assertEqual(self.client.post(reverse('staff:menu_mode'), {'action': 'force_full'}).status_code, 403)

    def test_tier1_can_change_menu_mode(self):
        self.client.force_login(self.tier1())
        response = self.client.post(reverse('staff:menu_mode'), {'action': 'force_full'})
        self.assertRedirects(response, reverse('staff:menu_mode'))

    def test_non_staff_group_member_still_denied(self):
        user = User.objects.create_user('ex-staff', password='x', is_staff=False)
        user.groups.add(Group.objects.get(name=MANAGER_GROUP))
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse('staff:inquiries')).status_code, 403)


class TierNavTests(TierTestCase):
    def nav(self, user):
        self.client.force_login(user)
        return self.client.get(reverse('staff:dashboard'))

    def test_tier2_sees_no_content_section_settings_or_change_links(self):
        response = self.nav(self.tier2())
        self.assertNotContains(response, reverse('staff:inquiries'))
        self.assertNotContains(response, reverse('staff:newsletter'))
        self.assertNotContains(response, reverse('staff:settings'))
        self.assertNotContains(response, reverse('staff:event_add'))
        self.assertNotContains(response, reverse('admin:index'))
        self.assertContains(response, reverse('staff:events'))

    def test_tier1_sees_content_section_but_not_settings(self):
        response = self.nav(self.tier1())
        self.assertContains(response, reverse('staff:inquiries'))
        self.assertContains(response, reverse('staff:event_add'))
        self.assertNotContains(response, reverse('staff:settings'))
        self.assertNotContains(response, reverse('admin:index'))

    def test_superuser_sees_settings_and_django_admin(self):
        response = self.nav(self.superuser())
        self.assertContains(response, reverse('staff:settings'))
        self.assertContains(response, reverse('admin:index'))

    def test_tier2_menu_mode_page_has_no_change_form(self):
        self.client.force_login(self.tier2())
        response = self.client.get(reverse('staff:menu_mode'))
        self.assertNotContains(response, 'name="action"')
        self.assertContains(response, 'Ask a manager')
