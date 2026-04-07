from django.db import models
from django_ckeditor_5.fields import CKEditor5Field
from apps.core.models import ScheduledModel, RecurrenceMixin


class ContentGroup(models.Model):
    """
    A named grouping of related ContentSlots that together form a complete
    output surface — e.g. a banner, hero panel, or promo section.

    A group owns an ordered set of slots, each typed by component role
    (title, subtitle, body, etc.). Multiple slots of the same component_type
    are allowed and distinguished by slug, enabling independent per-slot
    styling in templates.

    Designed to be fetched via {% get_content_group 'slug' as group %}, which
    prefetches all slots and their blocks in a fixed number of queries.
    The slot accessor properties filter in Python against that prefetched
    data — no additional queries are fired per property call.

    Template usage:
        {% load content_tags %}
        {% get_content_group 'hero_banner' as group %}
        {% if group %}
            {% for slot in group.title_slots %}
                {% with block=slot.get_active_block %}
                    {% if block %}<h1>{{ block.body|safe }}</h1>{% endif %}
                {% endwith %}
            {% endfor %}
            {% for slot in group.body_slots %}...{% endfor %}
            {% for slot in group.button_slots %}...{% endfor %}
        {% endif %}
    """

    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text="Machine name used to look up this group in templates and views"
    )
    label = models.CharField(
        max_length=200,
        help_text="Human-readable name shown in admin"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional hint for editors about where/how this group is used"
    )

    class Meta:
        ordering = ['slug']
        verbose_name = 'Content Group'
        verbose_name_plural = 'Content Groups'

    def __str__(self):
        return f"{self.label} ({self.slug})"

    # ------------------------------------------------------------------
    # Slot accessors
    #
    # Filter in Python against prefetched slots so that no additional DB
    # queries fire when the group was fetched via get_content_group.
    # If accessed without prefetching (shell, view), Django queries normally.
    # Sorted by (order, slug) so display sequence is admin-driven.
    # ------------------------------------------------------------------

    def _slots_by_type(self, component_type):
        return sorted(
            [s for s in self.slots.all() if s.component_type == component_type],
            key=lambda s: (s.order, s.slug)
        )

    @property
    def title_slots(self):
        return self._slots_by_type(ContentSlot.ComponentType.TITLE)

    @property
    def subtitle_slots(self):
        return self._slots_by_type(ContentSlot.ComponentType.SUBTITLE)

    @property
    def body_slots(self):
        return self._slots_by_type(ContentSlot.ComponentType.BODY)

    @property
    def footer_slots(self):
        return self._slots_by_type(ContentSlot.ComponentType.FOOTER)

    @property
    def image_slots(self):
        return self._slots_by_type(ContentSlot.ComponentType.IMAGE)

    @property
    def button_slots(self):
        return self._slots_by_type(ContentSlot.ComponentType.BUTTON)

    @property
    def all_slots(self):
        """All slots ordered by (order, slug) regardless of component type."""
        return sorted(self.slots.all(), key=lambda s: (s.order, s.slug))


class ContentSlot(models.Model):
    """
    A named slot that templates reference by slug.
    Defines WHERE content appears — e.g. 'about_header', 'catering_body'.
    Created via load_content_slots management command or directly in admin.

    Slots may optionally belong to a ContentGroup, grouping them into a named
    output surface (banner, panel, etc.). Standalone slots with no group
    remain fully valid — existing behaviour is unaffected.

    When a slot belongs to a group, component_type declares its role within
    that group. Multiple slots in the same group may share a component_type;
    they are distinguished by slug and ordered by the order field.
    """

    class ComponentType(models.TextChoices):
        TITLE    = 'title',    'Title'
        SUBTITLE = 'subtitle', 'Subtitle / Tagline'
        BODY     = 'body',     'Body / Description'
        FOOTER   = 'footer',   'Footer / CTA Text'
        IMAGE    = 'image',    'Image'
        BUTTON   = 'button',   'Button'

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

    # Nullable — existing standalone slots are unaffected.
    # SET_NULL means deleting a group orphans its slots rather than cascading.
    group = models.ForeignKey(
        ContentGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='slots',
        help_text="Optional: assign to a ContentGroup to make this slot part of a structured output"
    )
    component_type = models.CharField(
        max_length=20,
        choices=ComponentType.choices,
        blank=True,
        default='',
        help_text="Role this slot plays within its group. Leave blank for standalone slots."
    )
    order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Display order within the group among slots of the same component type"
    )

    class Meta:
        ordering = ['slug']
        verbose_name = 'Content Slot'
        verbose_name_plural = 'Content Slots'

    def __str__(self):
        if self.group and self.component_type:
            return f"{self.group.label} › {self.get_component_type_display()} — {self.label} ({self.slug})"
        return f"{self.label} ({self.slug})"

    def get_active_block(self):
        """
        Returns the single active ContentBlock for this slot, or None.

        Filters in Python against self.blocks.all() so that when this slot
        was fetched as part of a prefetched ContentGroup, no additional query
        is fired. When called on a standalone slot, Django queries normally.
        """
        return next(
            (block for block in self.blocks.all() if block.is_active and block.is_active_today()),
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

    # Button fields — only relevant when the parent slot is component_type='button'.
    # Kept on ContentBlock (not ContentSlot) so button CTAs participate in versioning.
    button_label = models.CharField(
        max_length=100,
        blank=True,
        help_text="Button text, e.g. 'Reserve a Table'. Only used when slot component_type is Button."
    )
    button_url = models.CharField(
        max_length=500,
        blank=True,
        help_text=(
            "Button destination. Accepts any link format: "
            "https://example.com, /relative/path, tel:(412) 321-7646, mailto:info@example.com. "
            "Only used when slot component_type is Button."
        )
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
