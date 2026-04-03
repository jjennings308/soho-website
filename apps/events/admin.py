from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.contrib import messages
import csv
import io
from django import forms
from django.shortcuts import render, redirect

from .models import EventDay


class CSVImportForm(forms.Form):
    csv_file = forms.FileField(
        label='CSV File',
        help_text=(
            'Required columns: date (YYYY-MM-DD), event_type. '
            'Optional columns: label, team, game_time (HH:MM), '
            'limited_menu (true/false), limited_menu_lead_hours.'
        )
    )


@admin.register(EventDay)
class EventDayAdmin(admin.ModelAdmin):
    list_display = [
        'date',
        'event_type_badge',
        'display_label',
        'team',
        'game_time',
        'limited_menu',
        'is_active',
        'menu_mode_status',
    ]
    list_filter = [
        'event_type',
        'team',
        'limited_menu',
        'is_active',
    ]
    list_editable = [
        'is_active',
        'limited_menu',
    ]
    search_fields = ['label', 'date']
    date_hierarchy = 'date'
    ordering = ['date', 'game_time']

    fieldsets = (
        ('Event', {
            'fields': ('date', 'event_type', 'label', 'is_active'),
        }),
        ('Game Details', {
            'fields': ('team', 'game_time', 'limited_menu_lead_hours'),
            'description': (
                'Complete these fields for game day events. '
                'game_time is used to calculate when limited menu activates.'
            ),
        }),
        ('Menu Behavior', {
            'fields': ('limited_menu',),
        }),
    )

    actions = ['mark_active', 'mark_inactive', 'mark_limited_menu', 'mark_full_menu']
    change_list_template = 'admin/events/eventday/change_list.html'

    # ── Display helpers ───────────────────────────────────────────────────────

    @admin.display(description='Type')
    def event_type_badge(self, obj):
        colors = {
            'game':          '#1d6fa5',
            'private_party': '#7c3aed',
            'live_music':    '#065f46',
            'holiday':       '#b45309',
            'other':         '#6b7280',
        }
        color = colors.get(obj.event_type, '#6b7280')
        return format_html(
            '<span style="'
            'background:{};color:#fff;padding:2px 8px;'
            'border-radius:4px;font-size:11px;font-weight:500'
            '">{}</span>',
            color,
            obj.get_event_type_display(),
        )

    @admin.display(description='Menu mode')
    def menu_mode_status(self, obj):
        today = timezone.localdate()
        if obj.date != today:
            return '—'
        if obj.is_limited_menu_active:
            return format_html(
                '<span style="color:#b91c1c;font-weight:500;">⚠ Limited</span>'
            )
        return format_html(
            '<span style="color:#166534;">✓ Full</span>'
        )

    # ── Bulk actions ──────────────────────────────────────────────────────────

    @admin.action(description='Mark selected events as active')
    def mark_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} event(s) marked active.', messages.SUCCESS)

    @admin.action(description='Mark selected events as inactive')
    def mark_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} event(s) marked inactive.', messages.SUCCESS)

    @admin.action(description='Enable limited menu for selected events')
    def mark_limited_menu(self, request, queryset):
        updated = queryset.update(limited_menu=True)
        self.message_user(request, f'{updated} event(s) set to limited menu.', messages.SUCCESS)

    @admin.action(description='Disable limited menu for selected events')
    def mark_full_menu(self, request, queryset):
        updated = queryset.update(limited_menu=False)
        self.message_user(request, f'{updated} event(s) set to full menu.', messages.SUCCESS)

    # ── CSV import ────────────────────────────────────────────────────────────

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom = [
            path('import-csv/', self.admin_site.admin_view(self.import_csv_view), name='events_eventday_import_csv'),
        ]
        return custom + urls

    def import_csv_view(self, request):
        if request.method == 'POST':
            form = CSVImportForm(request.POST, request.FILES)
            if form.is_valid():
                created, skipped, errors = self._process_csv(request.FILES['csv_file'])
                if created:
                    self.message_user(
                        request,
                        f'Successfully imported {created} event(s). '
                        f'{skipped} skipped (already exist). '
                        f'{errors} error(s).',
                        messages.SUCCESS if not errors else messages.WARNING,
                    )
                else:
                    self.message_user(request, 'No events imported.', messages.WARNING)
                return redirect('..')
        else:
            form = CSVImportForm()

        context = {
            **self.admin_site.each_context(request),
            'form': form,
            'title': 'Import Event Schedule (CSV)',
            'opts': self.model._meta,
        }
        return render(request, 'admin/events/eventday/csv_import.html', context)

    def _process_csv(self, csv_file):
        created = skipped = errors = 0
        try:
            decoded = csv_file.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(decoded))
            for row in reader:
                try:
                    date_str = row.get('date', '').strip()
                    event_type = row.get('event_type', 'game').strip()
                    if not date_str:
                        errors += 1
                        continue
                    from datetime import date
                    event_date = date.fromisoformat(date_str)

                    # Parse optional fields
                    game_time = None
                    if row.get('game_time', '').strip():
                        from datetime import time
                        h, m = row['game_time'].strip().split(':')
                        game_time = time(int(h), int(m))

                    limited_menu_str = row.get('limited_menu', 'true').strip().lower()
                    limited_menu = limited_menu_str not in ('false', '0', 'no')

                    lead_hours = int(row.get('limited_menu_lead_hours', 2) or 2)

                    obj, was_created = EventDay.objects.get_or_create(
                        date=event_date,
                        event_type=event_type,
                        defaults={
                            'label':                   row.get('label', '').strip(),
                            'team':                    row.get('team', '').strip(),
                            'game_time':               game_time,
                            'limited_menu':            limited_menu,
                            'limited_menu_lead_hours': lead_hours,
                        }
                    )
                    if was_created:
                        created += 1
                    else:
                        skipped += 1
                except Exception:
                    errors += 1
        except Exception:
            errors += 1
        return created, skipped, errors
