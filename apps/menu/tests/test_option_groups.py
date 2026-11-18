from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.menu.models import (
    CategoryOptionGroup, MenuCategory, MenuItem, MenuItemAddon, OptionChoice, OptionGroup,
    format_upcharge,
)
from apps.menu.templatetags.menu_tags import _currency


class FormatUpchargeTests(TestCase):
    def test_whole_dollars(self):
        self.assertEqual(format_upcharge(Decimal('7.00')), '+7')

    def test_cents_follow_currency_filter(self):
        self.assertEqual(format_upcharge(Decimal('7.50')), '+7.5')

    def test_none_and_zero_are_blank(self):
        self.assertEqual(format_upcharge(None), '')
        self.assertEqual(format_upcharge(Decimal('0')), '')

    def test_menu_tags_currency_matches_filter(self):
        self.assertEqual(_currency(Decimal('13.50')), '13.5')
        self.assertEqual(_currency(Decimal('14.00')), '14')
        self.assertEqual(_currency(Decimal('0')), '')


class OptionGroupModelTests(TestCase):
    def setUp(self):
        self.salads = MenuCategory.objects.create(name='Soups and Salads', slug='soups-and-salads')
        self.starters = MenuCategory.objects.create(name='Starters', slug='starters')

    def test_slug_filled_from_name_and_unique(self):
        a = OptionGroup.objects.create(name='Dressings')
        b = OptionGroup.objects.create(name='Dressings')
        self.assertEqual(a.slug, 'dressings')
        self.assertEqual(b.slug, 'dressings-2')

    def test_given_slug_kept_on_rename(self):
        g = OptionGroup.objects.create(name='Sauces', slug='sauces')
        g.name = 'Signature Sauces & Dry Rubs'
        g.save()
        g.refresh_from_db()
        self.assertEqual(g.slug, 'sauces')

    def test_choice_upcharge_display(self):
        g = OptionGroup.objects.create(name='Add to Any Salad', is_add_on=True)
        steak = OptionChoice.objects.create(group=g, name='Steak', upcharge=Decimal('8'))
        free = OptionChoice.objects.create(group=g, name='Croutons', upcharge=Decimal('0'))
        none = OptionChoice.objects.create(group=g, name='Extra dressing')
        self.assertEqual(steak.display_upcharge, '+8')
        self.assertEqual(free.display_upcharge, '')
        self.assertEqual(none.display_upcharge, '')

    def test_negative_upcharge_rejected(self):
        g = OptionGroup.objects.create(name='Add to Any Salad', is_add_on=True)
        choice = OptionChoice(group=g, name='Steak', upcharge=Decimal('-1'))
        with self.assertRaises(ValidationError):
            choice.full_clean()

    def test_choices_ordered(self):
        g = OptionGroup.objects.create(name='Dressings')
        OptionChoice.objects.create(group=g, name='Ranch', order=2)
        OptionChoice.objects.create(group=g, name='Caesar', order=1)
        self.assertEqual([c.name for c in g.choices.all()], ['Caesar', 'Ranch'])

    def test_group_without_choices_is_valid(self):
        g = OptionGroup(name='Sides', note='Prices vary')
        g.full_clean()
        g.save()
        self.assertEqual(g.choices.count(), 0)

    def test_one_group_on_several_categories(self):
        g = OptionGroup.objects.create(name='Dressings')
        CategoryOptionGroup.objects.create(category=self.salads, group=g)
        CategoryOptionGroup.objects.create(category=self.starters, group=g)
        self.assertEqual(set(g.categories.all()), {self.salads, self.starters})
        self.assertEqual(list(self.salads.option_groups.all()), [g])

    def test_group_attached_once_per_category(self):
        g = OptionGroup.objects.create(name='Dressings')
        CategoryOptionGroup.objects.create(category=self.salads, group=g)
        with self.assertRaises(IntegrityError):
            CategoryOptionGroup.objects.create(category=self.salads, group=g)


class AddonsDisplayTests(TestCase):
    def setUp(self):
        self.item = MenuItem.objects.create(name='Cheese Quesadilla', slug='cheese-quesadilla')

    def test_lists_available_addons_in_order(self):
        MenuItemAddon.objects.create(menu_item=self.item, name='Pulled pork', price=Decimal('6'), order=2)
        MenuItemAddon.objects.create(menu_item=self.item, name='Grilled chicken', price=Decimal('5'), order=1)
        MenuItemAddon.objects.create(
            menu_item=self.item, name='Steak', price=Decimal('7'), order=3, is_available=False)
        self.assertEqual(self.item.addons_display, 'Grilled chicken +5 · Pulled pork +6')

    def test_blank_when_none(self):
        self.assertEqual(self.item.addons_display, '')

    def test_zero_price_written_to_db_shows_no_bare_plus(self):
        # The model's 0.01 minimum normally prevents this; guard anyway.
        MenuItemAddon.objects.create(menu_item=self.item, name='Salsa', price=Decimal('0'))
        self.assertEqual(self.item.addons_display, 'Salsa')


class OptionGroupAdminTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        self.admin = get_user_model().objects.create_superuser('root', 'root@example.com', 'pw')
        self.client.force_login(self.admin)
        self.salads = MenuCategory.objects.create(name='Soups and Salads', slug='soups-and-salads')

    def _inline(self, prefix, rows, initial=0):
        data = {
            f'{prefix}-TOTAL_FORMS': str(len(rows)),
            f'{prefix}-INITIAL_FORMS': str(initial),
            f'{prefix}-MIN_NUM_FORMS': '0',
            f'{prefix}-MAX_NUM_FORMS': '1000',
        }
        for i, row in enumerate(rows):
            for key, value in row.items():
                data[f'{prefix}-{i}-{key}'] = value
        return data

    def test_pages_load(self):
        from django.urls import reverse
        g = OptionGroup.objects.create(name='Dressings')
        OptionChoice.objects.create(group=g, name='Ranch')
        CategoryOptionGroup.objects.create(category=self.salads, group=g)
        for url in (
            reverse('admin:menu_optiongroup_changelist'),
            reverse('admin:menu_optiongroup_add'),
            reverse('admin:menu_optiongroup_change', args=[g.pk]),
            reverse('admin:menu_menucategory_change', args=[self.salads.pk]),
        ):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_create_add_on_group_with_choices_and_attach(self):
        from django.urls import reverse
        data = {'name': 'Add to Any Salad', 'slug': 'add-to-any-salad', 'note': '',
                'is_add_on': 'on', 'is_active': 'on'}
        data.update(self._inline('choices', [
            {'name': 'Grilled or Crispy Chicken', 'upcharge': '7', 'order': '1', 'is_active': 'on'},
            {'name': 'Steak', 'upcharge': '8', 'cooked_to_order': 'on', 'order': '2', 'is_active': 'on'},
        ]))
        data.update(self._inline('category_links', [
            {'category': str(self.salads.pk), 'order': '2', 'is_active': 'on'},
        ]))
        resp = self.client.post(reverse('admin:menu_optiongroup_add'), data)
        self.assertEqual(resp.status_code, 302, resp.content[:2000])
        g = OptionGroup.objects.get(slug='add-to-any-salad')
        self.assertTrue(g.is_add_on)
        self.assertEqual([(c.name, c.display_upcharge, c.cooked_to_order) for c in g.choices.all()],
                         [('Grilled or Crispy Chicken', '+7', False), ('Steak', '+8', True)])
        self.assertEqual(list(self.salads.option_groups.all()), [g])

    def test_negative_upcharge_refused_in_admin(self):
        from django.urls import reverse
        data = {'name': 'Add to Any Salad', 'slug': 'add-to-any-salad', 'is_add_on': 'on', 'is_active': 'on'}
        data.update(self._inline('choices', [{'name': 'Steak', 'upcharge': '-1', 'order': '1'}]))
        data.update(self._inline('category_links', []))
        resp = self.client.post(reverse('admin:menu_optiongroup_add'), data)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(OptionGroup.objects.exists())


