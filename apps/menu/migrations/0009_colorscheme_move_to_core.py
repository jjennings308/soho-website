from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0032_move_colorscheme_from_menu'),
        ('menu', '0008_rename_promocolorscheme_to_colorscheme'),
    ]

    operations = [
        # Update the FK on Menu to point at core.ColorScheme in Django state.
        migrations.AlterField(
            model_name='menu',
            name='color_scheme',
            field=models.ForeignKey(
                'core.ColorScheme',
                blank=True,
                help_text='Color scheme for this menu. Leave blank to use the default scheme.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='menus',
            ),
        ),
        # Remove ColorScheme from menu's state only — the table is already gone.
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name='ColorScheme'),
            ],
        ),
    ]
