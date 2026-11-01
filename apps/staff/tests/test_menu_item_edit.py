from decimal import Decimal
from urllib.parse import quote

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from apps.menu import importers as im
from apps.menu.models import (
    Menu, MenuCategory, MenuCategoryAssignment, MenuItem, MenuItemAddon, MenuItemCategoryAssignment,
    MenuItemVariation,
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
    for prefix in ('variations', 'addons'):
        data.update({f'{prefix}-TOTAL_FORMS': '0', f'{prefix}-INITIAL_FORMS': '0',
                     f'{prefix}-MIN_NUM_FORMS': '0', f'{prefix}-MAX_NUM_FORMS': '1000'})
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


def rows(prefix, rows, initial=0):
    """Formset POST data: rows is a list of dicts (include 'id' for saved rows)."""
    data = {f'{prefix}-TOTAL_FORMS': str(len(rows)), f'{prefix}-INITIAL_FORMS': str(initial)}
    for i, row in enumerate(rows):
        for key, value in row.items():
            data[f'{prefix}-{i}-{key}'] = value
    return data


class SizesAndAddonsTests(TestCase):
    def setUp(self):
        self.item = MenuItem.objects.create(name='IPA', slug='ipa', price=Decimal('6.00'))
        self.url = reverse('staff:menu_item', args=[self.item.pk])
        manager = User.objects.create_user('mgr', password='x', is_staff=True)
        manager.groups.add(Group.objects.get(name=MANAGER_GROUP))
        self.client.force_login(manager)

    def post(self, **extra):
        return self.client.post(self.url, {**details(self.item), **extra})

    def test_add_a_size_and_an_addon_in_one_save(self):
        response = self.post(**rows('variations', [
            {'name': 'Pint', 'size': '16 oz', 'price': '6.00', 'order': '1', 'is_available': 'on'},
            {'name': 'Pitcher', 'price': '18.00', 'order': '2', 'is_available': 'on'},
        ]), **rows('addons', [{'name': 'Lime', 'price': '0.50', 'order': '0', 'is_available': 'on'}]))
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.assertEqual(list(self.item.variations.values_list('name', flat=True)), ['Pint', 'Pitcher'])
        self.assertEqual(self.item.addons.get().price, Decimal('0.50'))
        self.item.refresh_from_db()
        self.assertTrue(self.item.has_variations and self.item.has_addons)
        self.assertEqual(self.item.display_price, '6 – 18')  # listing now shows the range

    def test_blank_new_rows_are_ignored(self):
        self.post(**rows('variations', [{'name': '', 'price': '', 'order': '0'}]))
        self.assertFalse(self.item.variations.exists())
        self.item.refresh_from_db()
        self.assertFalse(self.item.has_variations)

    def test_edit_and_remove_saved_rows_and_flags_follow(self):
        pint = MenuItemVariation.objects.create(menu_item=self.item, name='Pint', price=Decimal('6'))
        lime = MenuItemAddon.objects.create(menu_item=self.item, name='Lime', price=Decimal('0.5'))
        self.item.sync_option_flags()
        self.post(**rows('variations', [{'id': pint.pk, 'name': 'Pint', 'price': '7.00', 'order': '0'}], initial=1),
                  **rows('addons', [{'id': lime.pk, 'name': 'Lime', 'price': '0.50', 'order': '0',
                                     'DELETE': 'on'}], initial=1))
        pint.refresh_from_db()
        self.assertEqual(pint.price, Decimal('7.00'))
        self.assertFalse(MenuItemAddon.objects.exists())
        self.item.refresh_from_db()
        self.assertTrue(self.item.has_variations)
        self.assertFalse(self.item.has_addons)

    def test_any_invalid_part_saves_nothing_and_opens_sizes_tab(self):
        response = self.client.post(self.url, {
            **details(self.item, name='Hazy IPA'),
            **rows('variations', [{'name': 'Pint', 'price': '', 'order': '0'}])})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['initial_tab'], 'sizes')
        self.assertContains(response, 'This field is required')
        self.item.refresh_from_db()
        self.assertEqual(self.item.name, 'IPA')
        self.assertFalse(self.item.variations.exists())

    def test_duplicate_size_names_are_refused(self):
        response = self.post(**rows('variations', [
            {'name': 'Pint', 'price': '6.00', 'order': '0'}, {'name': 'Pint', 'price': '7.00', 'order': '1'}]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.item.variations.exists())

    def test_page_offers_add_buttons_and_an_empty_row_template(self):
        response = self.client.get(self.url)
        self.assertContains(response, '+ Add a size')
        self.assertContains(response, '+ Add an add-on')
        self.assertContains(response, 'name="variations-__prefix__-price"')

    def test_read_only_staff_see_sizes_as_a_table(self):
        MenuItemVariation.objects.create(menu_item=self.item, name='Pitcher', size='60 oz', price=Decimal('18'))
        self.client.force_login(User.objects.create_user('viewer', password='x', is_staff=True))
        response = self.client.get(self.url)
        self.assertContains(response, 'Pitcher')
        self.assertContains(response, '60 oz')
        self.assertNotContains(response, '+ Add a size')
        self.assertNotContains(response, 'variations-TOTAL_FORMS')


class OptionFlagSyncTests(TestCase):
    def test_csv_variation_and_addon_imports_set_the_flags(self):
        item = MenuItem.objects.create(name='IPA', slug='ipa', price=Decimal('6.00'))
        im.apply('variations', 'item,name,price\nipa,Pint,6.00\n')
        im.apply('addons', 'item,name,price\nipa,Lime,0.50\n')
        item.refresh_from_db()
        self.assertTrue(item.has_variations and item.has_addons)
