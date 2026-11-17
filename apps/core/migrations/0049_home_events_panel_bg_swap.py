from django.db import migrations


def swap_home_events_background(apps, schema_editor):
    PanelSide = apps.get_model('core', 'PanelSide')
    PanelSide.objects.filter(slug='home-events-text', bg_color='white').update(
        bg_color='bg-secondary'
    )


def restore_home_events_background(apps, schema_editor):
    PanelSide = apps.get_model('core', 'PanelSide')
    PanelSide.objects.filter(slug='home-events-text', bg_color='bg-secondary').update(
        bg_color='white'
    )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0048_eventinquiry_spam_status'),
    ]

    operations = [
        migrations.RunPython(
            swap_home_events_background,
            restore_home_events_background,
        ),
    ]
