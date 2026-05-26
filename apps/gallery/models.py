from django.db import models
from django.utils.text import slugify

from apps.core.models import TimeStampedModel


class GalleryCategory(TimeStampedModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.CharField(max_length=255, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = 'Gallery Category'
        verbose_name_plural = 'Gallery Categories'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class GalleryItem(TimeStampedModel):
    MEDIA_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
    ]

    category = models.ForeignKey(
        GalleryCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='items',
    )
    menu_item = models.ForeignKey(
        'menu.MenuItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='gallery_items',
        help_text="Link to a menu item to show this photo on the menu card and modal.",
    )
    media_type = models.CharField(max_length=10, choices=MEDIA_CHOICES, default='image')
    image = models.ImageField(upload_to='gallery/', blank=True, max_length=500)
    video_url = models.URLField(blank=True)
    caption = models.CharField(max_length=255, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ['category__display_order', 'display_order']
        verbose_name = 'Gallery Item'
        verbose_name_plural = 'Gallery Items'

    @property
    def effective_caption(self):
        return self.caption or (self.menu_item.name if self.menu_item_id else '')

    def __str__(self):
        return self.caption or f"Gallery Item {self.pk}"
