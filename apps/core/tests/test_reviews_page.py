from django.test import TestCase
from django.urls import reverse

from apps.core.models import Review, SiteSettings


def make_review(**kwargs):
    defaults = {'reviewer_name': 'Pat', 'rating': 5, 'body': 'Great wings and friendly staff.'}
    return Review.objects.create(**{**defaults, **kwargs})


class ReviewsPageTests(TestCase):
    url = reverse('core:reviews')

    def test_page_lists_active_reviews_with_h1(self):
        make_review(body='Best pierogies on the North Shore.')
        make_review(body='Hidden review', is_active=False)
        response = self.client.get(self.url)
        self.assertContains(response, '<h1', count=1)
        self.assertContains(response, 'Best pierogies on the North Shore.')
        self.assertNotContains(response, 'Hidden review')
        self.assertNotContains(response, 'Read All Reviews')

    def test_empty_page_shows_message(self):
        self.assertContains(self.client.get(self.url), 'No reviews yet')

    def test_leave_a_review_buttons_follow_site_settings(self):
        self.assertNotContains(self.client.get(self.url), 'Review on Google')
        site = SiteSettings.load()
        site.google_review_url = 'https://g.example/review'
        site.save()
        self.assertContains(self.client.get(self.url), 'href="https://g.example/review"')


class HomeReviewsWidgetTests(TestCase):
    def test_featured_reviews_shown_with_link_to_all(self):
        make_review(body='Featured one', is_featured=True)
        response = self.client.get(reverse('core:home'))
        self.assertContains(response, 'Featured one')
        self.assertContains(response, 'Read All Reviews')

    def test_widget_hidden_without_featured_reviews(self):
        make_review(body='Not featured')
        self.assertNotContains(self.client.get(reverse('core:home')), 'Guest Reviews')
