from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from django_ckeditor_5.fields import CKEditor5Field


class MenuCategory(models.Model):
    """
    Categories for organizing menu items (e.g., Appetizers, Entrees, Desserts, Beverages)
    """
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.ImageField(
        upload_to='menu/category_icons/',
        blank=True,
        null=True,
        help_text="Optional icon for the category"
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Order in which categories appear (lower numbers first)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Display this category on the menu"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Menu Category'
        verbose_name_plural = 'Menu Categories'

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    """
    Individual menu items with details, pricing, and dietary information
    """
    DIETARY_CHOICES = [
        ('none', 'None'),
        ('vegetarian', 'Vegetarian'),
        ('vegan', 'Vegan'),
        ('gluten_free', 'Gluten Free'),
        ('dairy_free', 'Dairy Free'),
    ]

    SPICE_LEVELS = [
        (0, 'Not Spicy'),
        (1, 'Mild'),
        (2, 'Medium'),
        (3, 'Hot'),
        (4, 'Extra Hot'),
    ]

    # Basic Information
    category = models.ForeignKey(
        MenuCategory,
        on_delete=models.CASCADE,
        related_name='items'
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = CKEditor5Field(
        blank=True,
        help_text="Detailed description of the dish"
    )
    short_description = models.CharField(
        max_length=300,
        blank=True,
        help_text="Brief description for menu listings"
    )
    
    # Pricing
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    sale_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Optional discounted price"
    )
    
    # Images
    image = models.ImageField(
        upload_to='menu/items/',
        blank=True,
        null=True,
        help_text="Primary image of the dish"
    )
    image_alt_text = models.CharField(
        max_length=200,
        blank=True,
        help_text="Alternative text for accessibility"
    )
    
    # Dietary & Allergen Information
    dietary_type = models.CharField(
        max_length=20,
        choices=DIETARY_CHOICES,
        default='none'
    )
    is_gluten_free = models.BooleanField(default=False)
    is_vegan = models.BooleanField(default=False)
    is_dairy_free = models.BooleanField(default=False)
    is_nut_free = models.BooleanField(default=False)
    contains_shellfish = models.BooleanField(default=False)
    allergen_info = models.TextField(
        blank=True,
        help_text="Additional allergen warnings"
    )
    
    # Additional Details
    spice_level = models.IntegerField(
        choices=SPICE_LEVELS,
        default=0,
        help_text="Spiciness level of the dish"
    )
    calories = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Approximate calorie count"
    )
    preparation_time = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Preparation time in minutes"
    )
    
    # Features
    is_featured = models.BooleanField(
        default=False,
        help_text="Feature this item prominently"
    )
    is_chef_special = models.BooleanField(
        default=False,
        help_text="Mark as chef's special"
    )
    is_new = models.BooleanField(
        default=False,
        help_text="Mark as new item"
    )
    is_seasonal = models.BooleanField(
        default=False,
        help_text="Seasonal availability"
    )
    
    # Availability
    is_available = models.BooleanField(
        default=True,
        help_text="Currently available for order"
    )
    available_from = models.TimeField(
        blank=True,
        null=True,
        help_text="Available from this time (optional)"
    )
    available_until = models.TimeField(
        blank=True,
        null=True,
        help_text="Available until this time (optional)"
    )
    
    # Ordering
    order = models.PositiveIntegerField(
        default=0,
        help_text="Order within category (lower numbers first)"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category__order', 'order', 'name']
        verbose_name = 'Menu Item'
        verbose_name_plural = 'Menu Items'
        indexes = [
            models.Index(fields=['category', 'order']),
            models.Index(fields=['is_featured', 'is_available']),
        ]

    def __str__(self):
        return f"{self.name} ({self.category.name})"

    @property
    def current_price(self):
        """Return sale price if available, otherwise regular price"""
        return self.sale_price if self.sale_price else self.price

    @property
    def is_on_sale(self):
        """Check if item has a sale price"""
        return self.sale_price is not None and self.sale_price < self.price

    @property
    def dietary_labels(self):
        """Return list of dietary labels for display"""
        labels = []
        if self.dietary_type != 'none':
            labels.append(self.get_dietary_type_display())
        if self.is_gluten_free:
            labels.append('Gluten Free')
        if self.is_dairy_free:
            labels.append('Dairy Free')
        if self.is_nut_free:
            labels.append('Nut Free')
        return labels


class MenuItemImage(models.Model):
    """
    Additional images for menu items (gallery)
    """
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name='gallery_images'
    )
    image = models.ImageField(upload_to='menu/gallery/')
    alt_text = models.CharField(max_length=200, blank=True)
    caption = models.CharField(max_length=300, blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = 'Menu Item Image'
        verbose_name_plural = 'Menu Item Images'

    def __str__(self):
        return f"Image for {self.menu_item.name}"