class PublicMenuOptionGroupTests(TestCase):
    """Phase 4: the main menu page (menu_sections → menu_category_section)."""

    def setUp(self):
        from apps.menu.models import Menu, MenuCategoryAssignment, MenuItemCategoryAssignment
        self.food = Menu.objects.create(title='Food', slug='food', menu_type='food', role='default_food')
        self.salads = MenuCategory.objects.create(
            name='Soups and Salads', slug='soups-and-salads', display_name='Soups & Salads',
            subtitle='Fresh every day', description='Fresh salads and homemade soups')
        self.salad = MenuItem.objects.create(name='House Salad', slug='house-salad', price=Decimal('9'))
        MenuItemCategoryAssignment.objects.create(menu_item=self.salad, category=self.salads)
        MenuCategoryAssignment.objects.create(menu=self.food, category=self.salads, display_order=1)

        self.adds = OptionGroup.objects.create(name='Add to Any Salad', is_add_on=True)
        OptionChoice.objects.create(group=self.adds, name='Chicken', upcharge=Decimal('7'), order=1)
        OptionChoice.objects.create(group=self.adds, name='Steak', upcharge=Decimal('8'), order=2,
                                    cooked_to_order=True)
        OptionChoice.objects.create(group=self.adds, name='Tofu', upcharge=Decimal('5'), order=3, is_active=False)
        self.dressings = OptionGroup.objects.create(name='Dressings')
        OptionChoice.objects.create(group=self.dressings, name='Ranch', upcharge=Decimal('1'), order=1)
        OptionChoice.objects.create(group=self.dressings, name='Caesar', order=2)
        CategoryOptionGroup.objects.create(category=self.salads, group=self.dressings, order=1)
        CategoryOptionGroup.objects.create(category=self.salads, group=self.adds, order=2)

    def get(self):
        from django.urls import reverse
        return self.client.get(reverse('menu:full')).content.decode()

    def test_groups_render_in_order_with_choices(self):
        html = self.get()
        self.assertLess(html.index('Dressings'), html.index('Add to Any Salad'))
        self.assertLess(html.index('House Salad'), html.index('Dressings'))   # at the end of the section
        self.assertIn('Steak*', html)
        self.assertIn('menu-option-group__upcharge">+8<', html)
        self.assertNotIn('Tofu', html)                                       # inactive choice

    def test_upcharge_only_shown_for_add_on_groups(self):
        html = self.get()
        self.assertIn('Ranch', html)
        self.assertNotIn('menu-option-group__upcharge">+1<', html)

    def test_inactive_group_or_link_hidden(self):
        OptionGroup.objects.filter(pk=self.dressings.pk).update(is_active=False)
        CategoryOptionGroup.objects.filter(group=self.adds).update(is_active=False)
        html = self.get()
        self.assertNotIn('Dressings', html)
        self.assertNotIn('Add to Any Salad', html)

    def test_subtitle_and_description(self):
        html = self.get()
        self.assertIn('menu-category-subtitle">Fresh every day<', html)
        self.assertIn('Fresh salads and homemade soups', html)

    def test_blank_heading_hides_subtitle_but_keeps_description(self):
        MenuCategory.objects.filter(pk=self.salads.pk).update(display_name='')
        html = self.get()
        self.assertNotIn('Fresh every day', html)
        self.assertIn('Fresh salads and homemade soups', html)

    def test_category_with_only_groups_renders(self):
        from apps.menu.models import MenuCategoryAssignment
        sauces_cat = MenuCategory.objects.create(name='Sauces', slug='sauces', display_name='Sauces')
        MenuCategoryAssignment.objects.create(menu=self.food, category=sauces_cat, display_order=2)
        group = OptionGroup.objects.create(name='Signature Sauces')
        OptionChoice.objects.create(group=group, name='Buffalo')
        CategoryOptionGroup.objects.create(category=sauces_cat, group=group)
        html = self.get()
        self.assertIn('id="cat-sauces"', html)
        self.assertIn('Signature Sauces', html)

    def test_empty_category_still_hidden(self):
        from apps.menu.models import MenuCategoryAssignment
        empty = MenuCategory.objects.create(name='Empty', slug='empty', display_name='Empty Section')
        MenuCategoryAssignment.objects.create(menu=self.food, category=empty, display_order=3)
        self.assertNotIn('Empty Section', self.get())

    def test_item_addons_line_and_modal_json(self):
        MenuItemAddon.objects.create(menu_item=self.salad, name='Bacon', price=Decimal('2'), order=1)
        MenuItemAddon.objects.create(menu_item=self.salad, name='Avocado', price=Decimal('3'), order=2,
                                     is_available=False)
        html = self.get()
        self.assertIn('menu-item__addons mt-1">Bacon +2<', html)
        self.assertNotIn('Avocado', html)
        self.assertIn('&quot;price&quot;: &quot;+2&quot;', html.replace('"', '&quot;'))

    def test_promo_page_does_not_show_groups(self):
        from django.urls import reverse
        from apps.menu.models import Menu, MenuCategoryAssignment
        promo = Menu.objects.create(title='Salad Week', slug='salad-week', menu_type='promo')
        MenuCategoryAssignment.objects.create(menu=promo, category=self.salads)
        html = self.client.get(reverse('menu:menu_detail', args=['salad-week'])).content.decode()
        self.assertIn('House Salad', html)
        self.assertNotIn('Add to Any Salad', html)
