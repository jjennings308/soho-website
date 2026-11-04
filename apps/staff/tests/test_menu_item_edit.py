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


class PicturesTests(TestCase):
    def setUp(self):
        from apps.media.models import MediaCategory, MediaItem
        self.MediaItem = MediaItem
        self.item = MenuItem.objects.create(name='Classic Burger', slug='classic-burger', price=Decimal('14.50'))
        self.burgers = MediaCategory.objects.create(name='Burgers', slug='burgers')
        self.photos = [MediaItem.objects.create(name=f'Burger {n}', file=f'media/library/b{n}.jpg',
                                                category=self.burgers) for n in range(1, 4)]
        self.url = reverse('staff:menu_item_pictures', args=[self.item.pk])
        self.picker = reverse('staff:menu_item_picker', args=[self.item.pk])
        manager = User.objects.create_user('mgr', password='x', is_staff=True)
        manager.groups.add(Group.objects.get(name=MANAGER_GROUP))
        self.client.force_login(manager)

    def act(self, action, **data):
        return self.client.post(self.url, {'action': action, **data}, HTTP_X_REQUESTED_WITH='fetch')

    def add(self, *photos):
        return self.act('add', media_ids=[p.pk for p in photos])

    def order(self):
        return [(i.media_item.name, i.display_order, i.is_primary)
                for i in self.item.images.select_related('media_item').order_by('display_order')]

    def test_add_several_at_once_first_becomes_main(self):
        response = self.add(*self.photos)
        self.assertTemplateUsed(response, 'staff/menu/_item_pictures.html')
        self.assertContains(response, 'Added 3 pictures.')
        self.assertEqual(self.order(), [('Burger 1', 1, True), ('Burger 2', 2, False), ('Burger 3', 3, False)])

    def test_duplicates_videos_and_member_photos_are_ignored(self):
        self.add(self.photos[0])
        video = self.MediaItem.objects.create(name='Clip', media_type='video', video_url='https://example.com/v.mp4')
        member = self.MediaItem.objects.create(name='Guest', owner_type='member', file='media/submissions/g.jpg')
        response = self.act('add', media_ids=[self.photos[0].pk, video.pk, member.pk, 'x'])
        self.assertContains(response, 'No new pictures added.')
        self.assertEqual(self.item.images.count(), 1)

    def test_new_pictures_go_after_existing_and_main_stays(self):
        self.add(self.photos[0])
        self.add(self.photos[2], self.photos[1])
        self.assertEqual(self.order(), [('Burger 1', 1, True), ('Burger 3', 2, False), ('Burger 2', 3, False)])

    def test_make_main_and_move(self):
        self.add(*self.photos)
        pics = list(self.item.images.order_by('display_order'))
        self.act('primary', picture=pics[2].pk)
        self.act('up', picture=pics[2].pk)
        self.act('down', picture=pics[0].pk)
        self.assertEqual(self.order(), [('Burger 3', 1, True), ('Burger 1', 2, False), ('Burger 2', 3, False)])
        self.act('up', picture=self.item.images.order_by('display_order').first().pk)   # already first: no change
        self.assertEqual([o[0] for o in self.order()], ['Burger 3', 'Burger 1', 'Burger 2'])

    def test_remove_keeps_the_media_item_and_promotes_the_next(self):
        self.add(*self.photos)
        main = self.item.images.get(is_primary=True)
        self.act('remove', picture=main.pk)
        self.assertEqual(self.order(), [('Burger 2', 1, True), ('Burger 3', 2, False)])
        self.assertEqual(self.MediaItem.objects.filter(name='Burger 1').count(), 1)

    def test_picture_of_another_item_is_404_and_unknown_action_400(self):
        other = MenuItem.objects.create(name='Fries', slug='fries')
        from apps.menu.models import MenuItemImage
        foreign = MenuItemImage.objects.create(menu_item=other, media_item=self.photos[0])
        self.assertEqual(self.act('remove', picture=foreign.pk).status_code, 404)
        self.assertEqual(self.act('remove', picture='abc').status_code, 404)
        self.assertEqual(self.act('explode').status_code, 400)

    def test_plain_form_post_redirects_to_the_pictures_tab(self):
        response = self.client.post(self.url, {'action': 'add', 'media_ids': [self.photos[0].pk]})
        self.assertRedirects(response, reverse('staff:menu_item', args=[self.item.pk]) + '#pictures',
                             fetch_redirect_response=False)

    # ── Picker ───────────────────────────────────────────────────────────────

    def test_picker_lists_images_marks_added_and_filters(self):
        self.MediaItem.objects.create(name='Patio', file='media/library/patio.jpg')
        self.MediaItem.objects.create(name='Clip', media_type='video', video_url='https://example.com/v.mp4')
        self.add(self.photos[0])
        html = self.client.get(self.picker, {'category': ''}).content.decode()
        self.assertIn('Patio', html)
        self.assertNotIn('Clip', html)
        self.assertRegex(html, rf'data-id="{self.photos[0].pk}" disabled')
        self.assertIn('Added', html)
        html = self.client.get(self.picker, {'category': 'burgers', 'q': 'burger 2'}).content.decode()
        self.assertIn('Burger 2', html)
        self.assertNotIn('Burger 3', html)
        self.assertNotIn('Patio', html)

    def test_picker_defaults_to_the_category_matching_the_items_placement(self):
        self.MediaItem.objects.create(name='Patio', file='media/library/patio.jpg')
        MenuItemCategoryAssignment.objects.create(
            menu_item=self.item, category=MenuCategory.objects.create(name='Burgers', slug='burgers-menu'))
        self.assertNotContains(self.client.get(self.picker), 'Patio')
        page = self.client.get(reverse('staff:menu_item', args=[self.item.pk]))
        self.assertEqual(page.context['picker_category'], 'burgers')

    def test_picker_pages(self):
        from apps.staff.views import PICKER_PAGE_SIZE
        for n in range(PICKER_PAGE_SIZE):
            self.MediaItem.objects.create(name=f'Z {n:02}', file=f'media/library/z{n}.jpg')
        first = self.client.get(self.picker, {'category': ''}).content.decode()
        self.assertEqual(first.count('class="pk-card'), PICKER_PAGE_SIZE)
        self.assertIn('data-next="2"', first)
        second = self.client.get(self.picker, {'category': '', 'page': 2}).content.decode()
        self.assertEqual(second.count('class="pk-card'), 3)
        self.assertNotIn('data-next', second)

    # ── Access and old URL ───────────────────────────────────────────────────

    def test_read_only_staff_cannot_use_pictures_or_picker(self):
        self.client.force_login(User.objects.create_user('viewer', password='x', is_staff=True))
        self.assertEqual(self.add(self.photos[0]).status_code, 403)
        self.assertEqual(self.client.get(self.picker).status_code, 403)
        page = self.client.get(reverse('staff:menu_item', args=[self.item.pk]))
        self.assertNotContains(page, '+ Add pictures')
        self.assertNotContains(page, 'Make main')

    def test_old_images_url_redirects_to_the_pictures_tab(self):
        response = self.client.get(reverse('staff:menu_item_images', args=[self.item.pk]))
        self.assertRedirects(response, reverse('staff:menu_item', args=[self.item.pk]) + '#pictures',
                             fetch_redirect_response=False)


