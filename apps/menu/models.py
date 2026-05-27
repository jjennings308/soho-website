import os
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from django_ckeditor_5.fields import CKEditor5Field
from apps.core.models import ColorScheme, TimeStampedModel, ScheduledModel, RecurrenceMixin


class MenuItemUpload:
    def __call__(self, instance, filename):
        ext = os.path.splitext(filename)[1]
        return f'menu_items/{instance.slug}{ext}'

    def deconstruct(self):
        return ('apps.menu.models.MenuItemUpload', [], {})


# =============================================================================
# MENU CATEGORY
# =============================================================================

class MenuCategory(TimeStampedModel):
    """
    A named grouping of menu items — e.g. Starters, Burgers, Desserts,
    Signature Cocktails, Beer, Sweet Street, Happy Hour Food.

    category_type determines whether this category belongs on the Food menu
    or the Drinks menu. The Menu itself declares which categories it uses
    via MenuCategoryAssignment.

    Categories are shared infrastructure — the same category can appear on
    multiple Menus. A Menu selects the categories it wants to show; it does
    not own them.
    """

    CATEGORY_TYPE_CHOICES = [
        ('food',   'Food'),
        ('drinks', 'Drinks'),
    ]

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    category_type = models.CharField(
        max_length=10,
        choices=CATEGORY_TYPE_CHOICES,
        default='food',
        help_text=(
            "Food or Drinks — used to determine which menu this category "
            "belongs to (food or drinks)."
        )
    )
    description = models.TextField(blank=True)
    background_image = models.ImageField(
        upload_to='menu_categories/',
        blank=True,
        null=True,
        help_text=(
            "Optional background image for this category section on the menu page. "
            "When set, the image fills the section with a dark overlay for text "
            "legibility. Leave blank for the standard alternating background."
        )
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Default display order within this category type. "
                  "Per-menu ordering is set on MenuCategoryAssignment."
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive categories are hidden everywhere regardless of menu assignment."
    )
    show_disclaimer = models.BooleanField(
        default=False,
        help_text="Show the menu footer disclaimer at the bottom of this category section."
    )

    class Meta:
        ordering = ['category_type', 'order', 'name']
        verbose_name = 'Menu Category'
        verbose_name_plural = 'Menu Categories'

    def __str__(self):
        return f"{self.get_category_type_display()} › {self.name}"


# =============================================================================
# MENU SUB-CATEGORY
# =============================================================================

