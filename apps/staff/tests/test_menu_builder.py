from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from apps.core.models import ColorScheme
from apps.menu.models import Menu, MenuCategory, MenuCategoryAssignment
from apps.staff.permissions import MANAGER_GROUP

User = get_user_model()


def settings(menu=None, **changes):
    """POST data for the Settings form: a menu's current values plus changes."""
    data = {'title': 'Brunch', 'menu_type': 'food', 'role': 'none', 'is_active': 'on', 'homepage_slot': 'none'}
    if menu:
        data = {'title': menu.title, 'menu_type': menu.menu_type, 'role': menu.role, 'homepage_slot': menu.homepage_slot}
        if menu.is_active:
            data['is_active'] = 'on'
    for key, value in changes.items():
        if value is None:
            data.pop(key, None)
        else:
            data[key] = value
    return data


class MenuBuilderTestCase(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user('mgr', password='x', is_staff=True)
        self.manager.groups.add(Group.objects.get(name=MANAGER_GROUP))
        self.client.force_login(self.manager)
        self.list_url = reverse('staff:menus')
        self.add_url = reverse('staff:menu_add')

    def url(self, menu):
        return reverse('staff:menu_detail', args=[menu.pk])


class AccessTests(MenuBuilderTestCase):
    def test_read_only_staff_can_view_and_not_change(self):
        menu = Menu.objects.create(title='Food', slug='food', menu_type='food')
        self.client.force_login(User.objects.create_user('viewer', password='x', is_staff=True))
        response = self.client.get(self.list_url)
        self.assertContains(response, 'Food')
        self.assertNotContains(response, self.add_url)
        page = self.client.get(self.url(menu))
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, '>Save</button>')
        self.assertContains(page, 'disabled')
        self.assertEqual(self.client.post(self.url(menu), settings(menu, title='Hacked')).status_code, 403)
        self.assertEqual(self.client.get(self.add_url).status_code, 403)
        self.assertEqual(self.client.post(self.add_url, settings()).status_code, 403)
        menu.refresh_from_db()
        self.assertEqual(menu.title, 'Food')
        self.assertEqual(Menu.objects.count(), 1)

    def test_nav_link_shows_for_all_staff(self):
        self.assertContains(self.client.get(reverse('staff:dashboard')), self.list_url)


class AddTests(MenuBuilderTestCase):
    def test_add_creates_the_menu_and_opens_it(self):
        response = self.client.post(self.add_url, settings(display_name='Sunday Brunch', description='Eggs'))
        menu = Menu.objects.get()
        self.assertRedirects(response, self.url(menu), fetch_redirect_response=False)
        self.assertEqual((menu.title, menu.slug, menu.menu_type, menu.display_name, menu.is_active),
                         ('Brunch', 'brunch', 'food', 'Sunday Brunch', True))
        self.assertContains(self.client.get(response.url), 'No categories yet')

    def test_same_title_gets_its_own_slug(self):
        self.client.post(self.add_url, settings())
        self.client.post(self.add_url, settings())
        self.assertEqual(sorted(Menu.objects.values_list('slug', flat=True)), ['brunch', 'brunch-2'])

    def test_type_must_be_chosen(self):
        self.assertContains(self.client.get(self.add_url), 'Choose a type')
        response = self.client.post(self.add_url, settings(menu_type=''))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This field is required')
        self.assertFalse(Menu.objects.exists())

    def test_invalid_form_keeps_typed_values(self):
        response = self.client.post(self.add_url, settings(title='', description='Typed text'))
        self.assertContains(response, 'Typed text')
        self.assertFalse(Menu.objects.exists())


