from datetime import datetime, time
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.test import TestCase
from django.urls import reverse

from apps.core.models import RecurrenceMixin
from apps.menu.models import (
    Menu, MenuCategory, MenuCategoryAssignment, MenuItem, MenuItemCategoryAssignment, available_now_q,
)

EASTERN = ZoneInfo('America/New_York')


def at(hour, minute=0, day=2):
    """Freeze the clock. 2 Nov 2026 is a Monday (weekday 0), so day=2 → Monday."""
    moment = datetime(2026, 11, day, hour, minute, tzinfo=EASTERN)
    return patch('django.utils.timezone.now', return_value=moment)


class AvailabilityRulesTests(TestCase):
    """The database filter and the Python property must always give the same answer."""

    def check(self, expected, **fields):
        item, _ = MenuItem.objects.update_or_create(slug='soup', defaults={
            'name': 'Soup', 'is_available': True, 'available_from': None, 'available_until': None,
            'days_of_week': [], **fields})
        self.assertEqual(item.is_available_now, expected, 'is_available_now')
        self.assertEqual(MenuItem.objects.filter(available_now_q(), pk=item.pk).exists(), expected, 'available_now_q')

    def test_no_limits_shows_all_day(self):
        with at(3):
            self.check(True)

    def test_available_switch_wins(self):
        with at(12):
            self.check(False, is_available=False)
            self.check(False, is_available=False, available_from=time(11), available_until=time(16))

    def test_same_day_band(self):
        band = {'available_from': time(11), 'available_until': time(16)}
        for hour, minute, expected in [(10, 59, False), (11, 0, True), (15, 59, True), (16, 0, True), (16, 1, False)]:
            with self.subTest(hour=hour, minute=minute), at(hour, minute):
                self.check(expected, **band)

    def test_open_ended_bands(self):
        with at(10):
            self.check(False, available_from=time(11))
            self.check(True, available_until=time(16))
        with at(17):
            self.check(True, available_from=time(11))
            self.check(False, available_until=time(16))

    def test_overnight_band(self):
        band = {'available_from': time(22), 'available_until': time(2)}
        for hour, expected in [(21, False), (22, True), (23, True), (1, True), (3, False), (12, False)]:
            with self.subTest(hour=hour), at(hour):
                self.check(expected, **band)

    def test_days_of_week(self):
        with at(12):                                    # Monday
            self.check(True, days_of_week=[0, 4])
            self.check(False, days_of_week=[1, 4])
            self.check(False, days_of_week=[0], available_from=time(13))

    def test_late_evening_is_still_today_in_eastern_time(self):
        # 23:30 Monday in Pittsburgh is already Tuesday, and past the band, in UTC.
        with at(23, 30):
            self.check(True, days_of_week=[0])
            self.check(False, days_of_week=[1])
            self.check(True, available_from=time(23), available_until=time(23, 59))

    def test_recurrence_mixin_uses_local_day(self):
        class Thing(RecurrenceMixin):
            class Meta:
                abstract = True

            def __init__(self, days):
                self.days_of_week = days

        with at(23, 30):
            self.assertTrue(Thing.is_active_today(Thing([0])))
            self.assertFalse(Thing.is_active_today(Thing([1])))


class PublicPagesTests(TestCase):
    def setUp(self):
        self.lunch = MenuItem.objects.create(name='Lunch Wrap', slug='lunch-wrap', price=Decimal('11'),
                                             available_from=time(11), available_until=time(16))
        self.steak = MenuItem.objects.create(name='Steak Frites', slug='steak-frites', price=Decimal('24'))
        self.lunch_cat = MenuCategory.objects.create(name='Lunch', slug='lunch', display_name='Lunch Specials')
        self.mains = MenuCategory.objects.create(name='Mains', slug='mains', display_name='Mains Section')
        food = Menu.objects.create(title='Food', slug='food', menu_type='food', role='default_food')
        for category in (self.lunch_cat, self.mains):
            MenuCategoryAssignment.objects.create(menu=food, category=category)
        MenuItemCategoryAssignment.objects.create(menu_item=self.lunch, category=self.lunch_cat)
        MenuItemCategoryAssignment.objects.create(menu_item=self.steak, category=self.mains)

    def test_menu_page_shows_the_item_only_during_its_band(self):
        url = reverse('menu:full')
        with at(12):
            self.assertContains(self.client.get(url), 'Lunch Wrap')
        with at(18):
            response = self.client.get(url)
            self.assertNotContains(response, 'Lunch Wrap')
            self.assertContains(response, 'Steak Frites')

    def test_section_with_nothing_to_show_disappears(self):
        with at(18):
            response = self.client.get(reverse('menu:full'))
            self.assertNotContains(response, 'Lunch Specials')
            self.assertContains(response, 'Mains Section')

    def test_homepage_promo_helpers_respect_the_band(self):
        from apps.core.views import _get_random_promo_item
        promo = Menu.objects.create(title='Promo', slug='promo', menu_type='promo')
        MenuCategoryAssignment.objects.create(menu=promo, category=self.lunch_cat)
        with at(12):
            self.assertEqual(_get_random_promo_item(promo).menu_item, self.lunch)
        with at(18):
            self.assertIsNone(_get_random_promo_item(promo))
