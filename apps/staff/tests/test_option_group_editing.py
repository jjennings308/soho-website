"""Phase 6 of docs/PLAN-menu-option-groups.md: option groups in the staff portal."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from apps.menu.models import (
    CategoryOptionGroup, Menu, MenuCategory, MenuCategoryAssignment, MenuItem, MenuItemCategoryAssignment,
    OptionChoice, OptionGroup,
)
from apps.staff.permissions import MANAGER_GROUP

User = get_user_model()
FETCH = {'HTTP_X_REQUESTED_WITH': 'fetch'}


def group_data(group, choices, **changes):
    """POST data for the group editor: the group's values, then `choices` as formset rows (dicts)."""
    data = {'name': group.name, 'note': group.note, 'next': ''}
    if group.is_add_on:
        data['is_add_on'] = 'on'
    if group.is_active:
        data['is_active'] = 'on'
    saved = [c for c in choices if c.get('id')]
    data.update({'choices-TOTAL_FORMS': str(len(choices)), 'choices-INITIAL_FORMS': str(len(saved)),
                 'choices-MIN_NUM_FORMS': '0', 'choices-MAX_NUM_FORMS': '1000'})
    for i, row in enumerate(choices):
        for key, value in row.items():
            if value is not None:
                data[f'choices-{i}-{key}'] = value
    for key, value in changes.items():
        if value is False:
            data.pop(key, None)
        else:
            data[key] = value
    return data


def row(choice=None, **fields):
    """One formset row: a saved choice's values (plus changes) or a new one."""
    values = {}
    if choice:
        values = {'id': str(choice.pk), 'name': choice.name, 'order': str(choice.order),
                  'upcharge': '' if choice.upcharge is None else str(choice.upcharge)}
        if choice.cooked_to_order:
            values['cooked_to_order'] = 'on'
        if choice.is_active:
            values['is_active'] = 'on'
    else:
        values = {'order': '0', 'is_active': 'on'}
    for key, value in fields.items():
        if value is False:
            values.pop(key, None)
        else:
            values[key] = value
    return values


