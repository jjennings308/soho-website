"""
Create GalleryItem records for image files already on disk in media/gallery/.

Skips files that already have a matching GalleryItem. Leaves category unset
so items can be assigned in the admin afterward. Sets is_published=False so
nothing appears on the public site until you're ready.

Usage:
    python manage.py import_gallery_images
    python manage.py import_gallery_images --publish   # set is_published=True immediately
"""
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from apps.gallery.models import GalleryItem


GALLERY_SUBDIR = 'gallery'
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}


class Command(BaseCommand):
    help = 'Import existing gallery images from media/gallery/ into the database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--publish',
            action='store_true',
            help='Set is_published=True on imported items (default: False).',
        )

    def handle(self, *args, **options):
        publish = options['publish']
        gallery_dir = os.path.join(settings.MEDIA_ROOT, GALLERY_SUBDIR)

        if not os.path.isdir(gallery_dir):
            self.stderr.write(self.style.ERROR(f'Directory not found: {gallery_dir}'))
            return

        existing = set(
            GalleryItem.objects.values_list('image', flat=True)
        )

        created = skipped = 0
        for filename in sorted(os.listdir(gallery_dir)):
            ext = os.path.splitext(filename)[1].lower()
            if ext not in IMAGE_EXTENSIONS:
                continue

            relative_path = f'{GALLERY_SUBDIR}/{filename}'

            if relative_path in existing:
                self.stdout.write(f'  Skipped (already exists): {filename}')
                skipped += 1
                continue

            GalleryItem.objects.create(
                image=relative_path,
                media_type='image',
                caption='',
                display_order=0,
                is_published=publish,
            )
            self.stdout.write(f'  Created: {filename}')
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. {created} created, {skipped} skipped. '
            f'{"Published." if publish else "All unpublished — assign categories and publish in the admin."}'
        ))
