from django.db import migrations


class Migration(migrations.Migration):
    """
    The original migrations (0014, 0017) created image as a FK (image_id bigint).
    Those migrations were edited to use ImageField instead, but the DB still has
    the old columns. This migration fixes the actual database to match.
    """

    dependencies = [
        ('core', '0034_alter_panelside_image_fallback_url'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE core_banner DROP COLUMN IF EXISTS image_id;
                        ALTER TABLE core_banner ADD COLUMN IF NOT EXISTS image varchar(100) NOT NULL DEFAULT '';
                        ALTER TABLE core_banner ADD COLUMN IF NOT EXISTS image_alt varchar(255) NOT NULL DEFAULT '';

                        ALTER TABLE core_panelside DROP COLUMN IF EXISTS image_id;
                        ALTER TABLE core_panelside ADD COLUMN IF NOT EXISTS image varchar(100) NOT NULL DEFAULT '';
                        ALTER TABLE core_panelside ADD COLUMN IF NOT EXISTS image_alt varchar(255) NOT NULL DEFAULT '';
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[],
        ),
    ]
