from django.core.management.base import BaseCommand
from apps.content.models import ContentSlot


# Standard slots for SoHo Pittsburgh.
# Add new ones here freely — the command is idempotent (get_or_create).
# DO NOT rename slugs after templates depend on them.
STANDARD_SLOTS = [
    # -------------------------------------------------------------------------
    # Site-wide (previously SiteSettings fields)
    # -------------------------------------------------------------------------
    ('site_tagline',            'Site — Tagline',               'Short tagline used in the site header and meta tags'),
    ('site_description',        'Site — Description',           'General restaurant description used on the home page or about section'),
    ('maintenance_message',     'Maintenance — Message',        'Message shown to visitors when the site is in maintenance mode'),

    # -------------------------------------------------------------------------
    # Home page
    # -------------------------------------------------------------------------
    ('home_hero_heading',       'Home — Hero Heading',          'Large headline displayed over the hero image'),
    ('home_hero_subtext',       'Home — Hero Subtext',          'Tagline or short copy beneath the hero heading'),
    ('home_intro',              'Home — Intro Section',         'Brief welcome paragraph on the home page'),

    # -------------------------------------------------------------------------
    # About
    # -------------------------------------------------------------------------
    ('about_header',            'About — Header',               'Section heading for the About page or section'),
    ('about_short',             'About — Short Text',           'Brief about blurb used in footers, sidebars, or home page callouts'),
    ('about_body',              'About — Body Text',            'Main descriptive copy for the About section'),

    # -------------------------------------------------------------------------
    # Hours
    # -------------------------------------------------------------------------
    ('hours_text',              'Hours — Text',                 'Operating hours displayed in the footer, contact page, or sidebar'),

    # -------------------------------------------------------------------------
    # Menu
    # -------------------------------------------------------------------------
    ('menu_header',             'Menu — Header',                'Heading displayed at the top of the menu page'),
    ('menu_intro',              'Menu — Intro Text',            'Optional short intro above the menu items'),

    # -------------------------------------------------------------------------
    # Catering
    # -------------------------------------------------------------------------
    ('catering_header',         'Catering — Header',            'Heading for the catering section or page'),
    ('catering_body',           'Catering — Body Text',         'Main copy describing catering services — previously SiteSettings.catering_text'),
    ('catering_cta',            'Catering — Call to Action',    'Button label or short CTA text for catering inquiries'),

    # -------------------------------------------------------------------------
    # Reservations
    # -------------------------------------------------------------------------
    ('reservations_header',     'Reservations — Header',        'Heading for the reservations section'),
    ('reservations_body',       'Reservations — Body Text',     'Instructions or info about making reservations'),

    # -------------------------------------------------------------------------
    # Private Events
    # -------------------------------------------------------------------------
    ('private_events_header',   'Private Events — Header',      'Heading for private dining and event bookings'),
    ('private_events_body',     'Private Events — Body Text',   'Copy for private dining and event bookings'),

    # -------------------------------------------------------------------------
    # Footer
    # -------------------------------------------------------------------------
    ('footer_tagline',          'Footer — Tagline',             'Short tagline displayed in the footer'),
]


class Command(BaseCommand):
    help = 'Load standard content slots for SoHo Pittsburgh. Safe to re-run — existing slots are not modified.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all current slots without making changes',
        )

    def handle(self, *args, **options):
        if options['list']:
            slots = ContentSlot.objects.all().order_by('slug')
            if not slots.exists():
                self.stdout.write('No content slots found.')
                return
            for slot in slots:
                active = slot.get_active_block()
                active_label = f" → active: \"{active.label or 'unlabeled'}\"" if active else " → no active block"
                self.stdout.write(f"  {slot.slug:<30} {slot.label}{active_label}")
            return

        self.stdout.write(self.style.MIGRATE_HEADING('Loading standard content slots...'))
        created_count = 0
        skipped_count = 0

        for slug, label, description in STANDARD_SLOTS:
            slot, created = ContentSlot.objects.get_or_create(
                slug=slug,
                defaults={'label': label, 'description': description}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"  ✓ created  {slug}"))
                created_count += 1
            else:
                self.stdout.write(f"  – exists   {slug}")
                skipped_count += 1

        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(f'Done. {created_count} created, {skipped_count} already existed.')
        )