class MenuSubCategory(TimeStampedModel):
    """
    Optional sub-grouping within a category.
    Example: Category=Beer → SubCategories: On Tap, IPA & Craft, Bottles & Cans.
    Not every category uses sub-categories.
    """
    category = models.ForeignKey(
        MenuCategory,
        on_delete=models.CASCADE,
        related_name='subcategories',
        help_text="The category this sub-category belongs to."
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(
        default=0,
        help_text="Order within the parent category (lower numbers first)."
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['category__order', 'order', 'name']
        verbose_name = 'Menu Sub-Category'
        verbose_name_plural = 'Menu Sub-Categories'

    def __str__(self):
        return f"{self.category.name} › {self.name}"


# =============================================================================
# MENU ITEM  (item library — no inherent menu home)
# =============================================================================

class MenuItem(TimeStampedModel, RecurrenceMixin):
    """
    A single item in the item library. Not bound to any specific menu.

    Items are placed onto menus via MenuItemCategoryAssignment, which records
    which category the item appears in, its display order within that category,
    an optional price override, and game-day availability for that placement.

    The same item can appear in multiple categories across multiple menus —
    e.g. Potstickers in Starters (order=3) and Happy Hour Food (order=1) at
    a different price.
    """

    DIETARY_CHOICES = [
        ('none',        'None'),
        ('vegetarian',  'Vegetarian'),
        ('vegan',       'Vegan'),
        ('gluten_free', 'Gluten Free'),
        ('dairy_free',  'Dairy Free'),
    ]

    SPICE_LEVELS = [
        (0, 'Not Spicy'),
        (1, 'Mild'),
        (2, 'Medium'),
        (3, 'Hot'),
        (4, 'Extra Hot'),
    ]

    PRICE_DISPLAY_CHOICES = [
        ('price',  'Show Price'),
        ('market', 'Market Price (MP)'),
        ('hidden', 'Hide Price'),
    ]

    # ── Identity ──────────────────────────────────────────────────────────────
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = CKEditor5Field(
        blank=True,
        help_text="Detailed description shown in the item modal."
    )
    short_description = models.CharField(
        max_length=300,
        blank=True,
        help_text="Brief description for menu listings."
    )

    # ── Pricing ───────────────────────────────────────────────────────────────
    price_display = models.CharField(
        max_length=10,
        choices=PRICE_DISPLAY_CHOICES,
        default='price',
        help_text=(
            "'Show Price' displays the price field. "
            "'Market Price' shows 'MP'. "
            "'Hide Price' shows nothing — useful for drinks with no listed price."
        )
    )
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Base price. Leave blank for Market Price or Hidden."
    )
    sale_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Optional sale price. Shown instead of base price when set."
    )
    has_variations = models.BooleanField(
        default=False,
        help_text="Check if this item has multiple size/quantity options."
    )
    has_addons = models.BooleanField(
        default=False,
        help_text="Check if this item has add-on options."
    )

    # ── Dietary & Allergens ───────────────────────────────────────────────────
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
        help_text="Additional allergen warnings."
    )

    # ── Details ───────────────────────────────────────────────────────────────
    spice_level = models.IntegerField(choices=SPICE_LEVELS, default=0)
    calories = models.PositiveIntegerField(blank=True, null=True)
    preparation_time = models.PositiveIntegerField(blank=True, null=True)

    # ── Feature flags ─────────────────────────────────────────────────────────
    is_featured = models.BooleanField(
        default=False,
        help_text=(
            "Spotlight this item on the home page and menu featured sections. "
            "Independent of any promotion."
        )
    )
    is_chef_special = models.BooleanField(default=False)
    is_new = models.BooleanField(default=False)
    is_seasonal = models.BooleanField(default=False)

    # ── Availability ──────────────────────────────────────────────────────────
    is_available = models.BooleanField(
        default=True,
        help_text="Global availability switch. Overrides all menu placements."
    )
    available_from = models.TimeField(
        blank=True,
        null=True,
        help_text="Time of day this item becomes available (e.g. 11:00 for 11am). Leave blank for no restriction."
    )
    available_until = models.TimeField(
        blank=True,
        null=True,
        help_text="Time of day this item stops being available (e.g. 16:00 for 4pm). Leave blank for no restriction."
    )
    
    image = models.ImageField(upload_to=MenuItemUpload(), null=True, blank=True)
    image_alt = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Menu Item'
        verbose_name_plural = 'Menu Items'
        indexes = [
            models.Index(fields=['is_featured', 'is_available']),
        ]

    def __str__(self):
        return self.name

    # ── Properties ────────────────────────────────────────────────────────────

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

    @property
    def is_available_now(self):
        """
        True if the item is available right now based on all three checks:
        global switch, day of week, and time of day window.
        """
        if not self.is_available:
            return False
        if not self.is_active_today():
            return False
        if self.available_from or self.available_until:
            now = timezone.now().time()
            if self.available_from and now < self.available_from:
                return False
            if self.available_until and now > self.available_until:
                return False
        return True

# =============================================================================
# MENU ITEM VARIATION & ADDON
# =============================================================================

class MenuItemVariation(TimeStampedModel):
    """Size/quantity variants of a MenuItem (e.g. 12oz / 16oz draft pours)."""
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name='variations'
    )
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=200, blank=True)
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    quantity = models.PositiveIntegerField(blank=True, null=True)
    size = models.CharField(max_length=50, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_default = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'price']
        verbose_name = 'Menu Item Variation'
        verbose_name_plural = 'Menu Item Variations'
        unique_together = ['menu_item', 'name']

    def __str__(self):
        return f"{self.menu_item.name} — {self.name} (${self.price})"


class MenuItemAddon(TimeStampedModel):
    """Optional add-ons for a MenuItem (e.g. Bacon +2, Guacamole +2)."""
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name='addons'
    )
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=200, blank=True)
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    order = models.PositiveIntegerField(default=0)
    is_default = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'price']
        verbose_name = 'Menu Item Add-on'
        verbose_name_plural = 'Menu Item Add-ons'
        unique_together = ['menu_item', 'name']

    def __str__(self):
        return f"{self.menu_item.name} — {self.name} (${self.price})"


