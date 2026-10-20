from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from apps.core.models import EventInquiry
from apps.media.models import MediaItem
from apps.staff.permissions import MANAGER_GROUP


class SafeRedirectTests(TestCase):
    def setUp(self):
        staff = get_user_model().objects.create_user('staff', password='x', is_staff=True)
        staff.groups.add(Group.objects.get(name=MANAGER_GROUP))
        self.client.force_login(staff)
        self.item = MediaItem.objects.create(name='Burger', owner_type='staff')
        self.library = reverse('staff:media_library')

    def test_toggle_follows_local_next(self):
        response = self.client.post(reverse('staff:media_toggle', args=[self.item.pk]),
                                    {'next': '/staff/media/?page=2'})
        self.assertRedirects(response, '/staff/media/?page=2', fetch_redirect_response=False)

    def test_toggle_ignores_offsite_next_and_referer(self):
        response = self.client.post(reverse('staff:media_toggle', args=[self.item.pk]),
                                    {'next': 'https://evil.example/'},
                                    HTTP_REFERER='https://evil.example/')
        self.assertRedirects(response, self.library, fetch_redirect_response=False)

    def test_delete_ignores_offsite_next(self):
        response = self.client.post(reverse('staff:media_delete', args=[self.item.pk]),
                                    {'next': '//evil.example/'})
        self.assertRedirects(response, self.library, fetch_redirect_response=False)

    def test_edit_cancel_link_rejects_javascript_url(self):
        response = self.client.get(reverse('staff:media_edit', args=[self.item.pk]),
                                   {'next': 'javascript:alert(1)'})
        self.assertEqual(response.context['back_url'], self.library)
        self.assertNotContains(response, 'javascript:alert')

    def test_edit_post_ignores_offsite_next(self):
        response = self.client.post(reverse('staff:media_edit', args=[self.item.pk]),
                                    {'name': 'Burger', 'display_order': 0, 'next': 'https://evil.example/'})
        self.assertRedirects(response, self.library, fetch_redirect_response=False)

    def test_inquiry_status_ignores_offsite_referer(self):
        inquiry = EventInquiry.objects.create(name='Pat', email='pat@example.com', phone='1')
        response = self.client.post(reverse('staff:inquiry_status', args=[inquiry.pk]),
                                    {'status': 'contacted'}, HTTP_REFERER='https://evil.example/')
        self.assertRedirects(response, reverse('staff:inquiries'), fetch_redirect_response=False)
