from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from django_ckeditor_5.fields import CKEditor5Field


class MenuType(models.Model):
    """
    Top-level grouping for the menu (e.g., Food, Beverages, Specials).
    Managed entirely through the admin — no hardcoded choices.
    """
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(
        default=0,
        help_text="Order in which types appear (lower numbers first)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Display this type on the menu"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Menu Type'
        verbose_name_plural = 'Menu Types'

    def __str__(self):
        return self.name


class MenuCategory(models.Model):
    """
    Categories for organizing menu items (e.g., Appetizers, Entrees, Desserts, Beverages)
    """
    menu_type = models.ForeignKey(
        MenuType,
        on_delete=models.CASCADE,
        related_name='categories',
        help_text="The top-level type this category belongs to (e.g., Food, Beverages)"
    )
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
        help_text="Order in which categories appear within their type (lower numbers first)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Display this category on the menu"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['menu_type__order', 'order', 'name']
        verbose_name = 'Menu Category'
        verbose_name_plural = 'Menu Categories'

    def __str__(self):
        return f"{self.menu_type.name} › {self.name}"


class MenuSubCategory(models.Model):
    """
    Optional sub-grouping within a category (e.g., Category: Beer → SubCategory: Bottled, Draft).
    Not every category will use sub-categories.
    """
    category = models.ForeignKey(
        MenuCategory,
        on_delete=models.CASCADE,
        related_name='subcategories',
        help_text="The category this sub-category belongs to (e.g., Beer)"
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(
        default=0,
        help_text="Order in which sub-categories appear within their category (lower numbers first)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Display this sub-category on the menu"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category__menu_type__order', 'category__order', 'order', 'name']
        verbose_name = 'Menu Sub-Category'
        verbose_name_plural = 'Menu Sub-Categories'

    def __str__(self):
        return f"{self.category.menu_type.name} › {self.category.name} › {self.name}"


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
    subcategory = models.ForeignKey(
        MenuSubCategory,
        on_delete=models.SET_NULL,
        related_name='items',
        blank=True,
        null=True,
        help_text="Optional sub-category (e.g., Bottled, Draft). Leave blank if not applicable."
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
    PRICE_DISPLAY_CHOICES = [
        ('price', 'Show Price'),
        ('market', 'Market Price (MP)'),
        ('hidden', 'Hide Price'),
    ]
    price_display = models.CharField(
        max_length=10,
        choices=PRICE_DISPLAY_CHOICES,
        default='price',
        help_text=(
            "'Show Price' displays the price field. "
            "'Market Price' shows 'MP' on the menu. "
            "'Hide Price' shows nothing — useful when price isn't relevant for web display."
        )
    )
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Base price or price for standard size. Leave blank for Market Price or Hidden."
    )
    sale_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Optional discounted price"
    )

    has_variations = models.BooleanField(
        default=False,
        help_text="Check if this item has multiple size/quantity options"
    )
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
    calories = models.PositiveIntegerField(blank=True, null=True)
    preparation_time = models.PositiveIntegerField(blank=True, null=True)

    # Features
    is_featured = models.BooleanField(default=False)
    is_chef_special = models.BooleanField(default=False)
    is_new = models.BooleanField(default=False)
    is_seasonal = models.BooleanField(default=False)

    # Availability
    is_available = models.BooleanField(default=True)
    available_from = models.TimeField(blank=True, null=True)
    available_until = models.TimeField(blank=True, null=True)

    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category__menu_type__order', 'category__order', 'order', 'name']
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
        if self.price_display != 'price':
            return None
        return self.sale_price if self.sale_price else self.price

    @property
    def display_price(self):
        if self.price_display == 'market':
            return "MP"
        if self.price_display == 'hidden':
            return ""
        if self.has_variations:
            return self.price_range or "See Options"
        price = self.current_price
        return float(price) if price is not None else "—"

    @property
    def is_on_sale(self):
        if self.price_display != 'price' or self.price is None:
            return False
        return self.sale_price is not None and self.sale_price < self.price

    @property
    def dietary_labels(self):
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
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='variations')
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=200, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    quantity = models.PositiveIntegerField(blank=True, null=True)
    size = models.CharField(max_length=50, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_default = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)
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
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='addons')
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=200, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    order = models.PositiveIntegerField(default=0)
    is_default = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)
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
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='gallery_images')
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


# =============================================================================
# PROMOTIONAL MENU SYSTEM
# =============================================================================

