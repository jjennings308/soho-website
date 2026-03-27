from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from django_ckeditor_5.fields import CKEditor5Field
from django.contrib.contenttypes.fields import GenericRelation


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
    menu_type = models.ForeignKey(
        MenuType,
        on_delete=models.CASCADE,
        related_name='categories',
        help_text="The top-level type this category belongs to (e.g., Food, Beverages)"
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
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
    media = GenericRelation(
        'media_manager.Media',
        related_query_name='menu_category',
    )

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
    media = GenericRelation(
            'media_manager.Media',
            related_query_name='menu_item',
        )    

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
        from apps.menu.templatetags.menu_filters import currency
        if self.price_display == 'market':
            return 'MP'
        if self.price_display == 'hidden':
            return ''
        if self.has_variations:
            prices = [v.price for v in self.variations.all()]
            if prices:
                lo, hi = min(prices), max(prices)
                return currency(lo) if lo == hi else f'{currency(lo)} – {currency(hi)}'
        if self.is_on_sale:
            return currency(self.sale_price)
        return currency(self.price)

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


# =============================================================================
# PROMOTIONAL MENU SYSTEM
# =============================================================================

class PromoColorScheme(models.Model):
    """
    A named, reusable color palette for promo components.
    Assign to any MenuPromotion via its color_scheme FK.
    One scheme may be flagged as the default — used when a promotion has no
    scheme assigned and PromoSettings has no relevant override.

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
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Internal label shown in the admin, e.g. 'Black & Gold', 'Holiday Red'"
    )
    primary_color = models.CharField(
        max_length=30,
        blank=True,
        help_text="Main promo color (hex, e.g. #ffb612)"
    )
    accent_color = models.CharField(
        max_length=30,
        blank=True,
        help_text="Secondary / highlight color (hex)"
    )
    text_color = models.CharField(
        max_length=30,
        blank=True,
        help_text="Text color within promo components (hex)"
    )
    bg_color = models.CharField(
        max_length=30,
        blank=True,
        help_text="Background color for promo components (hex)"
    )
    is_default = models.BooleanField(
        default=False,
        help_text=(
            "Use this scheme when a promotion has no scheme assigned. "
            "Saving a new default automatically clears the flag on the previous one."
        )
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', 'name']
        verbose_name = 'Promo Color Scheme'
        verbose_name_plural = 'Promo Color Schemes'

    def __str__(self):
        return f"{self.name} (default)" if self.is_default else self.name

    def save(self, *args, **kwargs):
        # Enforce at most one default — clear other schemes before saving this one.
        if self.is_default:
            PromoColorScheme.objects.exclude(pk=self.pk).filter(
                is_default=True
            ).update(is_default=False)
        super().save(*args, **kwargs)

    def as_dict(self):
        """Returns the four color values as a plain dict, ready for resolve_colors()."""
        return {
            'primary': self.primary_color,
            'accent':  self.accent_color,
            'text':    self.text_color,
            'bg':      self.bg_color,
        }


class PromoSettings(models.Model):
    """
    Singleton — legacy global default promo color palette.
    Still used as a last-resort fallback in MenuPromotion.resolve_colors()
    when neither a per-promo scheme nor an is_default scheme exists.
    Colors here fall back to theme.css :root defaults (transparent/inherit) when blank.
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
    A curated collection of menu items presented with a promo color scheme.
    Droppable as a component anywhere — home page, its own page, a section, etc.

    Color resolution order in resolve_colors():
        1. This promotion's assigned color_scheme (FK)
        2. The PromoColorScheme flagged is_default
        3. PromoSettings singleton (legacy fallback)
        4. Empty string → theme.css :root takes over
    """
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)

    # ── Color Scheme ──────────────────────────────────────────────────────────
    color_scheme = models.ForeignKey(
        PromoColorScheme,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='promotions',
        help_text=(
            "Color scheme for this promotion. "
            "Leave blank to use the default scheme."
        )
    )

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
    show_on_homepage = models.BooleanField(
        default=False,
        help_text="Promoted on the home page"
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
    media = GenericRelation(
        'media_manager.Media',
        related_query_name='promotion',
    )

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

        Resolution order:
          1. This promotion's assigned color_scheme (FK)
          2. The PromoColorScheme flagged is_default
          3. PromoSettings singleton (legacy fallback)
          4. Empty string → theme.css :root takes over
        """
        scheme = self.color_scheme
        if scheme is None:
            scheme = PromoColorScheme.objects.filter(is_default=True).first()
        if scheme is not None:
            return scheme.as_dict()
        # Legacy fallback — can be removed once all promos use schemes
        defaults = PromoSettings.load()
        return {
            'primary': defaults.promo_primary_color,
            'accent':  defaults.promo_accent_color,
            'text':    defaults.promo_text_color,
            'bg':      defaults.promo_bg_color,
        }


class MenuPromotionItem(models.Model):
    promotion = models.ForeignKey(
        MenuPromotion,
        on_delete=models.CASCADE,
        related_name='promotion_items'
    )
    # Now optional — leave blank for a fresh/standalone promo item
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.SET_NULL,      # changed from CASCADE
        related_name='promotion_entries',
        null=True,                       # added
        blank=True,                      # added
        help_text="Link to an existing menu item, or leave blank to enter details below."
    )
    # Standalone fields — used when menu_item is blank, or to override when linked
    name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Item name. Auto-filled from the linked item if left blank."
    )
    description = CKEditor5Field(
        blank=True,
        help_text="Description. Auto-filled from the linked item if left blank."
    )
    promo_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Promotional price — overrides the item's standard price when set."
    )
    note = models.CharField(
        max_length=200,
        blank=True,
        help_text="Short callout shown on the item, e.g. 'Limited time!' or 'While supplies last'."
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'menu_item__name']
        verbose_name = 'Promotion Item'
        verbose_name_plural = 'Promotion Items'
        # unique_together removed — a blank menu_item can appear multiple times

    def __str__(self):
        item_name = self.name or (self.menu_item.name if self.menu_item else 'Unnamed item')
        price_str = f"${self.promo_price}" if self.promo_price else "standard price"
        return f"{self.promotion.title} — {item_name} ({price_str})"

    def resolved_name(self):
        return self.name or (self.menu_item.name if self.menu_item else '')

    def resolved_description(self):
        return self.description or (self.menu_item.description if self.menu_item else '')

    @property
    def display_price(self):
        if self.promo_price is not None:
            return float(self.promo_price)
        if self.menu_item:
            return self.menu_item.display_price
        return None
