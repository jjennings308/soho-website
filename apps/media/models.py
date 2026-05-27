from django.db import models
from django.utils.text import slugify

from apps.core.models import TimeStampedModel


def media_upload_path(instance, filename):
    """
    Route new uploads to the correct subdirectory by owner type.

    Staff uploads  → media/library/<filename>
    Member uploads → media/submissions/<filename>

    Note: files already on disk under media/gallery/ keep their existing
    paths when imported by the import_media_files management command —
    this function only applies to new uploads through the upload form.
    """
    if instance.owner_type == 'member':
        return f'media/submissions/{filename}'
    return f'media/library/{filename}'


# =============================================================================
# MEDIA CATEGORY
# =============================================================================

class MediaCategory(TimeStampedModel):
    """
    A named grouping for MediaItems — used to organise the staff library
    and to drive the category tabs on the public /gallery/ page.

    is_gallery_visible=False marks internal-only categories (e.g. 'Banner
    Images', 'Menu Backgrounds') that should never appear as public tabs.
    is_published=False hides a category from the public gallery while keeping
    it visible in the staff portal (e.g. a category being prepared for launch).
    """

    name          = models.CharField(max_length=100)
    slug          = models.SlugField(unique=True, help_text="Auto-generated from name.")
    description   = models.CharField(
        max_length=255,
        blank=True,
        help_text="Shown as a subtitle on the public gallery page.",
    )
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Controls tab order on the public gallery. Lower numbers appear first.",
    )
    is_published = models.BooleanField(
        default=True,
        help_text=(
            "False = hidden from the public gallery. "
            "Still visible in the staff portal."
        ),
    )
    is_gallery_visible = models.BooleanField(
        default=True,
        help_text=(
            "False = internal library category only (e.g. Banner Images). "
            "Never shown as a tab on the public gallery page."
        ),
    )

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name        = 'Media Category'
        verbose_name_plural = 'Media Categories'

    def __str__(self):
        return self.name


# =============================================================================
# MEDIA ITEM
# =============================================================================

class MediaItem(TimeStampedModel):
    """
    The single source of truth for every image and video on the site.

    Guiding principle: Media is what it is. Gallery is how it's used.

    Every image shown anywhere on the site — menu items, banners, category
    backgrounds, the public gallery — is a MediaItem. The consuming model
    (MenuItem, Banner, etc.) holds a FK to MediaItem; it does not own the file.

    owner_type separates staff-controlled media from future member submissions:
      'staff'  — uploaded/imported by staff; eligible for site-wide assignment.
                 Staff pickers always filter to owner_type='staff'.
      'member' — customer submission; goes through a moderation queue;
                 never appears in staff assignment pickers.

    Upload paths:
      New staff uploads   → media/library/<filename>
      Member submissions  → media/submissions/<filename>
      Imported gallery    → keeps existing media/gallery/... path as-is

    Slug is auto-generated from name on first save, with -2/-3 collision handling.
    """

    OWNER_TYPE_CHOICES = [
        ('staff',  'Staff'),
        ('member', 'Member submission'),
    ]

    MEDIA_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
    ]

    # ── Identity ──────────────────────────────────────────────────────────────
    name = models.CharField(
        max_length=200,
        help_text=(
            "Human-readable library name — staff-entered, renameable. "
            "E.g. 'Burger Hero Shot Summer 2025'. "
            "Separate from caption, which is public-facing."
        ),
    )
    slug = models.SlugField(
        max_length=220,
        unique=True,
        blank=True,
        help_text="Auto-generated from name. Used internally, not in URLs.",
    )

    # ── Ownership & type ──────────────────────────────────────────────────────
    owner_type = models.CharField(
        max_length=10,
        choices=OWNER_TYPE_CHOICES,
        default='staff',
        help_text=(
            "Staff items are eligible for site-wide use. "
            "Member submissions go through moderation and never appear in staff pickers."
        ),
    )
    media_type = models.CharField(
        max_length=10,
        choices=MEDIA_TYPE_CHOICES,
        default='image',
    )

    # ── File / URL ────────────────────────────────────────────────────────────
    file = models.ImageField(
        upload_to=media_upload_path,
        blank=True,
        max_length=500,
        help_text="Used when media_type='image'. Leave blank for video items.",
    )
    video_url = models.URLField(
        blank=True,
        help_text=(
            "Used when media_type='video'. "
            "GLightbox auto-detects YouTube, Vimeo, TikTok, and direct MP4 URLs."
        ),
    )

    # ── Public display ────────────────────────────────────────────────────────
    alt_text = models.CharField(
        max_length=255,
        blank=True,
        help_text="Accessibility alt text. Also used as a fallback caption.",
    )
    caption = models.CharField(
        max_length=255,
        blank=True,
        help_text="Public-facing caption shown in the gallery lightbox.",
    )

    # ── Organisation ──────────────────────────────────────────────────────────
    category = models.ForeignKey(
        MediaCategory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='items',
        help_text="Primary category for gallery display.",
    )
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Order within category on the public gallery.",
    )

    # ── Visibility ────────────────────────────────────────────────────────────
    is_published = models.BooleanField(
        default=False,
        help_text=(
            "False = not shown on the public gallery. "
            "Staff items default to False and must be explicitly published."
        ),
    )

    # ── Uploader / member link ────────────────────────────────────────────────
    uploaded_by = models.ForeignKey(
        'auth.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='uploaded_media',
        help_text="Staff user who uploaded this item. Null for files imported from disk.",
    )
    member = models.ForeignKey(
        'members.SoHoMember',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='media_submissions',
        help_text="Populated for member submissions only (owner_type='member').",
    )

    # ── Moderation ────────────────────────────────────────────────────────────
    is_approved = models.BooleanField(
        default=True,
        help_text=(
            "Staff items: always True. "
            "Member submissions: starts False, set True by staff after review."
        ),
    )
    is_flagged = models.BooleanField(
        default=False,
        help_text="Moderation flag — set True to queue for staff review.",
    )
    flagged_reason = models.TextField(blank=True)

    class Meta:
        ordering = ['category__display_order', 'display_order', 'name']
        verbose_name        = 'Media Item'
        verbose_name_plural = 'Media Items'

    def save(self, *args, **kwargs):
        # Auto-generate slug from name on first save; never overwrite manually set slugs.
        if not self.slug:
            base = slugify(self.name)
            slug = base
            n = 2
            while MediaItem.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{n}'
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def url(self):
        """Convenience accessor — returns the file URL for images or video_url for video."""
        if self.media_type == 'video':
            return self.video_url
        return self.file.url if self.file else ''

    @property
    def file_size_display(self):
        """
        Returns the exact file size as a formatted string (e.g. '1,234,567 bytes').
        Returns '' if there is no file or the file is missing on disk.
        """
        if not self.file:
            return ''
        try:
            size = self.file.size  # bytes; raises OSError if file missing
        except (FileNotFoundError, OSError):
            return ''
        return f"{size:,} bytes"
