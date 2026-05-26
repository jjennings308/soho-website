import json
import os
import urllib.request
import urllib.error
from datetime import date

from django.core.management.base import BaseCommand, CommandError

from apps.core.models import Review


VALID_SOURCES = ('google', 'yelp')


class Command(BaseCommand):
    help = 'Import reviews from Google Places API or Yelp Fusion API.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            choices=VALID_SOURCES,
            required=True,
            help='Which platform to import from: google or yelp',
        )

    def handle(self, *args, **options):
        source = options['source']
        if source == 'google':
            imported, skipped = self._import_google()
        else:
            imported, skipped = self._import_yelp()
        self.stdout.write(
            f'Done — {imported} imported, {skipped} skipped (already exist).'
        )

    # ── Google Places API ────────────────────────────────────────────────────

    def _import_google(self):
        api_key = os.environ.get('GOOGLE_PLACES_API_KEY', '').strip()
        place_id = os.environ.get('GOOGLE_PLACE_ID', '').strip()

        if not api_key or not place_id:
            raise CommandError(
                'GOOGLE_PLACES_API_KEY and GOOGLE_PLACE_ID must be set in your .env'
            )

        url = (
            'https://maps.googleapis.com/maps/api/place/details/json'
            f'?place_id={place_id}'
            '&fields=reviews'
            f'&key={api_key}'
        )

        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read())
        except urllib.error.URLError as e:
            raise CommandError(f'Google API request failed: {e}')

        status = data.get('status')
        if status != 'OK':
            raise CommandError(f'Google API returned status: {status}')

        reviews = data.get('result', {}).get('reviews', [])
        if not reviews:
            self.stdout.write('No reviews returned by Google (API returns up to 5 most recent).')
            return 0, 0

        imported = skipped = 0
        for r in reviews:
            # Google has no stable review ID — use author + unix time as fingerprint
            source_id = f"google_{r.get('author_name', '')}_{r.get('time', '')}"

            if Review.objects.filter(source='google', source_id=source_id).exists():
                skipped += 1
                continue

            review_date = date.fromtimestamp(r['time']) if r.get('time') else date.today()

            Review.objects.create(
                source='google',
                source_id=source_id,
                reviewer_name=r.get('author_name', 'Anonymous'),
                reviewer_location='',
                rating=min(max(round(r.get('rating', 5)), 1), 5),
                body=r.get('text', ''),
                is_active=False,
            )
            imported += 1

        return imported, skipped

    # ── Yelp Fusion API ──────────────────────────────────────────────────────

    def _import_yelp(self):
        api_key = os.environ.get('YELP_API_KEY', '').strip()
        business_id = os.environ.get('YELP_BUSINESS_ID', '').strip()

        if not api_key or not business_id:
            raise CommandError(
                'YELP_API_KEY and YELP_BUSINESS_ID must be set in your .env'
            )

        url = f'https://api.yelp.com/v3/businesses/{business_id}/reviews?limit=20'
        req = urllib.request.Request(url, headers={'Authorization': f'Bearer {api_key}'})

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            raise CommandError(f'Yelp API error {e.code}: {e.reason}')
        except urllib.error.URLError as e:
            raise CommandError(f'Yelp API request failed: {e}')

        reviews = data.get('reviews', [])
        if not reviews:
            self.stdout.write('No reviews returned by Yelp.')
            return 0, 0

        imported = skipped = 0
        for r in reviews:
            source_id = r.get('id', '')
            if not source_id:
                skipped += 1
                continue

            if Review.objects.filter(source='yelp', source_id=source_id).exists():
                skipped += 1
                continue

            user = r.get('user', {})
            location = user.get('location', {}) or {}
            city = location.get('city', '') if isinstance(location, dict) else ''

            time_created = r.get('time_created', '')
            try:
                review_date = date.fromisoformat(time_created[:10]) if time_created else date.today()
            except ValueError:
                review_date = date.today()

            Review.objects.create(
                source='yelp',
                source_id=source_id,
                reviewer_name=user.get('name', 'Anonymous'),
                reviewer_location=city,
                rating=min(max(round(r.get('rating', 5)), 1), 5),
                body=r.get('text', ''),
                is_active=False,
            )
            imported += 1

        return imported, skipped