class PromoSettings(models.Model):
    """
    Singleton — global default promo color palette.
    MenuPromotion instances fall back to these when their own color fields are blank.
    Colors here fall back to theme.css :root defaults (transparent/inherit) when blank.

    Inject resolved colors onto the component wrapper in templates:
        {% with colors=promo.resolve_colors %}
        <section style="
            --color-promo-primary: {{ colors.primary }};
            --color-promo-accent:  {{ colors.accent }};
            --color-promo-text:    {{ colors.text }};
            --color-promo-bg:      {{ colors.bg }};
        ">
        {% endwith %}
    """
    promo_primary_color = models.CharField(
        max_length=30, blank=True,
        help_text="Global default: main promo color (hex, e.g. #ffb612)"
    )
    promo_accent_color = models.CharField(
        max_length=30, blank=True,
        help_text="Global default: secondary promo color (hex)"
    )
    promo_text_color = models.CharField(
        max_length=30, blank=True,
        help_text="Global default: text color within promo components (hex)"
    )
    promo_bg_color = models.CharField(
        max_length=30, blank=True,
        help_text="Global default: background color for promo components (hex)"
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Promo Settings'
        verbose_name_plural = 'Promo Settings'

    def __str__(self):
        return 'Promo Settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class MenuPromotion(models.Model):
    """
    A curated collection of menu items presented with promo colors.
    Droppable as a component anywhere — home page, its own page, a section, etc.

    Color resolution per field:
        1. This instance's color field (if set)
        2. PromoSettings global default (if set)
        3. theme.css :root fallback (transparent / inherit)

    Call resolve_colors() in the view to pass the final dict to the template.
    """
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)

    # ── Scheduling ────────────────────────────────────────────────────────────
    start_date = models.DateField(
        blank=True, null=True,
        help_text="Date this promotion becomes visible (leave blank for immediate)"
    )
    end_date = models.DateField(
        blank=True, null=True,
        help_text="Date this promotion expires (leave blank for no expiry)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Master switch — uncheck to hide regardless of dates"
    )

    # ── Color Overrides ───────────────────────────────────────────────────────
    # Leave blank to inherit from PromoSettings global defaults.
    promo_primary_color = models.CharField(
        max_length=30, blank=True,
        help_text="Override: main promo color for this promotion (hex)"
    )
    promo_accent_color = models.CharField(
        max_length=30, blank=True,
        help_text="Override: secondary promo color for this promotion (hex)"
    )
    promo_text_color = models.CharField(
        max_length=30, blank=True,
        help_text="Override: text color for this promotion's component (hex)"
    )
    promo_bg_color = models.CharField(
        max_length=30, blank=True,
        help_text="Override: background color for this promotion's component (hex)"
    )

    # ── Items ─────────────────────────────────────────────────────────────────
    items = models.ManyToManyField(
        MenuItem,
        through='MenuPromotionItem',
        related_name='promotions',
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_date', 'title']
        verbose_name = 'Menu Promotion'
        verbose_name_plural = 'Menu Promotions'

    def __str__(self):
        return self.title

    @property
    def is_currently_active(self):
        """True if active flag is set and today falls within the date range."""
        if not self.is_active:
            return False
        today = timezone.now().date()
        if self.start_date and today < self.start_date:
            return False
        if self.end_date and today > self.end_date:
            return False
        return True

    def resolve_colors(self):
        """
        Returns resolved hex values for all four promo color slots.
        Instance fields win over PromoSettings; empty string means theme.css takes over.
        """
        defaults = PromoSettings.load()
        return {
            'primary': self.promo_primary_color or defaults.promo_primary_color,
            'accent':  self.promo_accent_color  or defaults.promo_accent_color,
            'text':    self.promo_text_color     or defaults.promo_text_color,
            'bg':      self.promo_bg_color       or defaults.promo_bg_color,
        }


class MenuPromotionItem(models.Model):
    """
    Through model linking MenuPromotion to MenuItem.
    promo_price overrides the item's standard price when set — leave blank to
    display the item's normal price within the promotion.
    """
    promotion = models.ForeignKey(
        MenuPromotion,
        on_delete=models.CASCADE,
        related_name='promotion_items'
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name='promotion_entries'
    )
    promo_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Promotional price — overrides the item's standard price when set"
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order within this promotion (lower numbers first)"
    )

    class Meta:
        ordering = ['order', 'menu_item__name']
        verbose_name = 'Promotion Item'
        verbose_name_plural = 'Promotion Items'
        unique_together = ['promotion', 'menu_item']

    def __str__(self):
        price_str = f"${self.promo_price}" if self.promo_price else "standard price"
        return f"{self.promotion.title} — {self.menu_item.name} ({price_str})"

    @property
    def display_price(self):
        """Promo price if set, otherwise falls through to the item's standard display_price."""
        if self.promo_price is not None:
            return float(self.promo_price)
        return self.menu_item.display_price
