from django.db import migrations

# Mirrors apps.staff.permissions.MANAGER_GROUP; migrations shouldn't import app code.
MANAGER_GROUP = 'Staff Manager'


def create_group(apps, schema_editor):
    apps.get_model('auth', 'Group').objects.get_or_create(name=MANAGER_GROUP)


def delete_group(apps, schema_editor):
    apps.get_model('auth', 'Group').objects.filter(name=MANAGER_GROUP).delete()


class Migration(migrations.Migration):
    """Create the Tier 1 group used by the staff portal (see apps/staff/permissions.py)."""

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(create_group, delete_group),
    ]