class OptionGroupPortalTestCase(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user('mgr', password='x', is_staff=True)
        self.manager.groups.add(Group.objects.get(name=MANAGER_GROUP))
        self.client.force_login(self.manager)
        self.food = Menu.objects.create(title='Food', slug='food', menu_type='food', role='default_food')
        self.salads = self._category('Soups and Salads', 'soups-and-salads', 'House Salad', 1)
        self.wraps = self._category('Tacos and Wraps', 'tacos-and-wraps', 'Chicken Wrap', 2)

    def _category(self, name, slug, item_name, position):
        category = MenuCategory.objects.create(name=name, slug=slug, display_name=name)
        MenuCategoryAssignment.objects.create(menu=self.food, category=category, display_order=position)
        item = MenuItem.objects.create(name=item_name, slug=slugify_(item_name))
        MenuItemCategoryAssignment.objects.create(menu_item=item, category=category)
        return category

    def section_url(self, category):
        return reverse('staff:category_option_groups', args=[category.pk])

    def act(self, category, **data):
        return self.client.post(self.section_url(category), data, **FETCH)


def slugify_(text):
    from django.utils.text import slugify
    return slugify(text)


class DoneWhenTests(OptionGroupPortalTestCase):
    """The plan's Phase 6 'done when', end to end."""

    def test_create_attach_twice_edit_once_detach_reattach(self):
        response = self.act(self.salads, action='new', **{'newgroup-name': 'Dressings'})
        self.assertContains(response, 'Created Dressings')
        dressings = OptionGroup.objects.get(name='Dressings')
        self.assertEqual(dressings.slug, 'dressings')
        self.assertFalse(dressings.is_add_on)

        editor = reverse('staff:option_group', args=[dressings.pk])
        self.client.post(editor, group_data(dressings, [row(name='Ranch', order='1'), row(name='Caesar', order='2')]))
        self.assertEqual([c.name for c in dressings.choices.all()], ['Ranch', 'Caesar'])

        self.act(self.wraps, action='attach', group=str(dressings.pk))
        page = self.client.get(editor).content.decode()
        self.assertIn('Also used in:', page)
        self.assertIn('Changes here show in all of them', page)

        ranch = dressings.choices.get(name='Ranch')
        caesar = dressings.choices.get(name='Caesar')
        self.client.post(editor, group_data(dressings, [row(ranch, name='Buttermilk Ranch'), row(caesar)]))
        menu = self.client.get(reverse('menu:full')).content.decode()
        self.assertEqual(menu.count('Buttermilk Ranch'), 2)           # shown in both categories

        link = CategoryOptionGroup.objects.get(category=self.wraps, group=dressings)
        self.act(self.wraps, action='detach', link=str(link.pk))
        link.refresh_from_db()
        self.assertFalse(link.is_active)
        self.assertEqual(self.client.get(reverse('menu:full')).content.decode().count('Buttermilk Ranch'), 1)
        response = self.act(self.wraps, action='attach', group=str(dressings.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CategoryOptionGroup.objects.filter(category=self.wraps, group=dressings).count(), 1)
        link.refresh_from_db()
        self.assertTrue(link.is_active)


class SectionTests(OptionGroupPortalTestCase):
    def setUp(self):
        super().setUp()
        self.sauces = OptionGroup.objects.create(name='Sauces')
        self.adds = OptionGroup.objects.create(name='Add to Any Salad', is_add_on=True)
        OptionChoice.objects.create(group=self.adds, name='Steak', upcharge=Decimal('8'), cooked_to_order=True)

    def links(self):
        return list(CategoryOptionGroup.objects.filter(category=self.salads, is_active=True)
                    .order_by('order').values_list('group__name', 'order'))

    def test_attach_goes_to_the_end_numbered(self):
        self.act(self.salads, action='attach', group=str(self.sauces.pk))
        self.act(self.salads, action='attach', group=str(self.adds.pk))
        self.assertEqual(self.links(), [('Sauces', 1), ('Add to Any Salad', 2)])

    def test_new_group_goes_to_the_end(self):
        self.act(self.salads, action='attach', group=str(self.sauces.pk))
        self.act(self.salads, action='new', **{'newgroup-name': 'Dressings', 'newgroup-is_add_on': 'on'})
        self.assertEqual(self.links(), [('Sauces', 1), ('Dressings', 2)])
        self.assertTrue(OptionGroup.objects.get(name='Dressings').is_add_on)

    def test_reorder(self):
        self.act(self.salads, action='attach', group=str(self.sauces.pk))
        self.act(self.salads, action='attach', group=str(self.adds.pk))
        link = CategoryOptionGroup.objects.get(category=self.salads, group=self.adds)
        self.act(self.salads, action='up', link=str(link.pk))
        self.assertEqual(self.links(), [('Add to Any Salad', 1), ('Sauces', 2)])

    def test_section_shows_choices_and_sharing(self):
        CategoryOptionGroup.objects.create(category=self.wraps, group=self.adds)
        self.act(self.salads, action='attach', group=str(self.adds.pk))
        html = self.client.get(reverse('staff:category', args=[self.salads.pk])).content.decode()
        self.assertIn('Steak* +8', html)
        self.assertIn('Also used in: Tacos and Wraps', html)

    def test_attach_list_leaves_out_attached_groups(self):
        self.act(self.salads, action='attach', group=str(self.sauces.pk))
        html = self.client.get(self.section_url(self.salads)).content.decode()
        self.assertNotIn(f'<option value="{self.sauces.pk}">', html)
        self.assertIn(f'<option value="{self.adds.pk}">', html)

    def test_duplicate_new_name_refused(self):
        response = self.act(self.salads, action='new', **{'newgroup-name': 'sauces'})
        self.assertContains(response, 'Another option group already has this name.')
        self.assertEqual(OptionGroup.objects.count(), 2)

    def test_no_group_chosen(self):
        self.assertContains(self.act(self.salads, action='attach', group=''), 'Choose a group to add.')

    def test_link_from_another_category_404(self):
        other = CategoryOptionGroup.objects.create(category=self.wraps, group=self.sauces)
        response = self.act(self.salads, action='detach', link=str(other.pk))
        self.assertEqual(response.status_code, 404)
        other.refresh_from_db()
        self.assertTrue(other.is_active)

    def test_plain_post_redirects_to_section(self):
        response = self.client.post(self.section_url(self.salads), {'action': 'attach', 'group': str(self.sauces.pk)})
        self.assertRedirects(response, reverse('staff:category', args=[self.salads.pk]) + '#option-groups')


class EditorTests(OptionGroupPortalTestCase):
    def setUp(self):
        super().setUp()
        self.group = OptionGroup.objects.create(name='Add to Any Salad', slug='add-to-any-salad', is_add_on=True)
        self.steak = OptionChoice.objects.create(group=self.group, name='Steak', upcharge=Decimal('8'), order=1)
        self.url = reverse('staff:option_group', args=[self.group.pk])

    def test_add_edit_remove_choices_in_one_save(self):
        chicken = OptionChoice.objects.create(group=self.group, name='Chicken', upcharge=Decimal('7'), order=2)
        response = self.client.post(self.url, group_data(self.group, [
            row(self.steak, upcharge='9', cooked_to_order='on'),
            row(chicken, DELETE='on'),
            row(name='Salmon', upcharge='10', order='3'),
        ], note='Add a protein'))
        self.assertRedirects(response, self.url)
        self.group.refresh_from_db()
        self.assertEqual(self.group.note, 'Add a protein')
        self.assertEqual([(c.name, c.upcharge, c.cooked_to_order) for c in self.group.choices.all()],
                         [('Steak', Decimal('9.00'), True), ('Salmon', Decimal('10.00'), False)])

    def test_rename_keeps_slug(self):
        self.client.post(self.url, group_data(self.group, [row(self.steak)], name='Salad Add-ons'))
        self.group.refresh_from_db()
        self.assertEqual((self.group.name, self.group.slug), ('Salad Add-ons', 'add-to-any-salad'))

    def test_negative_upcharge_saves_nothing(self):
        response = self.client.post(self.url, group_data(self.group, [row(self.steak, upcharge='-1')], name='Renamed'))
        self.assertEqual(response.status_code, 200)
        self.group.refresh_from_db()
        self.assertEqual(self.group.name, 'Add to Any Salad')
        self.steak.refresh_from_db()
        self.assertEqual(self.steak.upcharge, Decimal('8'))

    def test_duplicate_choice_name_refused(self):
        response = self.client.post(self.url, group_data(self.group, [row(self.steak), row(name='Steak')]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.group.choices.count(), 1)

    def test_group_with_no_choices_saves(self):
        response = self.client.post(self.url, group_data(self.group, [row(self.steak, DELETE='on')], note='Prices vary'))
        self.assertRedirects(response, self.url)
        self.assertEqual(self.group.choices.count(), 0)

    def test_next_round_trip(self):
        back = reverse('staff:category', args=[self.salads.pk]) + '#option-groups'
        response = self.client.post(self.url, group_data(self.group, [row(self.steak)], next=back))
        self.assertTrue(response.url.startswith(self.url + '?next='))
        self.assertContains(self.client.get(response.url), f'href="{back}"')


class AccessTests(OptionGroupPortalTestCase):
    def test_read_only_staff(self):
        group = OptionGroup.objects.create(name='Dressings')
        OptionChoice.objects.create(group=group, name='Ranch')
        CategoryOptionGroup.objects.create(category=self.salads, group=group)
        self.client.force_login(User.objects.create_user('viewer', password='x', is_staff=True))
        category_page = self.client.get(reverse('staff:category', args=[self.salads.pk]))
        self.assertContains(category_page, 'Dressings')
        self.assertNotContains(category_page, 'Create group')
        editor = self.client.get(reverse('staff:option_group', args=[group.pk]))
        self.assertContains(editor, 'Ranch')
        self.assertNotContains(editor, '>Save</button>')
        self.assertEqual(self.client.post(reverse('staff:option_group', args=[group.pk]),
                                          group_data(group, [], name='Hacked')).status_code, 403)
        self.assertEqual(self.act(self.salads, action='new', **{'newgroup-name': 'X'}).status_code, 403)
        group.refresh_from_db()
        self.assertEqual(group.name, 'Dressings')
