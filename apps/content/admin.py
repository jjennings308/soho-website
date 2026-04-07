import csv
import io
from django import forms
from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.utils.html import format_html, mark_safe
from .models import ContentGroup, ContentSlot, ContentBlock


# ---------------------------------------------------------------------------
# CSV import form
# ---------------------------------------------------------------------------

class ContentGroupCSVImportForm(forms.Form):
    csv_file = forms.FileField(
        label='CSV File',
        help_text=(
            'Required columns: type, slug, label. '
            'Optional columns: description, component_type, order. '
            'Rows with type="group" define groups; rows with type="slot" '
            'belong to the most recent group row above them.'
        )
    )


# ---------------------------------------------------------------------------
# ContentBlock inline — used under ContentSlot
# ---------------------------------------------------------------------------

class ContentBlockInline(admin.StackedInline):
    model = ContentBlock
    extra = 1
    fields = ['label', 'body', 'image', 'button_label', 'button_url', 'is_active', 'updated_at']
    readonly_fields = ['updated_at']
    ordering = ['-updated_at']


# ---------------------------------------------------------------------------
# ContentSlot inline — used under ContentGroup
# ---------------------------------------------------------------------------

class ContentSlotInline(admin.TabularInline):
    model = ContentSlot
    extra = 0
    fields = ['label', 'slug', 'component_type', 'order', 'active_block_summary']
    readonly_fields = ['active_block_summary']
    ordering = ['order', 'slug']
    show_change_link = True

    def active_block_summary(self, obj):
        if not obj.pk:
            return '—'
        block = obj.get_active_block()
        if block:
            label = block.label or str(block.created_at.date()) if block.created_at else 'active'
            return format_html('<span style="color: #2d7a2d;">&#10003; {}</span>', label)
        return mark_safe('<span style="color: #999;">no active block</span>')
    active_block_summary.short_description = 'Active Block'


# ---------------------------------------------------------------------------
# ContentGroup
# ---------------------------------------------------------------------------

@admin.register(ContentGroup)
class ContentGroupAdmin(admin.ModelAdmin):
    list_display = ['label', 'slug', 'slot_count', 'description_summary']
    search_fields = ['slug', 'label']
    inlines = [ContentSlotInline]
    change_list_template = 'admin/content/contentgroup/change_list.html'

    def get_prepopulated_fields(self, request, obj=None):
        if obj:
            return {}
        return {'slug': ('label',)}

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['slug']
        return []

    def slot_count(self, obj):
        return obj.slots.count()
    slot_count.short_description = '# Slots'

    def description_summary(self, obj):
        if obj.description:
            return obj.description[:80] + ('…' if len(obj.description) > 80 else '')
        return mark_safe('<span style="color: #999;">—</span>')
    description_summary.short_description = 'Description'

    # ── CSV import ────────────────────────────────────────────────────────────

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom = [
            path(
                'import-csv/',
                self.admin_site.admin_view(self.import_csv_view),
                name='content_contentgroup_import_csv',
            ),
        ]
        return custom + urls

    def import_csv_view(self, request):
        if request.method == 'POST':
            form = ContentGroupCSVImportForm(request.POST, request.FILES)
            if form.is_valid():
                groups_created, groups_skipped, slots_created, slots_skipped, errors = \
                    self._process_csv(request.FILES['csv_file'])

                summary = (
                    f'Groups: {groups_created} created, {groups_skipped} already existed. '
                    f'Slots: {slots_created} created, {slots_skipped} already existed.'
                )
                if errors:
                    self.message_user(
                        request,
                        f'{summary} {errors} row(s) skipped due to errors.',
                        messages.WARNING,
                    )
                else:
                    self.message_user(request, summary, messages.SUCCESS)
                return redirect('..')
        else:
            form = ContentGroupCSVImportForm()

        context = {
            **self.admin_site.each_context(request),
            'form': form,
            'title': 'Import Content Groups (CSV)',
            'opts': self.model._meta,
        }
        return render(request, 'admin/content/contentgroup/csv_import.html', context)

    def _process_csv(self, csv_file):
        groups_created = groups_skipped = slots_created = slots_skipped = errors = 0
        valid_component_types = {ct.value for ct in ContentSlot.ComponentType}
        current_group = None

        try:
            decoded = csv_file.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(decoded))

            for row in reader:
                row_type = row.get('type', '').strip().lower()
                slug = row.get('slug', '').strip()
                label = row.get('label', '').strip()
                description = row.get('description', '').strip()
                component_type = row.get('component_type', '').strip().lower()
                order_raw = row.get('order', '').strip()

                # Skip blank rows
                if not row_type and not slug:
                    continue

                # Validate required fields
                if not slug or not label or row_type not in ('group', 'slot'):
                    errors += 1
                    continue

                try:
                    if row_type == 'group':
                        group, created = ContentGroup.objects.get_or_create(
                            slug=slug,
                            defaults={'label': label, 'description': description}
                        )
                        current_group = group
                        if created:
                            groups_created += 1
                        else:
                            groups_skipped += 1

                    elif row_type == 'slot':
                        if current_group is None:
                            errors += 1
                            continue

                        if component_type and component_type not in valid_component_types:
                            errors += 1
                            continue

                        try:
                            order = int(order_raw) if order_raw else 0
                        except ValueError:
                            order = 0

                        slot, created = ContentSlot.objects.get_or_create(
                            slug=slug,
                            defaults={
                                'label': label,
                                'description': description,
                                'group': current_group,
                                'component_type': component_type,
                                'order': order,
                            }
                        )
                        if created:
                            slots_created += 1
                        else:
                            slots_skipped += 1

                except Exception:
                    errors += 1

        except Exception:
            errors += 1

        return groups_created, groups_skipped, slots_created, slots_skipped, errors


