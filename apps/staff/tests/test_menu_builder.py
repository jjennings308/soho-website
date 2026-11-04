from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.core.models import ColorScheme
from apps.menu.models import (
    Menu, MenuCategory, MenuCategoryAssignment, MenuItem, MenuItemCategoryAssignment, MenuSubCategory,
)
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
        self.assertRedirects(response, self.url(menu) + '#categories', fetch_redirect_response=False)
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
        self.assertContains(self.client.get(self.url(menu)), 'None ticked means every day')

    def test_saved_days_stay_ticked(self):
        menu = Menu.objects.create(title='HH', slug='hh', menu_type='promo', days_of_week=[1])
        html = ' '.join(self.client.get(self.url(menu)).content.decode().split())
        self.assertRegex(html, r'value="1"[^>]*checked')

    def test_fields_for_other_types_are_cleared(self):
        scheme = ColorScheme.objects.create(name='Gold')
        response = self.client.post(self.add_url, settings(
            color_scheme=scheme.pk, homepage_slot='slot_1', valid_from='2027-01-01', valid_until='2027-01-07'))
        menu = Menu.objects.get()
        self.assertRedirects(response, self.url(menu) + '#categories', fetch_redirect_response=False)
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


class MenuCategoriesTests(MenuBuilderTestCase):
    def setUp(self):
        super().setUp()
        self.menu = Menu.objects.create(title='Brunch', slug='brunch', menu_type='food')
        self.burgers = MenuCategory.objects.create(name='Burgers', slug='burgers', category_type='food')
        self.beer = MenuCategory.objects.create(name='Beer', slug='beer', category_type='drinks')
        self.salads = MenuCategory.objects.create(name='Salads', slug='salads', category_type='food')
        self.item = MenuItem.objects.create(name='Classic Burger', slug='classic-burger', price=Decimal('14.50'))
        self.placement = MenuItemCategoryAssignment.objects.create(menu_item=self.item, category=self.burgers)
        self.page = self.url(self.menu)
        self.actions = reverse('staff:menu_categories', args=[self.menu.pk])

    def fetch(self, **data):
        return self.client.post(self.actions, data, HTTP_X_REQUESTED_WITH='fetch')

    def on_menu(self):
        return list(self.menu.menu_category_assignments.order_by('display_order').values_list('category__name', 'display_order'))

    def put(self, *categories):
        return [MenuCategoryAssignment.objects.create(menu=self.menu, category=c, display_order=0) for c in categories]

    def test_read_only_staff_see_the_items_and_cannot_change_anything(self):
        assignment = self.put(self.burgers)[0]
        self.client.force_login(User.objects.create_user('viewer', password='x', is_staff=True))
        page = self.client.get(self.page)
        self.assertContains(page, 'Classic Burger')
        self.assertNotContains(page, 'Remove from this menu')
        self.assertNotContains(page, 'New category')
        self.assertEqual(self.client.get(self.actions).status_code, 403)
        for action in ('add', 'new', 'up', 'down', 'remove'):
            self.assertEqual(self.fetch(action=action, assignment=assignment.pk).status_code, 403)
        self.assertEqual(len(self.on_menu()), 1)

    def test_adding_a_category_brings_its_items_without_copying(self):
        response = self.fetch(**{'action': 'add', 'add-category': self.burgers.pk})
        self.assertTemplateUsed(response, 'staff/menu/_menu_categories.html')
        self.assertContains(response, 'Added Burgers with 1 item.')
        self.assertContains(response, 'Classic Burger')
        self.assertEqual(self.on_menu(), [('Burgers', 1)])
        self.assertEqual(MenuItemCategoryAssignment.objects.count(), 1)     # nothing copied

    def test_items_added_to_the_category_later_appear(self):
        self.put(self.burgers)
        other = MenuItem.objects.create(name='Veggie Burger', slug='veggie-burger')
        MenuItemCategoryAssignment.objects.create(menu_item=other, category=self.burgers)
        self.assertContains(self.client.get(self.page), 'Veggie Burger')

    def test_add_goes_to_the_end(self):
        self.put(self.burgers)
        self.fetch(**{'action': 'add', 'add-category': self.beer.pk})
        self.assertEqual(self.on_menu(), [('Burgers', 1), ('Beer', 2)])

    def test_category_already_on_the_menu_is_refused_and_not_offered(self):
        self.put(self.burgers)
        self.assertNotContains(self.client.get(self.page), f'<option value="{self.burgers.pk}"')
        response = self.fetch(**{'action': 'add', 'add-category': self.burgers.pk})
        self.assertContains(response, "isn&#x27;t on this menu yet")
        self.assertEqual(len(self.on_menu()), 1)

    def test_choices_are_grouped_with_counts_and_skip_inactive(self):
        MenuCategory.objects.create(name='Old Stuff', slug='old-stuff', is_active=False)
        html = self.client.get(self.page).content.decode()
        self.assertIn('<optgroup label="Food">', html)
        self.assertIn('<optgroup label="Drinks">', html)
        self.assertIn('Burgers (1 item)', html)
        self.assertIn('Beer (0 items)', html)
        self.assertNotIn('Old Stuff', html)

    def test_new_category_is_created_and_added_with_the_name_as_heading(self):
        response = self.fetch(**{'action': 'new', 'newcat-name': 'Omelettes & More', 'newcat-display_name': '',
                                 'newcat-category_type': 'food'})
        self.assertContains(response, 'Created Omelettes &amp; More.')
        category = MenuCategory.objects.get(name='Omelettes & More')
        self.assertEqual((category.slug, category.display_name), ('omelettes-more', 'Omelettes & More'))
        self.assertEqual(self.on_menu(), [('Omelettes & More', 1)])

    def test_new_category_keeps_a_given_heading(self):
        self.fetch(**{'action': 'new', 'newcat-name': 'Fall', 'newcat-display_name': 'Fall Favorites',
                      'newcat-category_type': 'drinks'})
        category = MenuCategory.objects.get(name='Fall')
        self.assertEqual((category.display_name, category.category_type), ('Fall Favorites', 'drinks'))

    def test_duplicate_category_name_is_refused(self):
        response = self.fetch(**{'action': 'new', 'newcat-name': 'burgers', 'newcat-category_type': 'food'})
        self.assertContains(response, 'already exists')
        self.assertEqual(MenuCategory.objects.filter(name__iexact='burgers').count(), 1)
        self.assertEqual(self.on_menu(), [])

    def test_new_category_type_defaults_from_the_menu(self):
        drinks = Menu.objects.create(title='Bar', slug='bar', menu_type='drinks')
        self.assertRegex(' '.join(self.client.get(self.url(drinks)).content.decode().split()),
                         r'value="drinks" selected')

    def test_reorder_only_changes_this_menu(self):
        first, second, third = self.put(self.burgers, self.beer, self.salads)
        other = Menu.objects.create(title='Other', slug='other', menu_type='food')
        kept = MenuCategoryAssignment.objects.create(menu=other, category=self.burgers, display_order=9)
        self.fetch(action='up', assignment=third.pk)
        self.assertEqual([n for n, _ in self.on_menu()], ['Burgers', 'Salads', 'Beer'])
        self.fetch(action='down', assignment=first.pk)
        self.assertEqual(self.on_menu(), [('Salads', 1), ('Burgers', 2), ('Beer', 3)])
        kept.refresh_from_db()
        self.assertEqual(kept.display_order, 9)

    def test_moving_past_the_end_changes_nothing(self):
        first, second = self.put(self.burgers, self.beer)
        self.fetch(action='up', assignment=first.pk)
        self.fetch(action='down', assignment=second.pk)
        self.assertEqual(self.on_menu(), [('Burgers', 1), ('Beer', 2)])

    def test_remove_keeps_the_category_and_its_items(self):
        assignment = self.put(self.burgers)[0]
        response = self.fetch(action='remove', assignment=assignment.pk)
        self.assertContains(response, 'Took Burgers off this menu')
        self.assertEqual(self.on_menu(), [])
        self.assertTrue(MenuCategory.objects.filter(pk=self.burgers.pk).exists())
        self.assertTrue(MenuItemCategoryAssignment.objects.filter(pk=self.placement.pk).exists())

    def test_shared_category_names_its_other_menus(self):
        self.put(self.burgers)
        other = Menu.objects.create(title='Event Food', slug='event-food', menu_type='food')
        MenuCategoryAssignment.objects.create(menu=other, category=self.burgers)
        self.assertContains(self.client.get(self.page), 'Also on: Event Food')

    def test_item_flags_and_special_price_show(self):
        self.put(self.burgers)
        self.placement.override_price = Decimal('9.00')
        self.placement.is_active = False
        self.placement.save()
        self.item.is_available = False
        self.item.save()
        page = self.client.get(self.page)
        self.assertContains(page, '$9.00')
        self.assertContains(page, 'Hidden here')
        self.assertContains(page, 'Unavailable')

    def test_assignment_of_another_menu_is_404_and_unknown_action_400(self):
        other = Menu.objects.create(title='Other', slug='other', menu_type='food')
        foreign = MenuCategoryAssignment.objects.create(menu=other, category=self.burgers)
        self.assertEqual(self.fetch(action='remove', assignment=foreign.pk).status_code, 404)
        self.assertEqual(self.fetch(action='up', assignment='abc').status_code, 404)
        self.assertEqual(self.fetch(action='explode').status_code, 400)

    def test_plain_post_redirects_to_the_tab(self):
        response = self.client.post(self.actions, {'action': 'add', 'add-category': self.burgers.pk})
        self.assertRedirects(response, self.page + '#categories', fetch_redirect_response=False)

    def test_new_menu_opens_on_categories_and_reaches_the_public_page(self):
        response = self.client.post(self.add_url, settings(title='Late Night', menu_type='promo'))
        menu = Menu.objects.get(slug='late-night')
        self.assertRedirects(response, self.url(menu) + '#categories', fetch_redirect_response=False)
        self.client.post(reverse('staff:menu_categories', args=[menu.pk]),
                         {'action': 'add', 'add-category': self.burgers.pk}, HTTP_X_REQUESTED_WITH='fetch')
        self.assertContains(self.client.get(reverse('menu:menu_detail', args=['late-night'])), 'Classic Burger')

    def test_query_count_doesnt_grow_with_the_items(self):
        self.put(self.burgers)
        self.client.get(self.page)                                  # settle session and site settings
        with CaptureQueriesContext(connection) as few:
            self.client.get(self.page)
        for n in range(10):
            item = MenuItem.objects.create(name=f'Burger {n}', slug=f'burger-{n}')
            MenuItemCategoryAssignment.objects.create(menu_item=item, category=self.burgers)
        with CaptureQueriesContext(connection) as many:
            self.client.get(self.page)
        self.assertEqual(len(many), len(few))