class PromoSettings(models.Model):
    """
    Singleton — legacy global color fallback.
    Used as last resort in Menu.resolve_colors() when no scheme is assigned
    and no default scheme exists. Can be removed once all menus use schemes.
    """
    promo_primary_color = models.CharField(max_length=30, blank=True)
    promo_accent_color  = models.CharField(max_length=30, blank=True)
    promo_text_color    = models.CharField(max_length=30, blank=True)
    promo_bg_color      = models.CharField(max_length=30, blank=True)
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


# =============================================================================
# MENU  (unified — replaces MenuPromotion; default menu IS the regular menu)
# =============================================================================

class Menu(RecurrenceMixin, ScheduledModel):
    """
    A named collection of menu items, unified across regular menus and
    promotional menus.

    menu_type controls rendering:
        'food'   — food menu; assign role=default_food or event_food
        'drinks' — drinks menu; assign role=default_drinks or event_drinks
        'promo'  — promotional menu; uses color_scheme and homepage_slot

    The active food and drinks menus are selected by role via get_active_menus(),
    not by is_default. is_default is legacy — prefer role for new menus.
    Non-default menus are promos, happy hour, specials, etc.

    Categories are declared via MenuCategoryAssignment. Items within each
    category are placed via MenuItemCategoryAssignment.

    Color resolution for non-default menus (resolve_colors()):
        1. This menu's assigned color_scheme FK
        2. ColorScheme flagged is_default
        3. PromoSettings singleton (legacy fallback)
    """

    MENU_TYPE_CHOICES = [
        ('food',   'Food'),
        ('drinks', 'Drinks'),
        ('promo',  'Promotion'),
    ]

    # ── Identity ──────────────────────────────────────────────────────────────
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)

    # ── Type & default ────────────────────────────────────────────────────────
    menu_type = models.CharField(
        max_length=10,
        choices=MENU_TYPE_CHOICES,
        default='promo',
        help_text=(
            "Food or Drinks for role-assigned menus. "
            "Promotion enables color scheme and homepage display."
        )
    )
    is_default = models.BooleanField(
        default=False,
        help_text=(
            "Legacy flag — the active menu is now selected by role, not is_default. "
            "Leave unchecked for new menus."
        )
    )

    # ── Color scheme (promos) ─────────────────────────────────────────────────
    color_scheme = models.ForeignKey(
        ColorScheme,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='menus',
        help_text="Color scheme for this menu. Leave blank to use the default scheme."
    )

# ── Homepage display ──────────────────────────────────────────────────────────
    HOMEPAGE_SLOT_CHOICES = [
        ('none',   'None'),
        ('slot_1', 'Homepage Slot 1 (left)'),
        ('slot_2', 'Homepage Slot 2 (right)'),
    ]

    homepage_slot = models.CharField(
        max_length=10,
        choices=HOMEPAGE_SLOT_CHOICES,
        default='none',
        help_text=(
            "Assign this promo menu to a homepage display slot. "
            "Slot 1 appears left of the hero banner, Slot 2 appears right. "
            "Only one menu should occupy each slot at a time."
        )
    )

    # ── Role ──────────────────────────────────────────────────────────────────
    ROLE_CHOICES = [
        ('none',          'No special role'),
        ('default_food',  'Default Food Menu'),
        ('default_drinks','Default Drinks Menu'),
        ('event_food',    'Event Food Menu'),
        ('event_drinks',  'Event Drinks Menu'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='none',
        help_text=(
            "Functional role used by views to select the correct menu. "
            "Only one menu may hold each non-'none' role at a time — "
            "assigning a role here automatically removes it from any other menu."
        )
    )

    # ── Categories (declared via through table) ───────────────────────────────
    categories = models.ManyToManyField(
        MenuCategory,
        through='MenuCategoryAssignment',
        related_name='menus',
        blank=True,
    )

    class Meta:
        ordering = ['menu_type', 'title']
        verbose_name = 'Menu'
        verbose_name_plural = 'Menus'

    def __str__(self):
        marker = ' (default)' if self.is_default else ''
        return f"{self.title}{marker}"

    def save(self, *args, **kwargs):
        if self.role != 'none':
            # Demote any other menu currently holding this role
            Menu.objects.filter(role=self.role).exclude(pk=self.pk).update(role='none')
        super().save(*args, **kwargs)

    # ── Properties ────────────────────────────────────────────────────────────

    def resolve_colors(self):
        """
        Returns resolved hex values for all four color slots.

        Resolution order:
            1. This menu's assigned color_scheme FK
            2. ColorScheme flagged is_default
            3. PromoSettings singleton (legacy fallback)
        """
        scheme = self.color_scheme
        if scheme is None:
            scheme = ColorScheme.objects.filter(is_default=True).first()
        if scheme is not None:
            return scheme.as_dict()
        defaults = PromoSettings.load()
        return {
            'primary': defaults.promo_primary_color,
            'accent':  defaults.promo_accent_color,
            'text':    defaults.promo_text_color,
            'bg':      defaults.promo_bg_color,
        }

    def get_categories(self, category_type=None):
        """
        Returns assigned categories ordered by their MenuCategoryAssignment
        display_order. Optionally filter by category_type ('food'/'drinks').
        """
        qs = self.menu_category_assignments.select_related(
            'category'
        ).filter(
            category__is_active=True
        ).order_by('display_order')
        if category_type:
            qs = qs.filter(category__category_type=category_type)
        return [a.category for a in qs]


# =============================================================================
# MENU CATEGORY ASSIGNMENT
# (Menu declares which categories it uses, and in what order)
# =============================================================================

class MenuCategoryAssignment(models.Model):
    """
    Declares that a Menu uses a specific MenuCategory, and at what display order.

    This is the menu's scope declaration — "this menu shows these categories."
    Item placement within a category is handled by MenuItemCategoryAssignment.
    """
    menu = models.ForeignKey(
        Menu,
        on_delete=models.CASCADE,
        related_name='menu_category_assignments'
    )
    category = models.ForeignKey(
        MenuCategory,
        on_delete=models.CASCADE,
        related_name='menu_assignments'
    )
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Order in which this category appears within this menu."
    )

    class Meta:
        ordering = ['display_order']
        unique_together = ['menu', 'category']
        verbose_name = 'Menu Category Assignment'
        verbose_name_plural = 'Menu Category Assignments'

    def __str__(self):
        return f"{self.menu.title} → {self.category.name} (order {self.display_order})"


