from django.test import TestCase
from django.urls import reverse

from apps.core.models import SiteSettings


class HomeActionBarTests(TestCase):
    def bar(self):
        html = self.client.get(reverse('core:home')).content.decode()
        start = html.index('bg-[var(--color-bg-secondary)]')
        return html[start:html.index('</div>', start)]

    def test_all_three_buttons_when_links_are_set(self):
        site = SiteSettings.load()
        site.reservations_url = 'https://reserve.example/soho'
        site.doordash_url = 'https://doordash.example/soho'
        site.save()
        bar = self.bar()
        self.assertIn('Reserve a Table', bar)
        self.assertIn(f'href="{reverse("core:online_delivery")}"', bar)
        self.assertIn(f'href="{reverse("menu:full")}"', bar)
        # Reserve on the left, menu in the middle, delivery on the right.
        self.assertLess(bar.index('Reserve a Table'), bar.index('View Menu'))
        self.assertLess(bar.index('View Menu'), bar.index('Online Delivery'))

    def test_order_online_needs_a_delivery_link_and_reserve_needs_its_url(self):
        site = SiteSettings.load()
        site.reservations_url = ''
        site.doordash_url = site.grubhub_url = site.ubereats_url = ''
        site.save()
        bar = self.bar()
        self.assertNotIn('Reserve a Table', bar)
        self.assertNotIn('Online Delivery', bar)
        self.assertIn('View Menu', bar)  # the bar always shows the menu button


class HeroLayoutTests(TestCase):
    def test_hero_uses_equal_thirds(self):
        html = self.client.get(reverse('core:home')).content.decode()
        self.assertIn('grid grid-cols-1 md:grid-cols-3', html)
        self.assertNotIn('md:grid-cols-[1fr_3fr_1fr]', html)


class HeroSideBoxTests(TestCase):
    def test_side_boxes_use_less_padding_and_full_width_text(self):
        from apps.menu.models import Menu, MenuCategory, MenuCategoryAssignment, MenuItem, MenuItemCategoryAssignment
        menu = Menu.objects.create(title='Happy Hour', slug='happy-hour', menu_type='promo', homepage_slot='slot_1')
        cat = MenuCategory.objects.create(name='Drafts', slug='drafts')
        MenuCategoryAssignment.objects.create(menu=menu, category=cat)
        item = MenuItem.objects.create(name='Lager', slug='lager', short_description='Crisp and cold')
        MenuItemCategoryAssignment.objects.create(menu_item=item, category=cat)
        html = self.client.get(reverse('core:home')).content.decode()
        self.assertIn('Crisp and cold', html)
        self.assertNotIn('max-w-[180px]', html)
        self.assertEqual(html.count('md:min-h-[400px] p-2 md:p-3'), 2)  # both side boxes