class CategoryItemsTests(MenuBuilderTestCase):
    def setUp(self):
        super().setUp()
        self.menu = Menu.objects.create(title='Food', slug='food', menu_type='food')
        self.burgers = MenuCategory.objects.create(name='Burgers', slug='burgers')
        self.assignment = MenuCategoryAssignment.objects.create(menu=self.menu, category=self.burgers)
        self.items = [MenuItem.objects.create(name=n, slug=n.lower()) for n in ('Alpha', 'Bravo', 'Charlie')]
        self.page = self.url(self.menu)
        self.actions = reverse('staff:menu_categories', args=[self.menu.pk])
        self.picker = reverse('staff:menu_category_items', args=[self.menu.pk])

    def fetch(self, **data):
        return self.client.post(self.actions, data, HTTP_X_REQUESTED_WITH='fetch')

    def add(self, *items):
        return self.fetch(action='items_add', assignment=self.assignment.pk, item_ids=[i.pk for i in items])

    def order(self):
        return list(self.burgers.item_assignments.order_by('order').values_list('menu_item__name', 'order'))

    def placement(self, item):
        return MenuItemCategoryAssignment.objects.get(menu_item=item, category=self.burgers)

    def test_add_several_in_the_order_picked_at_the_end(self):
        MenuItemCategoryAssignment.objects.create(menu_item=self.items[0], category=self.burgers, order=5)
        response = self.add(self.items[2], self.items[1])
        self.assertContains(response, 'Added 2 items to Burgers.')
        self.assertEqual(self.order(), [('Alpha', 5), ('Charlie', 6), ('Bravo', 7)])

    def test_already_placed_and_bad_ids_are_ignored(self):
        self.add(self.items[0])
        response = self.fetch(action='items_add', assignment=self.assignment.pk,
                              item_ids=[self.items[0].pk, 'x', 999999])
        self.assertContains(response, 'No new items added.')
        self.assertEqual(len(self.order()), 1)

    def test_move_renumbers_and_stops_at_the_ends(self):
        self.add(*self.items)
        self.fetch(action='item_up', placement=self.placement(self.items[2]).pk)
        self.assertEqual(self.order(), [('Alpha', 1), ('Charlie', 2), ('Bravo', 3)])
        self.fetch(action='item_down', placement=self.placement(self.items[1]).pk)
        self.fetch(action='item_up', placement=self.placement(self.items[0]).pk)
        self.assertEqual(self.order(), [('Alpha', 1), ('Charlie', 2), ('Bravo', 3)])

    def test_first_move_clears_ties(self):
        for item in self.items:
            MenuItemCategoryAssignment.objects.create(menu_item=item, category=self.burgers, order=0)
        self.fetch(action='item_down', placement=self.placement(self.items[0]).pk)
        self.assertEqual(self.order(), [('Bravo', 1), ('Alpha', 2), ('Charlie', 3)])

    def test_items_only_move_within_their_subcategory(self):
        tap = MenuSubCategory.objects.create(category=self.burgers, name='Smash', slug='burgers-smash', order=1)
        self.add(*self.items[:2])
        first, second = self.placement(self.items[0]), self.placement(self.items[1])
        second.subcategory = tap
        second.save()
        self.fetch(action='item_down', placement=second.pk)
        self.fetch(action='item_up', placement=first.pk)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual((first.subcategory, second.subcategory), (None, tap))
        html = self.client.get(self.page).content.decode()
        self.assertNotIn('value="item_up"', html)
        self.assertNotIn('value="item_down"', html)

    def test_take_out_keeps_the_item(self):
        self.add(self.items[0])
        response = self.fetch(action='item_remove', placement=self.placement(self.items[0]).pk)
        self.assertContains(response, 'Took Alpha out of Burgers.')
        self.assertEqual(self.order(), [])
        self.assertTrue(MenuItem.objects.filter(pk=self.items[0].pk).exists())

    def test_take_out_names_the_other_menus_it_leaves(self):
        self.add(self.items[0])
        other = Menu.objects.create(title='Event Food', slug='event-food', menu_type='food')
        MenuCategoryAssignment.objects.create(menu=other, category=self.burgers)
        self.assertContains(self.client.get(self.page), 'Also leaves Event Food.')

    def test_placement_in_a_category_not_on_this_menu_is_404(self):
        elsewhere = MenuCategory.objects.create(name='Elsewhere', slug='elsewhere')
        foreign = MenuItemCategoryAssignment.objects.create(menu_item=self.items[0], category=elsewhere)
        for action in ('item_up', 'item_down', 'item_remove'):
            self.assertEqual(self.fetch(action=action, placement=foreign.pk).status_code, 404)
        self.assertEqual(self.fetch(action='item_remove', placement='abc').status_code, 404)
        other = Menu.objects.create(title='Other', slug='other', menu_type='food')
        assignment = MenuCategoryAssignment.objects.create(menu=other, category=elsewhere)
        self.assertEqual(self.fetch(action='items_add', assignment=assignment.pk, item_ids=[1]).status_code, 404)

    def test_picker_lists_the_library_marks_added_and_searches(self):
        self.add(self.items[0])
        html = self.client.get(self.picker, {'assignment': self.assignment.pk}).content.decode()
        self.assertIn('Bravo', html)
        self.assertRegex(html, rf'data-id="{self.items[0].pk}" disabled')
        self.assertIn('Added', html)
        html = self.client.get(self.picker, {'assignment': self.assignment.pk, 'q': 'char'}).content.decode()
        self.assertIn('Charlie', html)
        self.assertNotIn('Bravo', html)

    def test_picker_pages_and_scoping(self):
        from apps.staff.views import ITEM_PICKER_PAGE_SIZE
        for n in range(ITEM_PICKER_PAGE_SIZE):
            MenuItem.objects.create(name=f'Z {n:02}', slug=f'z-{n}')
        first = self.client.get(self.picker, {'assignment': self.assignment.pk}).content.decode()
        self.assertEqual(first.count('data-id='), ITEM_PICKER_PAGE_SIZE)
        self.assertIn('data-next="2"', first)
        second = self.client.get(self.picker, {'assignment': self.assignment.pk, 'page': 2}).content.decode()
        self.assertEqual(second.count('data-id='), 3)
        self.assertEqual(self.client.get(self.picker).status_code, 404)
        other = Menu.objects.create(title='Other', slug='other', menu_type='food')
        self.assertEqual(self.client.get(
            reverse('staff:menu_category_items', args=[other.pk]), {'assignment': self.assignment.pk}).status_code, 404)

    def test_read_only_staff_get_no_controls_and_403(self):
        self.add(self.items[0])
        placement = self.placement(self.items[0])
        self.client.force_login(User.objects.create_user('viewer', password='x', is_staff=True))
        page = self.client.get(self.page)
        self.assertContains(page, 'Alpha')
        self.assertNotContains(page, '+ Add items')
        self.assertNotContains(page, 'Take out')
        self.assertEqual(self.client.get(self.picker, {'assignment': self.assignment.pk}).status_code, 403)
        for action in ('items_add', 'item_up', 'item_down', 'item_remove'):
            self.assertEqual(self.fetch(action=action, placement=placement.pk,
                                        assignment=self.assignment.pk).status_code, 403)
        self.assertEqual(len(self.order()), 1)

    def test_added_item_shows_on_the_public_page_in_the_new_order(self):
        self.add(self.items[0], self.items[1])
        self.fetch(action='item_up', placement=self.placement(self.items[1]).pk)
        html = self.client.get(reverse('menu:menu_detail', args=['food'])).content.decode()
        self.assertLess(html.index('Bravo'), html.index('Alpha'))
