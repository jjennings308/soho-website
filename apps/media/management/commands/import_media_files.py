"""
Management command to import existing image files from disk into MediaItem records.

Usage:
    python manage.py import_media_files
    python manage.py import_media_files --publish          # set is_published=True immediately
    python manage.py import_media_files --dir=gallery/sandwiches 10-4-24

Scans MEDIA_ROOT/gallery/ (or the directory specified by --dir, relative to MEDIA_ROOT)
recursively for image files. For each file not already tracked by a MediaItem record,
creates a new record with:
    owner_type='staff'
    is_published=False (or True if --publish is passed)
    is_approved=True
    is_flagged=False

File path is stored as-is, relative to MEDIA_ROOT — files are never moved or renamed.

Deduplication: by `file` field value (the relative path). Running again will skip
files already in the database.

Name generation: strips the file extension, replaces underscores and hyphens with
spaces, then title-cases the result. Staff can rename from the staff portal.

Non-image files (xlsx, pdf, etc.) are silently skipped.
"""

import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.media.models import MediaItem

# Supported image extensions (case-insensitive)
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.avif', '.bmp', '.tiff', '.tif'}

DEFAULT_SCAN_DIR = 'gallery'  # relative to MEDIA_ROOT

# Subdirectories (relative to MEDIA_ROOT) that the importer should never touch.
# gallery/deleted holds files archived by the staff delete action pending review.
SKIP_SUBDIRS = {
    Path('gallery') / 'deleted',
}


def filename_to_name(filename: str) -> str:
    """
    Convert a bare filename (no extension) to a human-readable display name.
    'IMG_9218'               → 'Img 9218'
    'Reuben Close up'        → 'Reuben Close Up'
    'Cuban-Close-up-4'       → 'Cuban Close Up 4'
    'burger hero shot'       → 'Burger Hero Shot'
    """
    stem = Path(filename).stem
    name = stem.replace('_', ' ').replace('-', ' ')
    # Collapse runs of spaces that may result from __ or -- in filenames
    name = ' '.join(name.split())
    return name.title()


class Command(BaseCommand):
    help = 'Import image files from disk into MediaItem records (safe to re-run).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--publish',
            action='store_true',
            default=False,
            help='Set is_published=True on all imported records (default: False).',
        )
        parser.add_argument(
            '--dir',
            dest='scan_dir',
            default=DEFAULT_SCAN_DIR,
            help=(
                'Directory to scan, relative to MEDIA_ROOT '
                f'(default: "{DEFAULT_SCAN_DIR}").'
            ),
        )

    def handle(self, *args, **options):
        publish     = options['publish']
        scan_subdir = options['scan_dir'].lstrip('/')

        media_root = Path(settings.MEDIA_ROOT)
        scan_path  = media_root / scan_subdir

        if not scan_path.exists():
            raise CommandError(f'Directory does not exist: {scan_path}')
        if not scan_path.is_dir():
            raise CommandError(f'Not a directory: {scan_path}')

        self.stdout.write(f'Scanning: {scan_path}')
        self.stdout.write(f'Publish immediately: {publish}')
        self.stdout.write('')

        # Collect all image files under the scan directory
        image_files = sorted(
            p for p in scan_path.rglob('*')
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
        )

        self.stdout.write(f'Found {len(image_files)} image file(s).')

        # Build a set of already-tracked relative paths for fast dedup
        existing_paths = set(
            MediaItem.objects.values_list('file', flat=True)
        )

        created_count = 0
        skipped_count = 0

        for abs_path in image_files:
            # Path stored in DB is relative to MEDIA_ROOT
            rel_path = abs_path.relative_to(media_root)
            rel_path_str = str(rel_path)  # e.g. "gallery/burgers/Burger_Hero.jpg"

            # Skip protected subdirectories (e.g. gallery/deleted)
            if any(
                rel_path.parts[:len(skip.parts)] == skip.parts
                for skip in SKIP_SUBDIRS
            ):
                skipped_count += 1
                continue

            if rel_path_str in existing_paths:
                skipped_count += 1
                continue

            name = filename_to_name(abs_path.name)

            MediaItem.objects.create(
                name         = name,
                owner_type   = 'staff',
                media_type   = 'image',
                file         = rel_path_str,
                is_published = publish,
                is_approved  = True,
                is_flagged   = False,
            )
            self.stdout.write(f'  + {rel_path_str}')
            created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'\nDone. {created_count} imported, {skipped_count} already existed.'
            )
        )
