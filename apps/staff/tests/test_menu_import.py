import csv
import io
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.menu import importers as im
from apps.menu.models import MenuCategory, MenuItem
from apps.staff.help import PAGE_TIPS
from apps.staff.permissions import MANAGER_GROUP
from apps.staff.views import MENU_IMPORT_SESSION_KEY

User = get_user_model()


def upload(text, name='items.csv'):
    return SimpleUploadedFile(name, text.encode('utf-8'), content_type='text/csv')


class MenuImportAccessTests(TestCase):
    URLS = [
        ('get', 'staff:menu_import', []), ('get', 'staff:menu_import_preview', []),
        ('get', 'staff:menu_import_template', ['items']), ('get', 'staff:menu_export', ['items']),
    ]

    def test_read_only_staff_get_403_and_see_no_link(self):
        self.client.force_login(User.objects.create_user('viewer', password='x', is_staff=True))
        for _, name, args in self.URLS:
            self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 403, name)
        self.assertEqual(self.client.post(reverse('staff:menu_import')).status_code, 403)
        self.assertNotContains(self.client.get(reverse('staff:dashboard')), reverse('staff:menu_import'))

    def test_managers_can_use_it_and_see_the_link(self):
        manager = User.objects.create_user('mgr', password='x', is_staff=True)
        manager.groups.add(Group.objects.get(name=MANAGER_GROUP))
        self.client.force_login(manager)
        for _, name, args in self.URLS:
            self.assertIn(self.client.get(reverse(name, args=args)).status_code, (200, 302), name)
        dashboard = self.client.get(reverse('staff:dashboard'))
        self.assertContains(dashboard, reverse('staff:menu_import'))
        self.assertNotContains(dashboard, reverse('staff:settings'))  # still superuser-only

    def test_superuser_sees_tools_link(self):
        self.client.force_login(User.objects.create_superuser('root', 'root@example.com', 'x'))
        self.assertContains(self.client.get(reverse('staff:dashboard')), reverse('staff:menu_import'))


class MenuImportFlowTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_superuser('root', 'root@example.com', 'x'))
        MenuItem.objects.create(name='Lager', slug='lager', price=Decimal('6.00'))
        self.url = reverse('staff:menu_import')
        self.preview = reverse('staff:menu_import_preview')

    def test_upload_page_lists_kinds_in_order_with_downloads(self):
        response = self.client.get(self.url)
        content = response.content.decode()
        positions = [content.index(f'{n}. {k}') for n, k in enumerate(im.KIND_ORDER, start=1)]
        self.assertEqual(positions, sorted(positions))
        self.assertContains(response, reverse('staff:menu_export', args=['placements']))
        self.assertContains(response, 'How this page works')  # page tip

    def test_preview_shows_changes_and_saves_nothing(self):
        response = self.client.post(self.url, {'kind': 'items', 'file': upload('name,slug,price\n,lager,7\nNew Beer,new-beer,5\n')},
                                     follow=True)
        self.assertRedirects(response, self.preview)
        self.assertEqual(response.context['counts'], {'new': 1, 'update': 1, 'unchanged': 0, 'error': 0})
        self.assertContains(response, '6.00')
        self.assertContains(response, '7.00')
        self.assertContains(response, 'Confirm import')
        self.assertEqual(MenuItem.objects.get(slug='lager').price, Decimal('6.00'))
        self.assertFalse(MenuItem.objects.filter(slug='new-beer').exists())

    def test_confirm_saves_and_clears_session(self):
        self.client.post(self.url, {'kind': 'items', 'file': upload('slug,price\nlager,7\n')})
        response = self.client.post(self.preview, {'action': 'confirm'}, follow=True)
        self.assertRedirects(response, self.url)
        self.assertContains(response, 'Imported items.csv: 0 added, 1 updated')
        self.assertEqual(MenuItem.objects.get(slug='lager').price, Decimal('7.00'))
        self.assertNotIn(MENU_IMPORT_SESSION_KEY, self.client.session)
        # Preview without an upload sends you back to the upload page.
        self.assertRedirects(self.client.get(self.preview), self.url)

    def test_errors_disable_confirm_and_confirm_post_saves_nothing(self):
        self.client.post(self.url, {'kind': 'items', 'file': upload('slug,price\nlager,7\nlager2,cheap\n')})
        response = self.client.get(self.preview)
        self.assertContains(response, 'disabled')
        self.assertContains(response, 'price: &quot;cheap&quot; is not a number')
        response = self.client.post(self.preview, {'action': 'confirm'})
        self.assertContains(response, 'Nothing was saved')
        self.assertEqual(MenuItem.objects.get(slug='lager').price, Decimal('6.00'))
        self.assertIn(MENU_IMPORT_SESSION_KEY, self.client.session)  # still there to review

    def test_unknown_column_shown_as_file_error(self):
        self.client.post(self.url, {'kind': 'items', 'file': upload('slug,prise\nlager,7\n')})
        self.assertContains(self.client.get(self.preview), 'Unknown column(s): prise')

    def test_cancel_discards_upload(self):
        self.client.post(self.url, {'kind': 'items', 'file': upload('slug,price\nlager,7\n')})
        response = self.client.post(self.preview, {'action': 'cancel'}, follow=True)
        self.assertContains(response, 'Import cancelled')
        self.assertNotIn(MENU_IMPORT_SESSION_KEY, self.client.session)
        self.assertEqual(MenuItem.objects.get(slug='lager').price, Decimal('6.00'))

    def test_upload_validation(self):
        response = self.client.post(self.url, {'kind': 'bogus', 'file': upload('slug\nx\n')})
        self.assertContains(response, 'Choose what the file contains')
        response = self.client.post(self.url, {'kind': 'items'})
        self.assertContains(response, 'Choose a CSV file')

    def test_excel_windows_encoding_upload(self):
        data = 'slug,short_description\nlager,Crisp café lager\n'.encode('cp1252')
        self.client.post(self.url, {'kind': 'items', 'file': SimpleUploadedFile('x.csv', data)})
        self.client.post(self.preview, {'action': 'confirm'})
        self.assertEqual(MenuItem.objects.get(slug='lager').short_description, 'Crisp café lager')

    def test_pending_upload_banner_on_upload_page(self):
        self.client.post(self.url, {'kind': 'items', 'file': upload('slug,price\nlager,7\n')})
        self.assertContains(self.client.get(self.url), 'is uploaded but not imported yet')


class MenuCsvDownloadTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_superuser('root', 'root@example.com', 'x'))
        MenuCategory.objects.create(name='Burgers', slug='burgers')

    def rows(self, response):
        return list(csv.reader(io.StringIO(response.content.decode('utf-8-sig'))))

    def test_templates_have_the_right_headers_and_an_example(self):
        for kind in im.KIND_ORDER:
            with self.subTest(kind=kind):
                response = self.client.get(reverse('staff:menu_import_template', args=[kind]))
                self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
                self.assertIn(f'{kind}-template.csv', response['Content-Disposition'])
                header, example = self.rows(response)
                self.assertEqual(header, [c.name for c in im.KINDS[kind].columns])
                self.assertTrue(any(example))

    def test_export_matches_import_columns(self):
        response = self.client.get(reverse('staff:menu_export', args=['categories']))
        header, row = self.rows(response)
        self.assertEqual(header, [c.name for c in im.KINDS['categories'].columns])
        self.assertEqual(row[header.index('slug')], 'burgers')

    def test_unknown_kind_404(self):
        self.assertEqual(self.client.get(reverse('staff:menu_export', args=['users'])).status_code, 404)
        self.assertEqual(self.client.get(reverse('staff:menu_import_template', args=['users'])).status_code, 404)


class MenuImportHelpTests(TestCase):
    def test_pages_have_tips_and_managers_see_help_topic(self):
        self.assertIn('menu_import', PAGE_TIPS)
        self.assertIn('menu_import_preview', PAGE_TIPS)
        manager = User.objects.create_user('mgr', password='x', is_staff=True)
        manager.groups.add(Group.objects.get(name=MANAGER_GROUP))
        self.client.force_login(manager)
        self.assertContains(self.client.get(reverse('staff:help')), 'id="menu-import"')

    def test_read_only_staff_do_not_see_help_topic(self):
        self.client.force_login(User.objects.create_user('viewer', password='x', is_staff=True))
        self.assertNotContains(self.client.get(reverse('staff:help')), 'id="menu-import"')
