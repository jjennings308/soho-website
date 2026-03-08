from django.db import migrations


# Mapping of: (slot_slug, slot_label, slot_description, sitesettings_field_name)
CONTENT_FIELD_MAP = [
    (
        'site_tagline',
        'Site — Tagline',
        'Short tagline used in the site header and meta tags.',
        'tagline',
    ),
    (
        'site_description',
        'Site — Description',
        'General restaurant description. Used on the home page or about section.',
        'description',
    ),
    (
        'hours_text',
        'Hours — Text',
        'Operating hours displayed in the footer, contact page, or sidebar.',
        'hours_text',
    ),
    (
        'about_short',
        'About — Short Text',
        'Brief about blurb used in footers, sidebars, or home page callouts.',
        'short_about_text',
    ),
    (
        'catering_body',
        'Catering — Body Text',
        'Main copy for the catering section or page.',
        'catering_text',
    ),
    (
        'maintenance_message',
        'Maintenance — Message',
        'Message shown to visitors when the site is in maintenance mode.',
        'maintenance_message',
    ),
]


def migrate_content_fields_forward(apps, schema_editor):
    """
    Reads existing content from SiteSettings and creates a ContentSlot +
    active ContentBlock for each field that has a non-empty value.
    Slots are created regardless — blocks are only created if content exists.
    """
    SiteSettings = apps.get_model('core', 'SiteSettings')
    ContentSlot = apps.get_model('content', 'ContentSlot')
    ContentBlock = apps.get_model('content', 'ContentBlock')

    try:
        settings = SiteSettings.objects.get(pk=1)
    except SiteSettings.DoesNotExist:
        # No settings row yet; just ensure slots exist for future use
        for slug, label, description, _ in CONTENT_FIELD_MAP:
            ContentSlot.objects.get_or_create(
                slug=slug,
                defaults={'label': label, 'description': description}
            )
        return

    for slug, label, description, field_name in CONTENT_FIELD_MAP:
        slot, _ = ContentSlot.objects.get_or_create(
            slug=slug,
            defaults={'label': label, 'description': description}
        )

        value = getattr(settings, field_name, '').strip()
        if value:
            ContentBlock.objects.create(
                slot=slot,
                label=f'Migrated from SiteSettings ({field_name})',
                body=value,
                is_active=True,
            )


def migrate_content_fields_backward(apps, schema_editor):
    """
    Reverse: copies the active ContentBlock body back into SiteSettings fields.
    Only restores content if the SiteSettings row exists.
    """
    SiteSettings = apps.get_model('core', 'SiteSettings')
    ContentSlot = apps.get_model('content', 'ContentSlot')

    try:
        settings = SiteSettings.objects.get(pk=1)
    except SiteSettings.DoesNotExist:
        return

    for slug, _, _, field_name in CONTENT_FIELD_MAP:
        try:
            slot = ContentSlot.objects.get(slug=slug)
            block = slot.blocks.filter(is_active=True).first()
            if block:
                setattr(settings, field_name, block.body)
        except ContentSlot.DoesNotExist:
            pass

    settings.save()


class Migration(migrations.Migration):
    """
    Data migration: copies content fields from SiteSettings into
    ContentSlot / ContentBlock before the schema migration drops the columns.
    """

    dependencies = [
        ('core', '0007_remove_themestyle_promo_accent_color_and_more'),
        ('content', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            migrate_content_fields_forward,
            reverse_code=migrate_content_fields_backward,
        ),
    ]
