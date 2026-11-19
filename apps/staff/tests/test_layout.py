"""Portal page layout shared by every page (staff/base.html)."""
import re

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from apps.staff.permissions import MANAGER_GROUP

User = get_user_model()


class HeaderActionsTests(TestCase):
    """Header buttons sit in .sp-topbar__actions, which input.css keeps visible on phones."""

    def setUp(self):
        user = User.objects.create_user('mgr', password='x', is_staff=True)
        user.groups.add(Group.objects.get(name=MANAGER_GROUP))
        self.client.force_login(user)

    def actions(self, url):
        html = self.client.get(url).content.decode()
        match = re.search(r'<div class="sp-topbar__actions">(.*?)</div>\s*</div>', html, re.S)
        self.assertIsNotNone(match, 'page has no header actions block')
        return match.group(1)

    def test_media_upload_and_import_reachable(self):
        actions = self.actions(reverse('staff:media_library'))
        self.assertIn(reverse('staff:media_upload'), actions)
        self.assertIn(reverse('staff:media_import'), actions)

    def test_other_header_buttons_use_the_same_block(self):
        self.assertIn(reverse('staff:menu_item_add'), self.actions(reverse('staff:menu_item_list')))
        self.assertIn(reverse('staff:event_add'), self.actions(reverse('staff:events')))

    def test_phone_css_keeps_actions_and_hides_title(self):
        with open('static/src/input.css') as f:
            css = f.read()
        phone = css[css.index('@media (max-width: 768px)'):]
        phone = phone[:phone.index('\n}')]
        self.assertIn('.sp-topbar__title { display: none; }', phone)
        self.assertNotIn('.sp-topbar { display: none; }', phone)
