from django.test import TestCase


class UrlTests(TestCase):
    def test_about_has_trailing_slash_and_old_url_redirects(self):
        self.assertEqual(self.client.get('/about/').status_code, 200)
        self.assertRedirects(self.client.get('/about'), '/about/', status_code=301)

    def test_contact_redirects_to_about_contact_section(self):
        self.assertRedirects(self.client.get('/contact/'), '/about/#contact', fetch_redirect_response=False)
        self.assertRedirects(self.client.get('/contact'), '/contact/', status_code=301,
                             fetch_redirect_response=False)

    def test_theme_test_page_removed(self):
        self.assertEqual(self.client.get('/test').status_code, 404)
