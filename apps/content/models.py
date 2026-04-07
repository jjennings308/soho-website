from django.db import models
from django_ckeditor_5.fields import CKEditor5Field
from apps.core.models import ScheduledModel, RecurrenceMixin


class ContentSlot(models.Model):
    """
    A named slot that templates reference by slug.
    Defines WHERE content appears — e.g. 'about_header', 'catering_body'.
    Created via load_content_slots management command or directly in admin.
    """
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text="Machine name used in templates: {% get_active_block 'about_header' %}"
    )
    label = models.CharField(
        max_length=200,
        help_text="Human-readable name shown in admin"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional hint for editors about where/how this content is used"
    )

    class Meta:
        ordering = ['slug']
        verbose_name = 'Content Slot'
        verbose_name_plural = 'Content Slots'

    def __str__(self):
        return f"{self.label} ({self.slug})"

    def get_active_block(self):
        """Returns the single active ContentBlock for this slot, or None."""
        return next(
            (block for block in self.blocks.active() if block.is_active_today()),
            None
        )
    

class ContentBlock(RecurrenceMixin, ScheduledModel):
    """
    A versioned piece of content assigned to a slot.
    Multiple blocks can exist per slot; only one should be active at a time.
    Deactivated blocks are kept for history and can be reactivated.
    """
    slot = models.ForeignKey(
        ContentSlot,
        on_delete=models.CASCADE,
        related_name='blocks'
    )
    label = models.CharField(
        max_length=200,
        blank=True,
        help_text="Internal label to distinguish versions, e.g. 'Summer 2025' or 'Original'"
    )
    body = CKEditor5Field(
        blank=True,
        help_text="Rich text content. Leave blank if this block is image-only."
    )
    image = models.ImageField(
        upload_to='content/blocks/',
        blank=True,
        null=True,
        help_text="Optional image. Leave blank if this block is text-only."
    )

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Content Block'
        verbose_name_plural = 'Content Blocks'

    def __str__(self):
        active_marker = " [ACTIVE]" if self.is_active else ""
        version_label = self.label or str(self.created_at.date()) if self.created_at else "unsaved"
        return f"{self.slot.label} — {version_label}{active_marker}"

    def save(self, *args, **kwargs):
        # Enforce single-active invariant: deactivate all other blocks for this slot
        if self.is_active:
            ContentBlock.objects.filter(
                slot=self.slot,
                is_active=True
            ).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)