# ---------------------------------------------------------------------------
# ContentSlot
# ---------------------------------------------------------------------------

@admin.register(ContentSlot)
class ContentSlotAdmin(admin.ModelAdmin):
    list_display = ['label', 'slug', 'group_link', 'component_type', 'order', 'active_block_label', 'block_count']
    list_filter = ['group', 'component_type']
    search_fields = ['slug', 'label']
    inlines = [ContentBlockInline]
    ordering = ['group__slug', 'order', 'slug']

    fieldsets = (
        (None, {
            'fields': ('slug', 'label', 'description'),
        }),
        ('Group membership', {
            'fields': ('group', 'component_type', 'order'),
            'description': (
                'Assign this slot to a ContentGroup to make it part of a structured output '
                '(banner, panel, etc.). Leave blank to keep it as a standalone slot.'
            ),
        }),
    )

    def get_prepopulated_fields(self, request, obj=None):
        if obj:
            return {}
        return {'slug': ('label',)}

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['slug']
        return []

    def active_block_label(self, obj):
        block = obj.get_active_block()
        if block:
            label = block.label or str(block.created_at.date()) if block.created_at else 'active'
            return format_html('<span style="color: #2d7a2d;">&#10003; {}</span>', label)
        return mark_safe('<span style="color: #999;">— none —</span>')
    active_block_label.short_description = 'Active Block'

    def block_count(self, obj):
        return obj.blocks.count()
    block_count.short_description = '# Versions'

    def group_link(self, obj):
        if obj.group:
            url = f'/admin/content/contentgroup/{obj.group.pk}/change/'
            return format_html('<a href="{}">{}</a>', url, obj.group.label)
        return mark_safe('<span style="color: #999;">standalone</span>')
    group_link.short_description = 'Group'


# ---------------------------------------------------------------------------
# ContentBlock
# ---------------------------------------------------------------------------

@admin.register(ContentBlock)
class ContentBlockAdmin(admin.ModelAdmin):
    """
    Standalone view for browsing all blocks across all slots.
    Primary editing is done via ContentSlotAdmin inlines.
    """
    list_display = ['__str__', 'slot', 'is_active', 'updated_at']
    list_filter = ['slot__group', 'slot', 'is_active']
    search_fields = ['label', 'slot__slug', 'slot__label', 'slot__group__slug']
    readonly_fields = ['created_at', 'updated_at']
    fields = [
        'slot', 'label', 'body', 'image',
        'button_label', 'button_url',
        'is_active', 'created_at', 'updated_at',
    ]
