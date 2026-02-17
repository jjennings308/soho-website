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
    
    # Pricing (base price - can be overridden by variations)
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Base price or price for standard size"
    )
    sale_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Optional discounted price"
    ) 
      
    # Has size/quantity variations
    has_variations = models.BooleanField(
        default=False,
        help_text="Check if this item has multiple size/quantity options"
    )
    
    # Has add-ons
    has_addons = models.BooleanField(
        default=False,
        help_text="Check if this item has add-on options"
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

    @property
    def price_range(self):
        """Return price range if item has variations"""
        if not self.has_variations:
            return None
        
        variations = self.variations.all()
        if not variations:
            return None
            
        prices = [v.price for v in variations]
        min_price = min(prices)
        max_price = max(prices)
        
        if min_price == max_price:
            return f"${min_price}"
        return f"${min_price} - ${max_price}"


class MenuItemVariation(models.Model):
    """
    Size/quantity variations for menu items (e.g., Small/Large, 6pc/12pc/30pc)
    """
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name='variations'
    )
    name = models.CharField(
        max_length=100,
        help_text="Variation name (e.g., 'Small', 'Large', '6 Wings', '12 Wings')"
    )
    description = models.CharField(
        max_length=200,
        blank=True,
        help_text="Optional description of this variation"
    )
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    quantity = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Quantity/count for this variation (e.g., 6, 12, 30)"
    )
    size = models.CharField(
        max_length=50,
        blank=True,
        help_text="Size descriptor (e.g., 'Small', 'Medium', 'Large', 'Cup', 'Bowl')"
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order (lower numbers first)"
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Is this the default/recommended option?"
    )
    is_available = models.BooleanField(
        default=True,
        help_text="Is this variation currently available?"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'price']
        verbose_name = 'Menu Item Variation'
        verbose_name_plural = 'Menu Item Variations'
        unique_together = ['menu_item', 'name']

    def __str__(self):
        return f"{self.menu_item.name} - {self.name} (${self.price})"
    
class MenuItemAddon(models.Model):
    """
    addons for menu items (e.g., cheese $2, Chicken $6)
    """
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name='addons'
    )
    name = models.CharField(
        max_length=100,
        help_text="Addon name (e.g., 'Chicken', 'Steak', etc.)"
    )
    description = models.CharField(
        max_length=200,
        blank=True,
        help_text="Optional description of this add-on"
    )
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order (lower numbers first)"
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Is this the default/recommended option?"
    )
    is_available = models.BooleanField(
        default=True,
        help_text="Is this add-on currently available?"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'price']
        verbose_name = 'Menu Item Add-on'
        verbose_name_plural = 'Menu Item Add-ons'
        unique_together = ['menu_item', 'name']

    def __str__(self):
        return f"{self.menu_item.name} - {self.name} (${self.price})"


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
