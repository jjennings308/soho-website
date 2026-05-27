from django.contrib import admin
from .models import MediaCategory, MediaItem

# Full admin registration happens in Step 5 (staff portal media section).
# These stubs give superuser emergency access in the Django admin.

@admin.register(MediaCategory)
class MediaCategoryAdmin(admin.ModelAdmin):
    list_display  = ['name', 'display_order', 'is_published', 'is_gallery_visible']
    list_editable = ['display_order', 'is_published', 'is_gallery_visible']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(MediaItem)
class MediaItemAdmin(admin.ModelAdmin):
    list_display  = ['name', 'category', 'owner_type', 'media_type', 'is_published', 'is_approved']
    list_filter   = ['owner_type', 'media_type', 'is_published', 'is_approved', 'category']
    search_fields = ['name', 'alt_text', 'caption']
    readonly_fields = ['slug']
