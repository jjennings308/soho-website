from django.contrib import admin
from django.utils.html import format_html
from .models import Theme, SiteSettings


@admin.register(Theme)
class ThemeAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'theme_directory', 'primary_font', 'is_active', 'current_theme_radio', 'created_at']
    list_editable = ('is_active',)
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']

    def current_theme_radio(self, obj):
        """
        Renders a radio button for each row. Only enabled for active themes.
        Selecting one and saving the changelist sets SiteSettings.active_theme.
        """
        site = SiteSettings.load()
        is_current = site.active_theme_id == obj.pk

        if obj.is_active:
            return format_html(
                '<input type="radio" name="_current_theme" value="{}" {}>',
                obj.pk,
                'checked' if is_current else '',
            )
        else:
            # Greyed out — must be active before it can be set as current
            return format_html(
                '<input type="radio" name="_current_theme" value="{}" disabled '
                'title="Activate this theme first">',
                obj.pk,
            )

    current_theme_radio.short_description = 'Current'
    current_theme_radio.allow_tags = True

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context)

        if request.method == 'POST':
            # Handle current theme radio selection
            selected_pk = request.POST.get('_current_theme')
            if selected_pk:
                try:
                    selected_theme = Theme.objects.get(pk=int(selected_pk), is_active=True)
                    site = SiteSettings.load()
                    if site.active_theme_id != selected_theme.pk:
                        site.active_theme = selected_theme
                        site.save()
                        self.message_user(
                            request,
                            f'"{selected_theme.name}" is now the current site theme.',
                        )
                except Theme.DoesNotExist:
                    self.message_user(
                        request,
                        "Could not set current theme — the selected theme is not active.",
                        level='error',
                    )

        return response


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    fieldsets = (
        ('Restaurant Information', {
            'fields': ('restaurant_name', 'logo', 'favicon')
        }),
        ('Contact Information', {
            'fields': ('phone', 'email', 'address_line1', 'address_line2', 'city', 'state', 'zip_code', 'country')
        }),
        ('Social Media', {
            'fields': ('facebook_url', 'instagram_url', 'twitter_url', 'yelp_url'),
            'classes': ('collapse',)
        }),
        ('Theme', {
            'fields': ('active_theme',),
            'description': (
                'The theme currently in use on the site. Only active themes are available. '
                'Colors are brand constants and are not affected by theme selection. '
                'You can also set the current theme directly from the Themes list.'
            )
        }),
        ('SEO Settings', {
            'fields': ('meta_description', 'meta_keywords'),
            'classes': ('collapse',)
        }),
        ('Maintenance', {
            'fields': ('maintenance_mode',),
            'classes': ('collapse',)
        }),
    )
