from django.contrib import admin
from django.utils.html import format_html

from .models import GalleryCategory, GalleryItem


@admin.register(GalleryCategory)
class GalleryCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'display_order', 'is_published', 'item_count']
    list_editable = ['display_order', 'is_published']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['display_order', 'name']

    def item_count(self, obj):
        return obj.items.filter(is_published=True).count()
    item_count.short_description = 'Published Items'


@admin.register(GalleryItem)
class GalleryItemAdmin(admin.ModelAdmin):
    list_display = ['thumbnail_preview', 'caption', 'category', 'menu_item', 'media_type', 'display_order', 'is_published']
    list_editable = ['display_order', 'is_published']
    list_filter = ['category', 'media_type', 'is_published']
    search_fields = ['caption', 'menu_item__name']
    readonly_fields = ['thumbnail_preview']
    ordering = ['category__display_order', 'display_order']
    autocomplete_fields = ['menu_item']

    def thumbnail_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:50px;width:70px;object-fit:cover;border-radius:2px;">',
                obj.image.url,
            )
        if obj.video_url:
            return format_html('<span style="color:#888;">&#9654; Video</span>')
        return '—'
    thumbnail_preview.short_description = 'Preview'
