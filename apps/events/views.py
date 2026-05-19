import calendar
from datetime import date

from django.shortcuts import render
from django.utils import timezone

from .models import EventDay


def events_calendar(request):
    today = timezone.localdate()

    month_str = request.GET.get('month', '')
    try:
        year, month = map(int, month_str.split('-'))
        current_month = date(year, month, 1)
    except (ValueError, AttributeError):
        current_month = today.replace(day=1)

    if current_month.month == 1:
        prev_month = date(current_month.year - 1, 12, 1)
    else:
        prev_month = date(current_month.year, current_month.month - 1, 1)

    if current_month.month == 12:
        next_month = date(current_month.year + 1, 1, 1)
    else:
        next_month = date(current_month.year, current_month.month + 1, 1)

    last_day = calendar.monthrange(current_month.year, current_month.month)[1]
    month_end = date(current_month.year, current_month.month, last_day)

    events_qs = list(
        EventDay.objects.filter(
            date__gte=current_month,
            date__lte=month_end,
            is_active=True,
        ).order_by('date', 'game_time')
    )

    events_by_date = {}
    for event in events_qs:
        events_by_date.setdefault(event.date, []).append(event)

    # Sunday-first calendar grid
    cal = calendar.Calendar(firstweekday=6)
    weeks = []
    for week in cal.monthdatescalendar(current_month.year, current_month.month):
        week_days = []
        for d in week:
            in_month = d.month == current_month.month
            week_days.append({
                'date': d,
                'in_month': in_month,
                'is_today': d == today,
                'events': events_by_date.get(d, []) if in_month else [],
            })
        weeks.append(week_days)

    # Agenda: upcoming from today if current month, otherwise all in month
    is_current_month = (current_month.year == today.year and current_month.month == today.month)
    if is_current_month:
        agenda_events = [e for e in events_qs if e.date >= today]
    else:
        agenda_events = events_qs

    # Group agenda events by date for template rendering
    agenda_by_date = {}
    for event in agenda_events:
        agenda_by_date.setdefault(event.date, []).append(event)
    agenda_groups = [
        {'date': d, 'events': evts, 'is_today': d == today}
        for d, evts in agenda_by_date.items()
    ]

    seen_legend = set()
    legend_items = []
    for event in events_qs:
        key = (event.event_type, event.home_away)
        if key not in seen_legend:
            seen_legend.add(key)
            legend_items.append({'label': event.type_label, 'color': event.color})

    context = {
        'current_month': current_month,
        'prev_month': prev_month,
        'next_month': next_month,
        'today': today,
        'weeks': weeks,
        'agenda_groups': agenda_groups,
        'agenda_events': agenda_events,
        'all_month_events': events_qs,
        'legend_items': legend_items,
        'week_headers': ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
    }
    return render(request, 'events/calendar.html', context)
