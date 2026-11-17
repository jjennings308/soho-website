from django.test import TestCase
from django.urls import reverse

from apps.media.models import MediaItem
from apps.menu.models import (
    Menu, MenuCategory, MenuCategoryAssignment, MenuItem, MenuItemCategoryAssignment, MenuItemImage,
)

IMAGE_PATH = 'media/library/lager.jpg'


class HomePromoImageTests(TestCase):
    """The two per-promo homepage image settings: hero card and 3x3 grid."""

    def setUp(self):
        self.photo = MediaItem.objects.create(
            name='Lager photo', owner_type='staff', file=IMAGE_PATH)
        self.menu = Menu.objects.create(
            title='Happy Hour', slug='happy-hour', menu_type='promo', homepage_slot='slot_1')
        self.category = MenuCategory.objects.create(name='Drafts', slug='drafts')
        MenuCategoryAssignment.objects.create(menu=self.menu, category=self.category)
        self.item = MenuItem.objects.create(
            name='Lager', slug='lager', short_description='Crisp and cold')
        MenuItemImage.objects.create(menu_item=self.item, media_item=self.photo, is_primary=True)
        MenuItemCategoryAssignment.objects.create(menu_item=self.item, category=self.category)

    def render(self):
        return self.client.get(reverse('core:home')).content.decode()

    def assert_images(self, card_images, grid_images, emoji):
        html = self.render()
        self.assertEqual(html.count(IMAGE_PATH), card_images + grid_images)
        self.assertEqual(html.count('🍽'), emoji)

    def test_default_shows_the_photo_in_the_card_and_the_grid(self):
        self.assert_images(card_images=1, grid_images=1, emoji=0)

    def test_card_text_only_hides_only_the_card_photo(self):
        Menu.objects.filter(pk=self.menu.pk).update(homepage_card_image='text')
        self.assert_images(card_images=0, grid_images=1, emoji=0)

    def test_card_placeholder_shows_an_emoji_instead_of_the_photo(self):
        Menu.objects.filter(pk=self.menu.pk).update(homepage_card_image='placeholder')
        self.assert_images(card_images=0, grid_images=1, emoji=1)

    def test_grid_without_images_hides_only_the_grid_photo(self):
        Menu.objects.filter(pk=self.menu.pk).update(homepage_grid_images=False)
        self.assert_images(card_images=1, grid_images=0, emoji=0)

    def test_both_off_is_text_only(self):
        Menu.objects.filter(pk=self.menu.pk).update(
            homepage_card_image='text', homepage_grid_images=False)
        self.assert_images(card_images=0, grid_images=0, emoji=0)

    def test_item_without_a_photo_falls_back_to_the_emoji_in_the_card(self):
        self.item.images.all().delete()
        self.assert_images(card_images=0, grid_images=0, emoji=1)

    def test_slots_can_use_different_settings(self):
        other = Menu.objects.create(
            title='Late Night', slug='late-night', menu_type='promo',
            homepage_slot='slot_2', homepage_card_image='text', homepage_grid_images=False)
        MenuCategoryAssignment.objects.create(menu=other, category=self.category)
        self.assert_images(card_images=1, grid_images=1, emoji=0)
