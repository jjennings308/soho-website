from django.core.management.base import BaseCommand

from apps.gallery.models import GalleryCategory

CATEGORIES = [
    (1, 'starters',         'Starters'),
    (2, 'soups-and-salads', 'Soups & Salads'),
    (3, 'wraps-and-tacos',  'Wraps & Tacos'),
    (4, 'sandwiches',       'Sandwiches'),
    (5, 'burgers',          'Burgers'),
    (6, 'sides',            'Sides'),
    (7, 'pizza',            'Pizza'),
    (8, 'kids',             'Kids'),
    (9, 'desserts',         'Desserts'),
    (10, 'drinks',          'Drinks'),
    (11, 'interior',        'Interior'),
    (12, 'exterior',        'Exterior'),
    (13, 'atmosphere',      'Atmosphere'),
]


class Command(BaseCommand):
    help = 'Seed the default gallery categories. Safe to re-run.'

    def handle(self, *args, **options):
        created_count = 0
        for order, slug, name in CATEGORIES:
            _, created = GalleryCategory.objects.get_or_create(
                slug=slug,
                defaults={'name': name, 'display_order': order},
            )
            if created:
                created_count += 1
                self.stdout.write(f'  Created: {name}')
            else:
                self.stdout.write(f'  Exists:  {name}')

        if created_count:
            self.stdout.write(self.style.SUCCESS(f'\n{created_count} categor{"y" if created_count == 1 else "ies"} created.'))
        else:
            self.stdout.write(self.style.SUCCESS('\nAll categories already exist — nothing to do.'))
