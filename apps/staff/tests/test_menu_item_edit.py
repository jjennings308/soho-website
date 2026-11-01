from decimal import Decimal
from urllib.parse import quote

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from apps.menu.models import (
    Menu, MenuCategory, MenuCategoryAssignment, MenuItem, MenuItemCategoryAssignment,
)
from apps.staff.permissions import MANAGER_GROUP

User = get_user_model()


def details(item, **changes):
    """POST data for the Details form: the item's current values plus changes."""
    data = {
        'name': item.name, 'short_description': item.short_description,
        'description': item.description, 'price_display': item.price_display,
        'price': item.price or '', 'sale_price': item.sale_price or '',
        'dietary_type': item.dietary_type, 'allergen_info': item.allergen_info,
        'spice_level': item.spice_level, 'calories': item.calories or '',
        'available_from': '', 'available_until': '',
    }
    for flag in ('is_gluten_free', 'is_vegan', 'is_dairy_free', 'is_nut_free', 'contains_shellfish',
                 'is_featured', 'is_chef_special', 'is_new', 'is_seasonal', 'is_available'):
        if getattr(item, flag):
            data[flag] = 'on'
    for key, value in changes.items():
        if value is None:
            data.pop(key, None)
        else:
            data[key] = value
    return data


class MenuItemPageTests(TestCase):
    def setUp(self):
        self.item = MenuItem.objects.create(
            name='Classic Burger', slug='classic-burger', price=Decimal('14.50'),
            short_description='Half-pound patty', description='<p>Our <strong>signature</strong> burger.</p>',
            allergen_info='Contains sesame.',
        )
        self.url = reverse('staff:menu_item', args=[self.item.pk])
        self.manager = User.objects.create_user('mgr', password='x', is_staff=True)
        self.manager.groups.add(Group.objects.get(name=MANAGER_GROUP))
        self.viewer = User.objects.create_user('viewer', password='x', is_staff=True)

    # ── Access ───────────────────────────────────────────────────────────────

    def test_read_only_staff_see_the_item_without_edit_controls(self):
        self.client.force_login(self.viewer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Contains sesame.')
        self.assertContains(response, '<strong>signature</strong>', html=False)
        self.assertNotContains(response, '>Save</button>')
        self.assertContains(response, 'disabled')
        self.assertNotContains(response, reverse('staff:menu_item_images', args=[self.item.pk]))

    def test_read_only_staff_cannot_save(self):
        self.client.force_login(self.viewer)
        response = self.client.post(self.url, details(self.item, name='Hacked'))
        self.assertEqual(response.status_code, 403)
        self.item.refresh_from_db()
        self.assertEqual(self.item.name, 'Classic Burger')

    def test_list_links_to_item_page_with_edit_or_view(self):
        list_url = reverse('staff:menu_item_list') + '?q=burger'
        self.client.force_login(self.viewer)
        response = self.client.get(list_url)
        self.assertContains(response, f'{self.url}?next={quote(list_url, safe="/")}')
        self.assertContains(response, 'View')
        self.client.force_login(self.manager)
        self.assertContains(self.client.get(list_url), 'Edit')

    # ── Saving ───────────────────────────────────────────────────────────────

    def test_manager_saves_details_and_stays_on_the_page(self):
        self.client.force_login(self.manager)
        response = self.client.post(self.url, details(
            self.item, name='Classic Cheeseburger', price='15.00', is_gluten_free='on', is_available=None,
            available_from='11:00'))
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.item.refresh_from_db()
        self.assertEqual(self.item.name, 'Classic Cheeseburger')
        self.assertEqual(self.item.slug, 'classic-burger')          # slug never changes on rename
        self.assertEqual(self.item.price, Decimal('15.00'))
        self.assertTrue(self.item.is_gluten_free)
        self.assertFalse(self.item.is_available)
        self.assertEqual(self.item.available_from.strftime('%H:%M'), '11:00')
        self.assertContains(self.client.get(response.url), 'Saved.')

    def test_validation_error_keeps_typed_values_and_saves_nothing(self):
        self.client.force_login(self.manager)
        response = self.client.post(self.url, details(self.item, name='', short_description='Typed text'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This field is required')
        self.assertContains(response, 'Typed text')
        self.item.refresh_from_db()
        self.assertEqual(self.item.short_description, 'Half-pound patty')

    def test_next_round_trip_returns_to_the_filtered_list(self):
        self.client.force_login(self.manager)
        list_url = reverse('staff:menu_item_list') + '?q=burger&avail=available'
        response = self.client.get(self.url, {'next': list_url})
        self.assertContains(response, f'href="{list_url.replace("&", "&amp;")}"')
        response = self.client.post(self.url, details(self.item, next=list_url))
        self.assertEqual(response.url, f'{self.url}?next={quote(list_url, safe="")}')
        self.assertContains(self.client.get(response.url), f'value="{list_url.replace("&", "&amp;")}"')

    def test_offsite_next_is_ignored(self):
        self.client.force_login(self.manager)
        response = self.client.get(self.url, {'next': 'https://evil.example/'})
        self.assertNotContains(response, 'evil.example')

    # ── Appears on ───────────────────────────────────────────────────────────

    def test_appears_on_lists_menu_category_and_special_price(self):
        burgers = MenuCategory.objects.create(name='Burgers', slug='burgers')
        happy = MenuCategory.objects.create(name='Happy Hour Food', slug='happy-hour-food')
        food = Menu.objects.create(title='Food Menu', slug='food-menu', menu_type='food')
        MenuCategoryAssignment.objects.create(menu=food, category=burgers)
        MenuItemCategoryAssignment.objects.create(menu_item=self.item, category=burgers)
        MenuItemCategoryAssignment.objects.create(menu_item=self.item, category=happy,
                                                  override_price=Decimal('9.00'))
        self.client.force_login(self.viewer)
        response = self.client.get(self.url)
        content = ' '.join(response.content.decode().split())
        self.assertIn('Food Menu &rsaquo; Burgers', content)
        self.assertIn('Not on any menu</em> &rsaquo; Happy Hour Food — $9.00', content)

    def test_item_with_no_placements_says_so(self):
        self.client.force_login(self.viewer)
        self.assertContains(self.client.get(self.url), "isn't in any category yet")
