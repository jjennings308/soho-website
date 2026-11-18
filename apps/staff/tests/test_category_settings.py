"""Phase 5 of docs/PLAN-menu-option-groups.md: category settings in the staff portal."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from apps.media.models import MediaItem
from apps.menu.models import Menu, MenuCategory, MenuCategoryAssignment, MenuItem, MenuItemCategoryAssignment
from apps.staff.permissions import MANAGER_GROUP

User = get_user_model()


def form_data(category, **changes):
    """POST data for the settings form: the category's current values plus changes (None/False drops a field)."""
    data = {
        'name': category.name, 'display_name': category.display_name, 'category_type': category.category_type,
        'subtitle': category.subtitle, 'description': category.description,
        'background_image': category.background_image_id or '', 'order': category.order,
    }
    if category.is_active:
        data['is_active'] = 'on'
    if category.show_disclaimer:
        data['show_disclaimer'] = 'on'
    for key, value in changes.items():
        if value is None or value is False:
            data.pop(key, None)
        else:
            data[key] = value
    return data


class CategorySettingsTestCase(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user('mgr', password='x', is_staff=True)
        self.manager.groups.add(Group.objects.get(name=MANAGER_GROUP))
        self.client.force_login(self.manager)
        self.burgers = MenuCategory.objects.create(name='Burgers', slug='burgers', display_name='Burgers',
                                                   description='Half-pound burgers')
        self.food = Menu.objects.create(title='Food Menu', slug='food', menu_type='food')
        self.event = Menu.objects.create(title='Event Food', slug='event-food', menu_type='food')
        for menu in (self.food, self.event):
            MenuCategoryAssignment.objects.create(menu=menu, category=self.burgers)
        item = MenuItem.objects.create(name='Cheeseburger', slug='cheeseburger')
        MenuItemCategoryAssignment.objects.create(menu_item=item, category=self.burgers)
        self.url = reverse('staff:category', args=[self.burgers.pk])


class CategoryListTests(CategorySettingsTestCase):
    def test_lists_every_category_with_menus(self):
        MenuCategory.objects.create(name='Old Specials', slug='old-specials', is_active=False)
        html = self.client.get(reverse('staff:categories')).content.decode()
        self.assertIn('Burgers', html)
        self.assertIn('Event Food, Food Menu', html)
        self.assertIn('Old Specials', html)              # inactive and on no menu: still reachable
        self.assertIn('Not on any menu', html)

    def test_sidebar_link_for_all_staff(self):
        self.client.force_login(User.objects.create_user('viewer', password='x', is_staff=True))
        self.assertContains(self.client.get(reverse('staff:dashboard')), reverse('staff:categories'))

    def test_menu_categories_tab_links_to_settings(self):
        html = self.client.get(reverse('staff:menu_detail', args=[self.food.pk])).content.decode()
        self.assertIn(f'{self.url}?next=', html)


class CategoryEditTests(CategorySettingsTestCase):
    def test_page_names_every_menu(self):
        html = self.client.get(self.url).content.decode()
        self.assertIn('Event Food', html)
        self.assertIn('changes here show on all of them', html)
        self.assertIn('<code>burgers</code>', html)

    def test_save_all_settings(self):
        photo = MediaItem.objects.create(name='Grill', file='media/library/grill.jpg')
        response = self.client.post(self.url, form_data(
            self.burgers, name='Burgers & Melts', display_name='Burgers', subtitle='Includes your choice of side',
            description='Half-pound burgers', background_image=photo.pk, show_disclaimer='on', order=4))
        self.assertRedirects(response, self.url)
        self.burgers.refresh_from_db()
        self.assertEqual(self.burgers.name, 'Burgers & Melts')
        self.assertEqual(self.burgers.subtitle, 'Includes your choice of side')
        self.assertEqual(self.burgers.background_image, photo)
        self.assertTrue(self.burgers.show_disclaimer)
        self.assertEqual(self.burgers.order, 4)
        self.assertEqual(self.burgers.slug, 'burgers')                # never changes

    def test_background_choices_are_staff_images_only(self):
        MediaItem.objects.create(name='Grill', file='media/library/grill.jpg')
        guest = MediaItem.objects.create(name='Guest Pic', owner_type='member', file='media/submissions/g.jpg')
        clip = MediaItem.objects.create(name='Clip', media_type='video', video_url='https://example.com/v.mp4')
        html = self.client.get(self.url).content.decode()
        self.assertIn('Grill', html)
        self.assertNotIn('Guest Pic', html)
        self.assertNotIn('>Clip<', html)
        response = self.client.post(self.url, form_data(self.burgers, background_image=guest.pk))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(self.url, form_data(self.burgers, background_image=clip.pk))
        self.assertEqual(response.status_code, 200)
        self.burgers.refresh_from_db()
        self.assertIsNone(self.burgers.background_image)

    def test_duplicate_name_refused(self):
        MenuCategory.objects.create(name='Sides', slug='sides')
        response = self.client.post(self.url, form_data(self.burgers, name='sides'))
        self.assertContains(response, 'Another category already has this name.')
        self.burgers.refresh_from_db()
        self.assertEqual(self.burgers.name, 'Burgers')

    def test_switching_off_needs_confirm(self):
        response = self.client.post(self.url, form_data(self.burgers, is_active=False))
        self.assertContains(response, 'hides this category on Event Food, Food Menu')
        self.burgers.refresh_from_db()
        self.assertTrue(self.burgers.is_active)
        response = self.client.post(self.url, form_data(self.burgers, is_active=False, confirm_hide='on'))
        self.assertRedirects(response, self.url)
        self.burgers.refresh_from_db()
        self.assertFalse(self.burgers.is_active)

    def test_switching_back_on_needs_no_confirm(self):
        MenuCategory.objects.filter(pk=self.burgers.pk).update(is_active=False)
        self.burgers.refresh_from_db()
        self.assertRedirects(self.client.post(self.url, form_data(self.burgers, is_active='on')), self.url)
        self.burgers.refresh_from_db()
        self.assertTrue(self.burgers.is_active)

    def test_next_round_trip_back_to_the_menu(self):
        back = reverse('staff:menu_detail', args=[self.food.pk]) + '#categories'
        response = self.client.post(self.url, form_data(self.burgers, next=back))
        self.assertRedirects(response, self.url + '?next=%2Fstaff%2Fmenu%2Fmenus%2F' + str(self.food.pk)
                             + '%2F%23categories', fetch_redirect_response=False)
        self.assertContains(self.client.get(response.url), f'href="{back}"')

    def test_offsite_next_ignored(self):
        html = self.client.get(self.url + '?next=https://evil.example.com/').content.decode()
        self.assertNotIn('evil.example.com', html)


class CategoryAccessTests(CategorySettingsTestCase):
    def test_read_only_staff_view_but_cannot_save(self):
        self.client.force_login(User.objects.create_user('viewer', password='x', is_staff=True))
        page = self.client.get(self.url)
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, '>Save</button>')
        self.assertContains(page, 'disabled')
        self.assertEqual(self.client.post(self.url, form_data(self.burgers, name='Hacked')).status_code, 403)
        self.burgers.refresh_from_db()
        self.assertEqual(self.burgers.name, 'Burgers')
