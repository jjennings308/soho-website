from datetime import date, time

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.events import importers as ei
from apps.events.models import EventDay
from apps.menu import importers as im
from apps.staff.permissions import MANAGER_GROUP

User = get_user_model()


def parse(text):
    return im.parse(ei.KIND, text)


def apply(text):
    return im.apply(ei.KIND, text)


class EventImportTests(TestCase):
    def test_new_events_with_labels_codes_and_12_hour_times(self):
        result = apply(
            'date,event_type,label,team,home_away,game_time\n'
            '4/3/2027,Game Day,Pirates vs. Cubs,Pittsburgh Pirates,home,6:40 PM\n'
            '4/10/2027,live_music,Jazz Night,,,20:00\n'
        )
        self.assertEqual(result.count('new'), 2)
        game = EventDay.objects.get(label='Pirates vs. Cubs')
        self.assertEqual((game.date, game.event_type, game.team), (date(2027, 4, 3), 'game', 'pirates'))
        self.assertEqual(game.game_time, time(18, 40))
        self.assertTrue(game.limited_menu)                 # home-game default
        self.assertEqual(EventDay.objects.get(label='Jazz Night').game_time, time(20, 0))

    def test_reupload_without_id_updates_instead_of_duplicating(self):
        text = 'date,event_type,label,team,game_time\n4/3/2027,game,Pirates vs. Cubs,pirates,18:40\n'
        apply(text)
        self.assertEqual(parse(text).count('unchanged'), 1)
        result = apply(text.replace('18:40', '19:05'))
        self.assertEqual(result.count('update'), 1)
        self.assertEqual(EventDay.objects.get().game_time, time(19, 5))

    def test_id_finds_the_event_so_its_date_can_change(self):
        event = EventDay.objects.create(date=date(2027, 4, 3), label='Opener')
        result = apply(f'id,date\n{event.pk},4/4/2027\n')
        self.assertEqual(result.rows[0].changes, {'date': ('4/3/2027', '4/4/2027')})
        event.refresh_from_db()
        self.assertEqual(event.date, date(2027, 4, 4))
        self.assertEqual(event.label, 'Opener')             # blank cells keep

    def test_unknown_id_and_missing_date_are_errors(self):
        result = parse('id,date,label\n999,,Ghost\n,,No date\n')
        self.assertFalse(result.ok)
        self.assertIn('no event with id 999', result.rows[0].errors[0])
        self.assertIn('date: needed', result.rows[1].errors[0])

    def test_bad_cells_refuse_the_whole_file(self):
        result = parse('date,event_type,game_time\n4/3/2027,game,\n13/3/2027,party,25:00\n')
        errors = ' '.join(result.rows[1].errors)
        self.assertIn('not a date', errors)
        with self.assertRaises(im.ImportRefused):
            apply('date,event_type\n4/3/2027,game\n4/5/2027,party\n')
        self.assertFalse(EventDay.objects.exists())

    def test_explicit_limited_menu_beats_the_away_game_default(self):
        result = apply(
            'date,label,team,home_away,limited_menu\n'
            '9/12/2027,Watch party,steelers,away,yes\n'
            '9/19/2027,Away game,steelers,away,\n'
        )
        self.assertIn('as given', result.rows[0].notes[0])
        self.assertIn('away-game default', result.rows[1].notes[0])
        self.assertTrue(EventDay.objects.get(label='Watch party').limited_menu)
        self.assertFalse(EventDay.objects.get(label='Away game').limited_menu)

    def test_two_rows_for_one_event_clash(self):
        event = EventDay.objects.create(date=date(2027, 4, 3), label='Opener')
        result = parse(f'id,date,label\n{event.pk},,\n,4/3/2027,Opener\n')
        self.assertIn('same record as line 2', result.rows[1].errors[0])

    def test_export_round_trips_with_no_changes(self):
        EventDay.objects.create(date=date(2027, 4, 3), label='Opener', team='pirates',
                                home_away='home', game_time=time(13, 5))
        EventDay.objects.create(date=date(2027, 5, 1), event_type='holiday', is_active=False)
        text = im.export_csv(ei.KIND)
        self.assertIn('4/3/2027', text)
        self.assertIn('13:05', text)
        result = parse(text)
        self.assertTrue(result.ok, [r.errors for r in result.rows])
        self.assertEqual(result.count('unchanged'), 2)

    def test_template_has_header_and_example(self):
        lines = im.template_csv(ei.KIND).lstrip('﻿').splitlines()
        self.assertTrue(lines[0].startswith('id,date,event_type'))
        self.assertIn('Pirates vs. Cubs', lines[1])


class EventImportPortalTests(TestCase):
    def setUp(self):
        manager = User.objects.create_user('mgr', password='x', is_staff=True)
        manager.groups.add(Group.objects.get(name=MANAGER_GROUP))
        self.manager = manager

    def test_events_page_links_to_import_for_managers_only(self):
        link = reverse('staff:menu_import') + '?kind=events'
        self.client.force_login(User.objects.create_user('viewer', password='x', is_staff=True))
        self.assertNotContains(self.client.get(reverse('staff:events')), link)
        self.assertEqual(self.client.get(link).status_code, 403)
        self.client.force_login(self.manager)
        self.assertContains(self.client.get(reverse('staff:events')), link)
        response = self.client.get(link)
        self.assertRegex(response.content.decode(), r'value="events" x-model="kind" checked')

    def test_upload_preview_confirm(self):
        self.client.force_login(self.manager)
        upload = SimpleUploadedFile('events.csv', b'date,label\n4/3/2027,Opener\n', content_type='text/csv')
        response = self.client.post(reverse('staff:menu_import'), {'kind': 'events', 'file': upload}, follow=True)
        self.assertContains(response, 'Opener')
        self.assertFalse(EventDay.objects.exists())
        response = self.client.post(reverse('staff:menu_import_preview'), {'action': 'confirm'}, follow=True)
        self.assertRedirects(response, reverse('staff:events'))
        self.assertContains(response, 'Imported events.csv: 1 added')
        self.assertTrue(EventDay.objects.filter(label='Opener').exists())

    def test_template_and_export_download(self):
        self.client.force_login(self.manager)
        for name in ('staff:menu_import_template', 'staff:menu_export'):
            response = self.client.get(reverse(name, args=['events']))
            self.assertEqual(response.status_code, 200)
            self.assertIn('id,date,event_type', response.content.decode('utf-8-sig'))
