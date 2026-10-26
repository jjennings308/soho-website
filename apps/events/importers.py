"""
Events CSV import / export — the menu import engine (apps/menu/importers.py)
with one more kind, so the same cell rules, preview and confirm apply.

    result = importers.parse(KIND, csv_text)
    result = importers.apply(KIND, csv_text)

A row finds an existing event by `id` (written by export), else by the same
date + event_type + team + label. No match → a new event. Changing the date of
an existing event therefore needs its id, i.e. edit an export.
"""
from apps.menu import importers
from apps.menu.importers import CLEAR, CellError, Column as C, Kind

from .models import EventDay

NAME = 'events'
LABEL = 'Events'
DESCRIPTION = ('Calendar events: games, private parties, live music, holidays. '
               'Leave id blank for new events; keep it (from an export) to change an existing one.')


def _value(row, col, default=''):
    value = row.values.get(col, default)
    return default if value == CLEAR else value


def _find(kind, row):
    if 'id' in row.values:
        pk = row.values['id']
        if pk == CLEAR:
            raise CellError('id: leave it blank for a new event, or keep the exported id')
        event = EventDay.objects.filter(pk=pk).first()
        if event is None:
            raise CellError(f'id: no event with id {pk} — leave it blank to add a new event')
        return event
    day = _value(row, 'date')
    if not day:
        if row.raw.get('date'):
            return None                     # the unreadable date is reported
        raise CellError('date: needed for a new event (or give the id of an existing one)')
    matches = list(EventDay.objects.filter(
        date=importers.parse_date(day),
        event_type=_value(row, 'event_type', 'game'),
        team=_value(row, 'team'),
        label__iexact=_value(row, 'label'),
    )[:2])
    if len(matches) > 1:
        raise CellError('matches more than one event on that date — use the id column from an export')
    return matches[0] if matches else None


def _label(row):
    event = row.instance or EventDay()
    day = _value(row, 'date') or (importers.format_date(event.date) if event.date else '')
    if row.values.get('label') or not row.instance:
        event = EventDay(
            label=_value(row, 'label', event.label),
            event_type=_value(row, 'event_type', event.event_type),
            team=_value(row, 'team', event.team),
        )
    return f'{day} — {event.display_label}' if day else event.display_label


def _home_away(row):
    return _value(row, 'home_away', row.instance.home_away if row.instance else '')


def _check(result):
    """Say what a new game's limited menu will be (EventDay.save() defaults it by home/away)."""
    for row in result.rows:
        if row.errors or row.instance or _value(row, 'event_type', 'game') != 'game':
            continue
        side = _home_away(row)
        if side not in ('home', 'away'):
            continue
        default = 'yes' if side == 'home' else 'no'
        given = _value(row, 'limited_menu')
        if not given:
            row.notes.append(f"limited menu {'on' if default == 'yes' else 'off'} — the {side}-game default")
        elif given != default:
            row.notes.append(f"limited menu {'on' if given == 'yes' else 'off'} as given, "
                             f"although {side} games default to {'on' if default == 'yes' else 'off'}")


def _after_save(row):
    # EventDay.save() sets limited_menu on a new home/away game; a value the
    # file gives explicitly wins (e.g. an away-game watch party).
    given = _value(row, 'limited_menu')
    if row.action == 'new' and given and row.instance.limited_menu != (given == 'yes'):
        row.instance.limited_menu = given == 'yes'
        row.instance.save(update_fields=['limited_menu', 'updated_at'])


KIND = Kind(NAME, EventDay, [
    C('id', type='key'), C('date'), C('event_type'), C('label'), C('team'), C('home_away'),
    C('game_time'), C('limited_menu'), C('limited_menu_lead_hours'), C('is_active'),
], key=('date', 'event_type', 'team', 'label'), export_order=('date', 'game_time', 'pk'),
    find=_find, label=_label, check=_check, after_save=_after_save,
    example={'date': '4/3/2027', 'event_type': 'game', 'label': 'Pirates vs. Cubs', 'team': 'pirates',
             'home_away': 'home', 'game_time': '18:40', 'limited_menu': 'yes',
             'limited_menu_lead_hours': '2', 'is_active': 'yes'})
