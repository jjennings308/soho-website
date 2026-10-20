from datetime import date, datetime, time
from unittest import mock
from zoneinfo import ZoneInfo

from django.test import TestCase

from apps.core.models import SiteSettings
from apps.events.models import EventDay

EASTERN = ZoneInfo('America/New_York')
TODAY = date(2026, 10, 18)


def at(hour, minute=0):
    """Freeze 'now' at the given Eastern time on TODAY."""
    return mock.patch('django.utils.timezone.now',
                      return_value=datetime(2026, 10, 18, hour, minute, tzinfo=EASTERN))


def make_event(**kwargs):
    defaults = {'date': TODAY, 'event_type': 'game', 'home_away': 'home'}
    return EventDay.objects.create(**{**defaults, **kwargs})


class SmartDefaultTests(TestCase):
    def test_home_game_defaults_to_limited_menu(self):
        self.assertTrue(make_event(home_away='home', limited_menu=False).limited_menu)

    def test_away_game_defaults_to_full_menu(self):
        self.assertFalse(make_event(home_away='away').limited_menu)

    def test_game_without_home_away_keeps_field_default(self):
        self.assertTrue(make_event(home_away='').limited_menu)

    def test_other_event_types_unaffected(self):
        self.assertFalse(make_event(event_type='private_party', home_away='home', limited_menu=False).limited_menu)
        self.assertTrue(make_event(event_type='private_party', home_away='away', limited_menu=True).limited_menu)

    def test_only_applies_on_creation(self):
        event = make_event(home_away='away')
        event.limited_menu = True  # staff turns it on for a watch party
        event.save()
        event.refresh_from_db()
        self.assertTrue(event.limited_menu)


class MenuModeTests(TestCase):
    def mode(self):
        return EventDay.get_current_menu_mode()

    def test_default_is_full(self):
        with at(12):
            self.assertEqual(self.mode(), 'full')

    def test_all_day_home_game_is_limited(self):
        make_event(game_time=None)
        with at(9):
            self.assertEqual(self.mode(), 'limited')

    def test_lead_hours_before_game_time(self):
        make_event(game_time=time(19, 0), limited_menu_lead_hours=2)
        with at(16, 59):
            self.assertEqual(self.mode(), 'full')
        with at(17, 0):
            self.assertEqual(self.mode(), 'limited')

    def test_inactive_or_unlimited_events_ignored(self):
        make_event(is_active=False)
        make_event(event_type='live_music', limited_menu=False)
        with at(12):
            self.assertEqual(self.mode(), 'full')

    def test_other_days_ignored(self):
        make_event(date=date(2026, 10, 19))
        with at(12):
            self.assertEqual(self.mode(), 'full')

    def test_away_game_switched_on_by_staff_is_limited(self):
        event = make_event(home_away='away')
        event.limited_menu = True
        event.save()
        with at(12):
            self.assertEqual(self.mode(), 'limited')

    def test_force_game_day_mode(self):
        site = SiteSettings.load()
        site.force_game_day_mode = True
        site.save()
        with at(12):
            self.assertEqual(self.mode(), 'limited')

    def test_force_full_menu_beats_everything(self):
        make_event(game_time=None)
        site = SiteSettings.load()
        site.force_full_menu = True
        site.force_game_day_mode = True
        site.save()
        with at(12):
            self.assertEqual(self.mode(), 'full')
