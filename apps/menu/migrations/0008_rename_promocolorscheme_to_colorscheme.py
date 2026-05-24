from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('menu', '0007_replace_show_on_homepage_with_homepage_slot'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='PromoColorScheme',
            new_name='ColorScheme',
        ),
    ]