class EditTests(MenuBuilderTestCase):
    def test_save_keeps_slug_and_sets_days(self):
        menu = Menu.objects.create(title='Food', slug='food', menu_type='food')
        response = self.client.post(self.url(menu), settings(menu, title='Dinner', days_of_week=['0', '4']))
        self.assertRedirects(response, self.url(menu), fetch_redirect_response=False)
        menu.refresh_from_db()
        self.assertEqual((menu.title, menu.slug, menu.days_of_week), ('Dinner', 'food', [0, 4]))
        self.assertContains(self.client.get(self.url(menu)), 'not applied on the website yet')

    def test_saved_days_stay_ticked(self):
        menu = Menu.objects.create(title='HH', slug='hh', menu_type='promo', days_of_week=[1])
        html = ' '.join(self.client.get(self.url(menu)).content.decode().split())
        self.assertRegex(html, r'value="1"[^>]*checked')

    def test_fields_for_other_types_are_cleared(self):
        scheme = ColorScheme.objects.create(name='Gold')
        response = self.client.post(self.add_url, settings(
            color_scheme=scheme.pk, homepage_slot='slot_1', valid_from='2027-01-01', valid_until='2027-01-07'))
        menu = Menu.objects.get()
        self.assertRedirects(response, self.url(menu), fetch_redirect_response=False)
        self.assertEqual((menu.color_scheme, menu.homepage_slot, menu.valid_from, menu.valid_until),
                         (None, 'none', None, None))

    def test_promo_keeps_colors_and_specials_keep_dates(self):
        scheme = ColorScheme.objects.create(name='Gold')
        self.client.post(self.add_url, settings(title='P', menu_type='promo', color_scheme=scheme.pk))
        self.assertEqual(Menu.objects.get(title='P').color_scheme, scheme)
        self.client.post(self.add_url, settings(title='S', menu_type='weekly_specials',
                                                valid_from='2027-01-01', valid_until='2027-01-07'))
        self.assertEqual(Menu.objects.get(title='S').valid_from, date(2027, 1, 1))

    def test_legacy_type_is_kept_and_not_offered(self):
        legacy = Menu.objects.create(title='SoHo', slug='soho-menu', menu_type='combined')
        page = self.client.get(self.url(legacy))
        self.assertContains(page, 'older type')
        self.assertNotContains(self.client.get(self.add_url), 'value="combined"')
        self.client.post(self.url(legacy), settings(legacy, title='SoHo Menu', menu_type=None))
        legacy.refresh_from_db()
        self.assertEqual((legacy.title, legacy.menu_type), ('SoHo Menu', 'combined'))

    def test_page_lists_categories_with_item_counts(self):
        menu = Menu.objects.create(title='Food', slug='food', menu_type='food')
        category = MenuCategory.objects.create(name='Burgers', slug='burgers')
        MenuCategoryAssignment.objects.create(menu=menu, category=category)
        self.assertContains(self.client.get(self.url(menu)), 'Burgers')


class LiveSiteGuardTests(MenuBuilderTestCase):
    def setUp(self):
        super().setUp()
        self.live = Menu.objects.create(title='Food Menu', slug='food-menu', menu_type='food', role='default_food')
        self.new = Menu.objects.create(title='Winter', slug='winter', menu_type='food')

    def test_taking_a_role_needs_confirming(self):
        response = self.client.post(self.url(self.new), settings(self.new, role='default_food'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '&quot;Food Menu&quot; is the Default Food Menu now')
        self.assertContains(response, 'Yes, change the live site')
        self.live.refresh_from_db()
        self.assertEqual(self.live.role, 'default_food')

        self.client.post(self.url(self.new), settings(self.new, role='default_food', confirm_live='on'))
        self.live.refresh_from_db()
        self.new.refresh_from_db()
        self.assertEqual((self.live.role, self.new.role), ('none', 'default_food'))

    def test_leaving_a_role_empty_needs_confirming(self):
        response = self.client.post(self.url(self.live), settings(self.live, role='none'))
        self.assertContains(response, 'coming soon')
        self.live.refresh_from_db()
        self.assertEqual(self.live.role, 'default_food')

    def test_a_free_role_and_unchanged_role_save_without_asking(self):
        self.assertEqual(self.client.post(self.url(self.new), settings(self.new, role='event_food')).status_code, 302)
        self.assertEqual(self.client.post(self.url(self.live), settings(self.live, title='Food')).status_code, 302)

    def test_taking_a_homepage_slot_needs_confirming_and_empties_the_old_one(self):
        old = Menu.objects.create(title='Old', slug='old', menu_type='promo', homepage_slot='slot_1')
        promo = Menu.objects.create(title='New', slug='new', menu_type='promo')
        response = self.client.post(self.url(promo), settings(promo, homepage_slot='slot_1'))
        self.assertContains(response, 'in that homepage slot now')
        self.client.post(self.url(promo), settings(promo, homepage_slot='slot_1', confirm_live='on'))
        old.refresh_from_db()
        promo.refresh_from_db()
        self.assertEqual((old.homepage_slot, promo.homepage_slot), ('none', 'slot_1'))

    def test_adding_a_menu_into_a_slot_also_empties_the_old_one(self):
        old = Menu.objects.create(title='Old', slug='old', menu_type='promo', homepage_slot='slot_2')
        self.client.post(self.add_url, settings(menu_type='promo', homepage_slot='slot_2', confirm_live='on'))
        old.refresh_from_db()
        self.assertEqual(old.homepage_slot, 'none')
        self.assertEqual(Menu.objects.get(slug='brunch').homepage_slot, 'slot_2')
