from django.contrib import admin
from django.utils.html import format_html
from .models import ContentSlot, ContentBlock


class ContentBlockInline(admin.StackedInline):
    model = ContentBlock
    extra = 1
    fields = ['label', 'body', 'image', 'is_active', 'updated_at']
    readonly_fields = ['updated_at']
    ordering = ['-updated_at']


@admin.register(ContentSlot)
class ContentSlotAdmin(admin.ModelAdmin):
    list_display = ['slug', 'label', 'active_block_label', 'block_count']
    search_fields = ['slug', 'label']
    readonly_fields = ['slug']  # prevent slug changes after templates depend on it
    inlines = [ContentBlockInline]

    def active_block_label(self, obj):
        block = obj.get_active_block()
        if block:
            return format_html('<span style="color: #2d7a2d;">&#10003; {}</span>', block.label or str(block.created_at.date()))
        return format_html('<span style="color: #999;">— none active —</span>')
    active_block_label.short_description = 'Active Block'

    def block_count(self, obj):
        count = obj.blocks.count()
        return count
    block_count.short_description = '# Versions'

    def get_readonly_fields(self, request, obj=None):
        # Allow slug to be set on creation, lock it after
        if obj:
            return self.readonly_fields
        return []


@admin.register(ContentBlock)
class ContentBlockAdmin(admin.ModelAdmin):
    """
    Standalone view for browsing all blocks across slots.
    Primary editing is done via ContentSlotAdmin inlines.
    """
    list_display = ['__str__', 'slot', 'is_active', 'updated_at']
    list_filter = ['slot', 'is_active']
    search_fields = ['label', 'slot__slug', 'slot__label']
    readonly_fields = ['created_at', 'updated_at']
    fields = ['slot', 'label', 'body', 'image', 'is_active', 'created_at', 'updated_at']
