"""
Seed a handful of sample EventDay records for development.
Safe to re-run — uses get_or_create throughout.

Usage:
    python manage.py seed_events
"""
from datetime import date, time, timedelta
from django.core.management.base import BaseCommand
from apps.events.models import EventDay


SAMPLE_EVENTS = [
    # (date_offset_days, event_type, label, team, game_time, limited_menu, lead_hours)
    (0,   'game',          'Pirates vs. Cubs',         'pirates',  time(18, 40), True,  2),
    (1,   'game',          'Pirates vs. Cubs',         'pirates',  time(12, 35), True,  2),
    (3,   'game',          'Pirates vs. Cardinals',    'pirates',  time(18, 40), True,  2),
    (5,   'private_party', 'Private Event — Patio',    '',         None,         True,  0),
    (7,   'live_music',    'Live Jazz Night',           '',         time(19, 0),  False, 0),
    (14,  'game',          'Steelers vs. Ravens',       'steelers', time(13, 0),  True,  3),
    (21,  'holiday',       'Independence Day',          '',         None,         False, 0),
]


class Command(BaseCommand):
    help = 'Seed sample EventDay records for development.'

    def handle(self, *args, **options):
        today = date.today()
        created_count = 0
        skipped_count = 0

        for offset, etype, label, team, gtime, limited, lead in SAMPLE_EVENTS:
            event_date = today + timedelta(days=offset)
            obj, created = EventDay.objects.get_or_create(
                date=event_date,
                event_type=etype,
                defaults={
                    'label':                   label,
                    'team':                    team,
                    'game_time':               gtime,
                    'limited_menu':            limited,
                    'limited_menu_lead_hours': lead,
                    'is_active':               True,
                }
            )
            if created:
                created_count += 1
                self.stdout.write(f'  Created: {obj}')
            else:
                skipped_count += 1
                self.stdout.write(f'  Skipped (exists): {obj}')

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. {created_count} created, {skipped_count} skipped.'
        ))
