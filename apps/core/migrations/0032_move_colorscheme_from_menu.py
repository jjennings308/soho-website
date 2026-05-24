from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0031_sitepopup_primary_color'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            # Rename the existing table so data is preserved.
            database_operations=[
                migrations.RunSQL(
                    sql='ALTER TABLE menu_colorscheme RENAME TO core_colorscheme;',
                    reverse_sql='ALTER TABLE core_colorscheme RENAME TO menu_colorscheme;',
                ),
            ],
            # Tell Django's state that core now owns ColorScheme.
            state_operations=[
                migrations.CreateModel(
                    name='ColorScheme',
                    fields=[
                        ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('updated_at', models.DateTimeField(auto_now=True)),
                        ('name', models.CharField(
                            help_text="Internal label, e.g. 'Black & Gold', 'Holiday Red'.",
                            max_length=100, unique=True)),
                        ('primary_color', models.CharField(
                            blank=True, help_text='Main color (hex, e.g. #ffb612).', max_length=30)),
                        ('accent_color', models.CharField(
                            blank=True, help_text='Secondary / highlight color (hex).', max_length=30)),
                        ('text_color', models.CharField(
                            blank=True, help_text='Text color (hex).', max_length=30)),
                        ('bg_color', models.CharField(
                            blank=True, help_text='Background color (hex).', max_length=30)),
                        ('is_default', models.BooleanField(
                            default=False,
                            help_text=(
                                'Use this scheme when a menu has no scheme assigned. '
                                'Saving a new default clears the flag on the previous one.'
                            ))),
                    ],
                    options={
                        'verbose_name': 'Color Scheme',
                        'verbose_name_plural': 'Color Schemes',
                        'ordering': ['-is_default', 'name'],
                    },
                ),
            ],
        ),
    ]