# =============================================================================
# MENU ITEM CATEGORY ASSIGNMENT
# (Places an item into a category, with per-placement order and overrides)
# =============================================================================

class MenuItemCategoryAssignment(models.Model):
    """
    Places a MenuItem into a MenuCategory at a specific position.

    Key design points:
    - The same item can appear in multiple categories across multiple menus.
    - order is per-placement, not per-item — Potstickers can be #3 in Starters
      and #1 in Happy Hour Food.
    - override_price replaces the item's base price for this placement only.
      The item's own price is never modified.
    - note is a short callout shown on the item in this placement only,
      e.g. 'Limited time!' or 'Half price during Happy Hour'.
    - Event menu visibility is controlled by role-based menu switching
      (Menu.role = event_food / event_drinks) — not per-item flags.
    """
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name='category_assignments'
    )
    category = models.ForeignKey(
        MenuCategory,
        on_delete=models.CASCADE,
        related_name='item_assignments'
    )
    subcategory = models.ForeignKey(
        MenuSubCategory,
        on_delete=models.SET_NULL,
        related_name='item_assignments',
        null=True,
        blank=True,
        help_text="Optional sub-grouping within the category (e.g. On Tap, Bottles & Cans)."
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order within this category. Independent per placement."
    )
    override_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text=(
            "Price for this placement only — overrides the item's base price. "
            "Used for Happy Hour, specials pricing, etc. "
            "Leave blank to use the item's standard price."
        )
    )
    note = models.CharField(
        max_length=200,
        blank=True,
        help_text=(
            "Short callout shown on this item in this placement only, "
            "e.g. 'Half price during Happy Hour' or 'Limited time!'."
        )
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Uncheck to hide this item from this category without removing the assignment."
    )

    class Meta:
        ordering = ['category__order', 'subcategory__order', 'order']
        unique_together = ['menu_item', 'category']
        verbose_name = 'Item Category Assignment'
        verbose_name_plural = 'Item Category Assignments'

    def __str__(self):
        price_note = f' (override ${self.override_price})' if self.override_price else ''
        return f"{self.menu_item.name} → {self.category.name}{price_note}"

    @property
    def display_price(self):
        """
        Returns the effective display price for this placement.
        Resolution order: override_price → item's own display_price logic.
        """
        if self.override_price is not None:
            from apps.menu.templatetags.menu_filters import currency
            return currency(self.override_price)
        return self.menu_item.display_price
