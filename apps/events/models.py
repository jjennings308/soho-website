from django.db import models
from django.utils import timezone
from django_ckeditor_5.fields import CKEditor5Field


class EventCategory(models.Model):
    """
    Categories for different types of events
    """
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color_code = models.CharField(
        max_length=7,
        default='#3B82F6',
        help_text="Hex color code for displaying events (e.g., #FF5733)"
    )
    icon = models.ImageField(
        upload_to='events/category_icons/',
        blank=True,
        null=True
    )
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Event Category'
        verbose_name_plural = 'Event Categories'

    def __str__(self):
        return self.name


class Event(models.Model):
    """
    Restaurant events, special occasions, promotions, and activities
    """
    EVENT_STATUS = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    RECURRENCE_TYPES = [
        ('none', 'Does Not Repeat'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]

    # Basic Information
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    category = models.ForeignKey(
        EventCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='events'
    )
    
    # Content
    short_description = models.CharField(
        max_length=300,
        help_text="Brief summary for event listings"
    )
    description = CKEditor5Field(
        help_text="Full event description with details"
    )
    
    # Images
    featured_image = models.ImageField(
        upload_to='events/featured/',
        blank=True,
        null=True,
        help_text="Main event image"
    )
    image_alt_text = models.CharField(max_length=200, blank=True)
    
    # Date and Time
    start_date = models.DateField(help_text="Event start date")
    start_time = models.TimeField(blank=True, null=True, help_text="Event start time (optional)")
    end_date = models.DateField(blank=True, null=True, help_text="Event end date (optional)")
    end_time = models.TimeField(blank=True, null=True, help_text="Event end time (optional)")
    
    # Recurrence
    recurrence_type = models.CharField(
        max_length=20,
        choices=RECURRENCE_TYPES,
        default='none',
        help_text="Does this event repeat?"
    )
    recurrence_end_date = models.DateField(
        blank=True,
        null=True,
        help_text="When does the recurring event end?"
    )
    
    # Capacity and Registration
    has_registration = models.BooleanField(
        default=False,
        help_text="Does this event require registration?"
    )
    max_capacity = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Maximum number of attendees (leave blank for unlimited)"
    )
    current_registrations = models.PositiveIntegerField(
        default=0,
        help_text="Current number of registrations"
    )
    registration_deadline = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Last date/time for registration"
    )
    
    # Pricing
    is_free = models.BooleanField(default=True)
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Price per person (if applicable)"
    )
    
    # Contact and Links
    contact_email = models.EmailField(
        blank=True,
        help_text="Contact email for event inquiries"
    )
    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text="Contact phone for event inquiries"
    )
    external_url = models.URLField(
        blank=True,
        help_text="External registration or information URL"
    )
    
    # Features
    is_featured = models.BooleanField(
        default=False,
        help_text="Feature this event prominently on the homepage"
    )
    is_special = models.BooleanField(
        default=False,
        help_text="Mark as special/exclusive event"
    )
    
    # Status and Publishing
    status = models.CharField(
        max_length=20,
        choices=EVENT_STATUS,
        default='draft'
    )
    published_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When this event was published"
    )
    
    # SEO
    meta_description = models.TextField(
        blank=True,
        max_length=160,
        help_text="Meta description for search engines"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_date', 'start_time', 'title']
        verbose_name = 'Event'
        verbose_name_plural = 'Events'
        indexes = [
            models.Index(fields=['start_date', 'status']),
            models.Index(fields=['is_featured', 'status']),
        ]

    def __str__(self):
        return f"{self.title} ({self.start_date})"

    def save(self, *args, **kwargs):
        # Auto-set published_date when status changes to published
        if self.status == 'published' and not self.published_date:
            self.published_date = timezone.now()
        super().save(*args, **kwargs)

    @property
    def is_upcoming(self):
        """Check if event is in the future"""
        return self.start_date >= timezone.now().date()

    @property
    def is_past(self):
        """Check if event has already occurred"""
        end_date = self.end_date if self.end_date else self.start_date
        return end_date < timezone.now().date()

    @property
    def is_ongoing(self):
        """Check if event is currently happening"""
        today = timezone.now().date()
        end_date = self.end_date if self.end_date else self.start_date
        return self.start_date <= today <= end_date

    @property
    def is_full(self):
        """Check if event has reached capacity"""
        if not self.has_registration or not self.max_capacity:
            return False
        return self.current_registrations >= self.max_capacity

    @property
    def spots_remaining(self):
        """Get number of spots remaining"""
        if not self.has_registration or not self.max_capacity:
            return None
        return max(0, self.max_capacity - self.current_registrations)

    @property
    def can_register(self):
        """Check if registration is still open"""
        if not self.has_registration:
            return False
        if self.is_full:
            return False
        if self.registration_deadline and timezone.now() > self.registration_deadline:
            return False
        return True


class EventImage(models.Model):
    """
    Additional images for events (gallery)
    """
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='gallery_images'
    )
    image = models.ImageField(upload_to='events/gallery/')
    alt_text = models.CharField(max_length=200, blank=True)
    caption = models.CharField(max_length=300, blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = 'Event Image'
        verbose_name_plural = 'Event Images'

    def __str__(self):
        return f"Image for {self.event.title}"
