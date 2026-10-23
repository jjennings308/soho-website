import re

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.template.loader import get_template
from django.test import TestCase
from django.urls import URLPattern, reverse

from apps.staff import urls as staff_urls
from apps.staff.help import PAGE_TIPS, TOPICS
from apps.staff.permissions import MANAGER_GROUP

User = get_user_model()

# Portal pages that need no tip: auth, the help page itself, and POST-only actions.
NO_TIP = {'login', 'logout', 'help', 'menu_import_template', 'menu_export'}  # + CSV downloads
POST_ONLY_SUFFIXES = ('_toggle', '_delete', '_send', '_copy', '_import', '_status', '_feature')


class HelpContentTests(TestCase):
    """Keep help.py, help.html and the URL list in sync."""

    def test_every_tip_points_at_a_real_page_and_topic(self):
        url_names = {p.name for p in staff_urls.urlpatterns if isinstance(p, URLPattern)}
        topic_ids = {t[0] for t in TOPICS}
        for name, (topic, _text) in PAGE_TIPS.items():
            self.assertIn(name, url_names, f'PAGE_TIPS has unknown page {name!r}')
            self.assertIn(topic, topic_ids, f'PAGE_TIPS[{name!r}] points at unknown topic {topic!r}')

    def test_every_topic_has_a_section_in_help_template(self):
        source = get_template('staff/help.html').template.source
        sections = set(re.findall(r'<section id="([\w-]+)"', source))
        self.assertEqual(sections, {t[0] for t in TOPICS})

    def test_every_portal_page_has_a_tip(self):
        pages = [p.name for p in staff_urls.urlpatterns
                 if isinstance(p, URLPattern) and p.name not in NO_TIP
                 and not p.name.endswith(POST_ONLY_SUFFIXES)]
        missing = [name for name in pages if name not in PAGE_TIPS]
        self.assertEqual(missing, [], 'Add these pages to PAGE_TIPS in apps/staff/help.py')


class HelpPageTests(TestCase):
    def login(self, tier):
        if tier == 'super':
            user = User.objects.create_superuser('root', 'root@example.com', 'x')
        else:
            user = User.objects.create_user(tier, password='x', is_staff=True)
            if tier == 'manager':
                user.groups.add(Group.objects.get(name=MANAGER_GROUP))
        self.client.force_login(user)
        return self.client.get(reverse('staff:help'))

    def test_read_only_staff_see_only_their_topics(self):
        response = self.login('viewer')
        self.assertContains(response, 'id="menu-mode"')
        self.assertContains(response, 'Your account is view-only')
        self.assertNotContains(response, 'id="newsletter"')
        self.assertNotContains(response, 'id="settings"')
        self.assertNotContains(response, '+ Add Event')  # manager-only steps hidden

    def test_managers_see_content_topics_but_not_settings(self):
        response = self.login('manager')
        self.assertContains(response, 'id="newsletter"')
        self.assertContains(response, 'id="inquiries"')
        self.assertContains(response, '+ Add Event')
        self.assertNotContains(response, 'id="settings"')

    def test_superusers_see_everything(self):
        response = self.login('super')
        self.assertContains(response, 'id="settings"')
        self.assertContains(response, 'You are a site administrator')

    def test_help_link_in_nav_for_all_staff(self):
        self.login('viewer')
        self.assertContains(self.client.get(reverse('staff:dashboard')), f'href="{reverse("staff:help")}"')


class PageTipTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user('viewer', password='x', is_staff=True))

    def test_page_shows_its_tip_linking_to_help_topic(self):
        response = self.client.get(reverse('staff:events'))
        self.assertContains(response, 'class="sp-tip"')
        self.assertContains(response, PAGE_TIPS['events'][1])
        self.assertContains(response, f'{reverse("staff:help")}#events')

    def test_tip_is_a_banner_icon_on_desktop_and_mobile_not_a_box_in_the_page(self):
        html = self.client.get(reverse('staff:events')).content.decode()
        self.assertIn('aria-controls="page-tip-desktop"', html)
        self.assertIn('aria-controls="page-tip-mobile"', html)
        self.assertIn('aria-label="How this page works"', html)
        content_starts = html.index('class="sp-content"')
        self.assertLess(html.index('page-tip-desktop'), content_starts)
        self.assertLess(html.index('page-tip-mobile'), content_starts)
        self.assertNotIn('class="sp-tip"', html[content_starts:])

    def test_help_page_has_no_tip(self):
        self.assertNotContains(self.client.get(reverse('staff:help')), 'class="sp-tip"')


class MenuStructureHelpTests(TestCase):
    def test_every_tier_sees_how_the_menu_fits_together(self):
        self.client.force_login(User.objects.create_user('viewer', password='x', is_staff=True))
        response = self.client.get(reverse('staff:help'))
        self.assertContains(response, 'id="menus-explained"')
        self.assertContains(response, 'Setting up a new menu', count=0)  # manager-only steps
        self.assertContains(response, 'stored but not shown on the website yet')
        self.assertContains(response, 'changed by a manager')
        self.assertNotContains(response, 'href="#menu-import"')  # viewers can't open that topic

    def test_managers_are_pointed_at_the_import(self):
        user = User.objects.create_user('mgr', password='x', is_staff=True)
        user.groups.add(Group.objects.get(name=MANAGER_GROUP))
        self.client.force_login(user)
        response = self.client.get(reverse('staff:help'))
        self.assertContains(response, 'href="#menu-import"')
        self.assertNotContains(response, 'changed by a site administrator.</p>')


class HowMenusWorkHelpTests(TestCase):
    def test_managers_get_the_setup_steps(self):
        user = User.objects.create_user('mgr2', password='x', is_staff=True)
        user.groups.add(Group.objects.get(name=MANAGER_GROUP))
        self.client.force_login(user)
        response = self.client.get(reverse('staff:help'))
        self.assertContains(response, 'Setting up a new menu')
        self.assertContains(response, 'href="#menus-explained"')  # linked from Menu items


class SizesAndAddonsHelpTests(TestCase):
    def test_everyone_sees_how_sizes_and_addons_show(self):
        self.client.force_login(User.objects.create_user('viewer2', password='x', is_staff=True))
        response = self.client.get(reverse('staff:help'))
        self.assertContains(response, 'id="sizes-addons"')
        self.assertContains(response, 'Has variations')
        self.assertNotContains(response, 'set <code>has_variations</code> to <code>yes</code>')  # manager-only

    def test_managers_get_the_spreadsheet_instructions(self):
        user = User.objects.create_user('mgr3', password='x', is_staff=True)
        user.groups.add(Group.objects.get(name=MANAGER_GROUP))
        self.client.force_login(user)
        self.assertContains(self.client.get(reverse('staff:help')), 'set <code>has_variations</code> to <code>yes</code>')
