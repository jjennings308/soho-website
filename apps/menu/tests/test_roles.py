from datetime import date, datetime
from unittest import mock
from zoneinfo import ZoneInfo

from django.test import TestCase

from apps.core.models import SiteSettings
from apps.events.models import EventDay
from apps.menu.models import Menu
from apps.menu.utils import get_active_menus


def make_menu(slug, role='none', **kwargs):
    return Menu.objects.create(title=slug.title(), slug=slug, role=role, **kwargs)


class MenuRoleTests(TestCase):
    def test_assigning_a_role_demotes_previous_holder(self):
        old = make_menu('old-food', role='default_food')
        new = make_menu('new-food', role='default_food')
        old.refresh_from_db()
        self.assertEqual(old.role, 'none')
        self.assertEqual(new.role, 'default_food')

    def test_other_roles_untouched(self):
        drinks = make_menu('drinks', role='default_drinks')
        make_menu('food', role='default_food')
        drinks.refresh_from_db()
        self.assertEqual(drinks.role, 'default_drinks')

    def test_many_menus_may_have_no_role(self):
        make_menu('a')
        make_menu('b')
        self.assertEqual(Menu.objects.filter(role='none').count(), 2)


class ActiveMenusTests(TestCase):
    def setUp(self):
        self.food = make_menu('food', role='default_food')
        self.drinks = make_menu('drinks', role='default_drinks')
        self.event_food = make_menu('event-food', role='event_food')
        self.event_drinks = make_menu('event-drinks', role='event_drinks')

    def test_standard_mode_uses_default_menus(self):
        menus = get_active_menus()
        self.assertEqual((menus['food'], menus['drinks'], menus['event_mode']),
                         (self.food, self.drinks, False))

    def test_event_mode_uses_event_menus(self):
        site = SiteSettings.load()
        site.force_game_day_mode = True
        site.save()
        menus = get_active_menus()
        self.assertEqual((menus['food'], menus['drinks'], menus['event_mode']),
                         (self.event_food, self.event_drinks, True))

    def test_home_game_today_switches_to_event_menus(self):
        now = datetime(2026, 10, 18, 12, tzinfo=ZoneInfo('America/New_York'))
        EventDay.objects.create(date=date(2026, 10, 18), event_type='game', home_away='home')
        with mock.patch('django.utils.timezone.now', return_value=now):
            self.assertEqual(get_active_menus()['food'], self.event_food)

    def test_missing_role_gives_none(self):
        self.drinks.delete()
        self.assertIsNone(get_active_menus()['drinks'])