class MenuItemAddTests(TestCase):
    def setUp(self):
        self.url = reverse('staff:menu_item_add')
        manager = User.objects.create_user('mgr', password='x', is_staff=True)
        manager.groups.add(Group.objects.get(name=MANAGER_GROUP))
        self.manager = manager
        self.client.force_login(manager)

    def data(self, **changes):
        return details(MenuItem(name='Fish Tacos', price=Decimal('13.00'), is_available=True), **changes)

    def test_button_shows_for_managers_only(self):
        list_url = reverse('staff:menu_item_list')
        self.assertContains(self.client.get(list_url), '+ Add Item')
        self.client.force_login(User.objects.create_user('viewer', password='x', is_staff=True))
        self.assertNotContains(self.client.get(list_url), '+ Add Item')
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.post(self.url, self.data()).status_code, 403)
        self.assertFalse(MenuItem.objects.exists())

    def test_add_creates_the_item_and_opens_its_page(self):
        response = self.client.post(self.url, self.data(), follow=True)
        item = MenuItem.objects.get()
        self.assertEqual((item.name, item.slug, item.price), ('Fish Tacos', 'fish-tacos', Decimal('13.00')))
        self.assertTrue(item.is_available)
        self.assertRedirects(response, reverse('staff:menu_item', args=[item.pk]))
        self.assertContains(response, 'Added &quot;Fish Tacos&quot;')
        self.assertContains(response, "isn't in any category yet")

    def test_same_name_gets_its_own_slug(self):
        self.client.post(self.url, self.data())
        self.client.post(self.url, self.data())
        self.assertEqual(sorted(MenuItem.objects.values_list('slug', flat=True)), ['fish-tacos', 'fish-tacos-2'])

    def test_name_with_no_letters_still_gets_a_slug(self):
        self.client.post(self.url, self.data(name='!!!'))
        self.assertEqual(MenuItem.objects.get().slug, 'item')

    def test_invalid_form_keeps_typed_values_and_saves_nothing(self):
        response = self.client.post(self.url, self.data(name='', short_description='Typed text'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This field is required')
        self.assertContains(response, 'Typed text')
        self.assertFalse(MenuItem.objects.exists())

    def test_next_returns_to_the_filtered_list(self):
        list_url = reverse('staff:menu_item_list') + '?q=taco'
        self.assertContains(self.client.get(self.url, {'next': list_url}), f'href="{list_url}"')
        response = self.client.post(self.url, self.data(next=list_url))
        self.assertContains(self.client.get(response.url), f'href="{list_url}"')

    def test_offsite_next_is_ignored(self):
        self.assertNotContains(self.client.get(self.url, {'next': 'https://evil.example/'}), 'evil.example')
