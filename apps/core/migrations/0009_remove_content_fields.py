from django.db import migrations


class Migration(migrations.Migration):
    """
    Schema migration: removes content copy fields from SiteSettings.

    Run AFTER 0008_migrate_content_to_slots which preserves existing
    field values as active ContentBlocks.

    Fields removed:
        - tagline             → content slot: 'site_tagline'
        - description         → content slot: 'site_description'
        - hours_text          → content slot: 'hours_text'
        - short_about_text    → content slot: 'about_short'
        - catering_text       → content slot: 'catering_body'
        - maintenance_message → content slot: 'maintenance_message'
    """

    dependencies = [
        ('core', '0008_migrate_content_to_slots'),
    ]

    operations = [
        migrations.RemoveField(model_name='sitesettings', name='tagline'),
        migrations.RemoveField(model_name='sitesettings', name='description'),
        migrations.RemoveField(model_name='sitesettings', name='hours_text'),
        migrations.RemoveField(model_name='sitesettings', name='short_about_text'),
        migrations.RemoveField(model_name='sitesettings', name='catering_text'),
        migrations.RemoveField(model_name='sitesettings', name='maintenance_message'),
    ]
