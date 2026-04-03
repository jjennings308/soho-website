from django.db import models
from django.core.validators import RegexValidator
from django.contrib.contenttypes.fields import GenericRelation


GOOGLE_FONTS_MAP = {
    '"Playfair Display", serif':        'Playfair+Display:ital,wght@0,400;0,600;0,700;0,900;1,400',
    '"Cormorant Garamond", serif':      'Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400',
    '"Libre Baskerville", serif':       'Libre+Baskerville:ital,wght@0,400;0,700;1,400',
    '"Inter", sans-serif':              'Inter:wght@300;400;500;600;700',
    '"Lato", sans-serif':               'Lato:ital,wght@0,300;0,400;0,700;1,300;1,400',
    '"Montserrat", sans-serif':         'Montserrat:wght@300;400;500;600;700',
    '"Open Sans", sans-serif':          'Open+Sans:ital,wght@0,300;0,400;0,600;1,400',
    '"Cinzel", serif':                  'Cinzel:wght@400;600;700',
    '"Oswald", sans-serif':             'Oswald:wght@300;400;500;600',
    '"Raleway", sans-serif':            'Raleway:wght@300;400;500;600;700',
    'Georgia, serif':                   None,
    '"Courier New", monospace':         None,
    '"Playwrite IE", sans-serif':       'Playwrite+IE:wght@100;200;300;400',
}

FONT_CHOICES = [
    ('Georgia, serif',                  'Georgia'),
    ('"Playfair Display", serif',       'Playfair Display'),
    ('"Cormorant Garamond", serif',     'Cormorant Garamond'),
    ('"Libre Baskerville", serif',      'Libre Baskerville'),
    ('"Inter", sans-serif',             'Inter'),
    ('"Lato", sans-serif',              'Lato'),
    ('"Montserrat", sans-serif',        'Montserrat'),
    ('"Open Sans", sans-serif',         'Open Sans'),
    ('"Cinzel", serif',                 'Cinzel (Elegant)'),
    ('"Oswald", sans-serif',            'Oswald'),
    ('"Raleway", sans-serif',           'Raleway'),
    ('"Courier New", monospace',        'Courier New'),
    ('"Playwrite IE", sans-serif',      'Playwrite IE'),
]


class Theme(models.Model):
    """
    A site theme. Controls the template directory and font stack.

    Font fields map to CSS variables injected at render time:
        --font-primary   → primary_font
        --font-secondary → secondary_font
        --font-accent    → accent_font

    All brand/palette colors are constants defined in theme.css — not
    admin-overridable. Promotional colors live in apps/menu/models.py.

    is_active — theme is enabled and available to be selected as active_theme.
                Only active themes can be set as SiteSettings.active_theme.
                Deactivating a theme that is currently active_theme will
                automatically clear SiteSettings.active_theme.
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    theme_directory = models.CharField(
        max_length=100,
        help_text="Folder name under templates/themes/ (e.g., 'classic', 'elegant')"
    )

    primary_font = models.CharField(
        max_length=100, choices=FONT_CHOICES, blank=True,
        help_text="--font-primary — headings and titles"
    )
    secondary_font = models.CharField(
        max_length=100, choices=FONT_CHOICES, blank=True,
        help_text="--font-secondary — body text and descriptions"
    )
    accent_font = models.CharField(
        max_length=100, choices=FONT_CHOICES, blank=True,
        help_text="--font-accent — prices, labels, and UI accents"
    )

    preview_image = models.ImageField(upload_to='theme_previews/', blank=True, null=True)
    media = GenericRelation(
        'media_manager.Media',
        related_query_name='theme',
    )
    is_active = models.BooleanField(
        default=False,
        help_text="Enable this theme so it can be selected as the site's active theme."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Theme'
        verbose_name_plural = 'Themes'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # If this theme is being deactivated and it's the current site theme,
        # clear SiteSettings.active_theme to avoid pointing at an inactive theme.
        if self.pk and not self.is_active:
            try:
                previous = Theme.objects.get(pk=self.pk)
                if previous.is_active:
                    # Was active, now being deactivated — clear if it's current
                    SiteSettings.objects.filter(active_theme=self).update(active_theme=None)
            except Theme.DoesNotExist:
                pass

        super().save(*args, **kwargs)

    @classmethod
    def get_active_theme(cls):
        """Returns the theme currently set as SiteSettings.active_theme."""
        return SiteSettings.load().active_theme

    def to_css_vars(self):
        """
        Returns a dict of { 'css-var-name': 'value' } for all non-blank font fields.
        Colors are constants in theme.css and are never included here.
        """
        mapping = {
            'font-primary':   self.primary_font,
            'font-secondary': self.secondary_font,
            'font-accent':    self.accent_font,
        }
        return {k: v for k, v in mapping.items() if v}

    def get_google_fonts(self):
        fonts = set()
        for field in [self.primary_font, self.secondary_font, self.accent_font]:
            if field and field in GOOGLE_FONTS_MAP and GOOGLE_FONTS_MAP[field]:
                fonts.add(GOOGLE_FONTS_MAP[field])
        return list(fonts)

    def get_google_fonts_url(self):
        font_families = self.get_google_fonts()
        if not font_families:
            return None
        families_param = '&family='.join(sorted(font_families))
        return f"https://fonts.googleapis.com/css2?family={families_param}&display=swap"

    def resolve_style_vars(self):
        """Delegates to to_css_vars(). Kept for call-site compatibility."""
        return self.to_css_vars()


class SiteSettings(models.Model):
    """
    Singleton (pk=1 always) — global site configuration.

    Editable copy (taglines, body text, hours, etc.) lives in apps/content
    and is managed via ContentSlot / ContentBlock. Use the content_tags
    template tag to render those blocks:

        {% load content_tags %}
        {% get_active_block 'hours_text' as block %}
        {{ block.body|safe }}

    Slots that correspond to removed fields:
        tagline             → 'site_tagline'
        description         → 'site_description'
        hours_text          → 'hours_text'
        short_about_text    → 'about_short'
        catering_text       → 'catering_body'
        maintenance_message → 'maintenance_message'
    """
    restaurant_name = models.CharField(max_length=200, default="Your Restaurant")

    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    email = models.EmailField(blank=True)

    address_line1 = models.CharField(max_length=200, blank=True)
    address_line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True, default="USA")

    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    yelp_url = models.URLField(blank=True)

    active_theme = models.ForeignKey(
        Theme,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='site_settings',
        limit_choices_to={'is_active': True},
        help_text="The theme currently in use. Only active themes can be selected."
    )

    meta_description = models.TextField(blank=True, max_length=160)
    meta_keywords = models.CharField(max_length=255, blank=True)

    logo = models.ImageField(upload_to='site/', blank=True, null=True)
    favicon = models.ImageField(upload_to='site/', blank=True, null=True)

    maintenance_mode = models.BooleanField(default=False)

    # ── Event / Game Day Overrides ────────────────────────────────────────────
    force_game_day_mode = models.BooleanField(
        default=False,
        help_text=(
            "Force limited menu mode on regardless of the event calendar. "
            "Useful for unexpected busy periods not on the schedule. "
            "Remember to uncheck this after the situation passes."
        )
    )
    force_full_menu = models.BooleanField(
        default=False,
        help_text=(
            "Force full menu on regardless of the event calendar or game day mode. "
            "Takes precedence over force_game_day_mode. "
            "Use this to override a calendar event that was cancelled or rescheduled."
        )
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Site Settings'
        verbose_name_plural = 'Site Settings'

    def __str__(self):
        return f"Site Settings - {self.restaurant_name}"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

# ── Banner ────────────────────────────────────────────────────────────────────

BANNER_COLOR_CHOICES = [
    ('bg-primary',      'Primary Background'),
    ('bg-secondary',    'Secondary Background'),
    ('bg-tertiary',     'Tertiary Background'),
    ('white',           'White'),
    ('steeler-black',   'Steeler Black'),
    ('steeler-gold',    'Steeler Gold'),
    ('text-primary',    'Primary Text'),
    ('text-secondary',  'Secondary Text'),
    ('text-tertiary',   'Tertiary Text'),
    ('gold-bright',     'Gold Bright'),
]


class Banner(models.Model):
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text="Referenced in the view, e.g. 'hero', 'grubhub'. Never change after deploy."
    )
    label = models.CharField(
        max_length=200,
        help_text="Admin-only label, e.g. 'Home Hero Banner'"
    )
    title = models.CharField(max_length=200, blank=True)
    content = models.TextField(
        blank=True,
        help_text="Boilerplate body copy shown when no seasonal ContentBlock is active."
    )
    bg_color = models.CharField(
        max_length=50,
        choices=BANNER_COLOR_CHOICES,
        default='bg-primary',
    )
    text_color = models.CharField(
        max_length=50,
        choices=BANNER_COLOR_CHOICES,
        default='text-primary',
    )
    image = models.ForeignKey(
        'media_manager.Media',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='banners',
        help_text="Background image pulled from the media manager."
    )
    image_opacity = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.40,
        help_text="0.00 = invisible, 1.00 = full opacity."
    )
    image_only = models.BooleanField(
        default=False,
        help_text="When checked, all text and buttons are hidden — image background only."
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['slug']
        verbose_name = 'Banner'
        verbose_name_plural = 'Banners'

    def __str__(self):
        return self.label

    def as_context(self, seasonal_body=None):
        """
        Returns the dict shape that banner_full.html expects.
        Pass seasonal_body (a safe HTML string) to overlay seasonal
        ContentBlock copy over the boilerplate content field.
        """
        return {
            'title': self.title,
            'content': seasonal_body if seasonal_body is not None else self.content,
            'bg_color': self.bg_color,
            'text_color': self.text_color,
            'image': self.image,
            'image_opacity': str(self.image_opacity),
            'image_only': self.image_only,
            'buttons': [
                b.as_dict()
                for b in self.buttons.filter(is_active=True).order_by('order')
            ],
        }


class BannerButton(models.Model):
    banner = models.ForeignKey(
        Banner,
        on_delete=models.CASCADE,
        related_name='buttons',
    )
    label = models.CharField(max_length=100)
    href = models.CharField(max_length=500)
    bg_color = models.CharField(
        max_length=50,
        choices=BANNER_COLOR_CHOICES,
        default='bg-secondary',
    )
    text_color = models.CharField(
        max_length=50,
        choices=BANNER_COLOR_CHOICES,
        default='text-primary',
    )
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']
        verbose_name = 'Button'
        verbose_name_plural = 'Buttons'

    def __str__(self):
        return f"{self.banner.label} — {self.label}"

    def as_dict(self):
        return {
            'label': self.label,
            'href': self.href,
            'bg_color': self.bg_color,
            'text_color': self.text_color,
        }
        
# ── Panel Side ───────────────────────────────────────────────────────────────

PANEL_MODE_CHOICES = [
    ('text',  'Text & Button'),
    ('image', 'Full Image'),
    ('map',   'Google Maps Embed')
]


class PanelSide(models.Model):
    """
    One side of a 50/50 split section. Two PanelSide records are paired
    in the view as left= and right= when including 50_50.html.

    mode='image' → renders as a full-bleed image (full_img dict).
    mode='text'  → renders title, content, optional button (text dict).

    Image panels can be reused across pages by referencing the same slug
    in multiple views — pair with a different text panel each time.
    """
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text="Referenced in the view, e.g. 'front-door-image', 'about-text'. Never change after deploy."
    )
    label = models.CharField(
        max_length=200,
        help_text="Admin-only label, e.g. 'Front Door Image Panel'"
    )
    mode = models.CharField(
        max_length=10,
        choices=PANEL_MODE_CHOICES,
        default='text',
        help_text="Image: full-bleed photo. Text: title, copy, and optional button."
    )

    # ── Shared ────────────────────────────────────────────────────────────────
    bg_color = models.CharField(
        max_length=50,
        choices=BANNER_COLOR_CHOICES,
        default='bg-primary',
        help_text="Background color. For image panels, shows while image loads."
    )

    # ── Text mode fields ──────────────────────────────────────────────────────
    title = models.CharField(max_length=200, blank=True)
    content_slot = models.ForeignKey(
        'content.ContentSlot',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='panel_sides',
        help_text="Optional ContentSlot for body copy. Active block is resolved at render time."
    )
    text_color = models.CharField(
        max_length=50,
        choices=BANNER_COLOR_CHOICES,
        default='text-primary',
    )
    button_label = models.CharField(max_length=100, blank=True)
    button_href = models.CharField(max_length=500, blank=True)
    button_bg_color = models.CharField(
        max_length=50,
        choices=BANNER_COLOR_CHOICES,
        default='bg-secondary',
        blank=True,
    )
    button_text_color = models.CharField(
        max_length=50,
        choices=BANNER_COLOR_CHOICES,
        default='text-primary',
        blank=True,
    )

    # ── Image mode fields ─────────────────────────────────────────────────────
    image = models.ForeignKey(
        'media_manager.Media',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='panel_sides',
        help_text="Full-bleed image. Used when mode is 'image'."
    )
    image_fallback_url = models.CharField(
        max_length=500,
        blank=True,
        help_text="Static fallback path if no media manager image is set, e.g. '/static/img/front_door.webp'."
    )

    # ── Horizontal Align fields ─────────────────────────────────────────────────────
    PANEL_HALIGN_CHOICES = [
        ('flex-start',  'Left'),
        ('center', 'Center'),
        ('flex-end',    'Right'),
    ]
    
    HALIGN_TO_TEXT = {
        'flex-start': 'left',
        'center':     'center',
        'flex-end':   'right',
    }
    
    horizontal_align = models.CharField(
        max_length=12,
        choices=PANEL_HALIGN_CHOICES,
        default='flex-start',
        blank=True,
)

    # ── Vertical Align fields ─────────────────────────────────────────────────────
    PANEL_ALIGN_CHOICES = [
        ('flex-start',  'Top'),
        ('center',      'Middle'),
        ('flex-end',    'Bottom'),
    ]

    vertical_align = models.CharField(
        max_length=12,
        choices=PANEL_ALIGN_CHOICES,
        default='center',
        blank=True,
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['slug']
        verbose_name = 'Panel Side'
        verbose_name_plural = 'Panel Sides'

    def __str__(self):
        return self.label

    def as_dict(self):
        """
        Returns the dict shape that 50_50.html expects for one side.
        Resolves the active ContentBlock from content_slot if set.
        """
        if self.mode == 'image':
            if self.image:
                img_src = self.image.file.url
                alt = self.image.alt_text or ''
            elif self.image_fallback_url:
                img_src = self.image_fallback_url
                alt = ''
            else:
                img_src = ''
                alt = ''
            return {
                'full_img': {
                    'img_src': img_src,
                    'alt': alt,
                    'bg_color': self.bg_color,
                }
                        }

        if self.mode == 'map':
            from urllib.parse import quote
            settings = SiteSettings.load()
            parts = [
                settings.address_line1,
                settings.address_line2,
                settings.city,
                settings.state,
                settings.zip_code,
            ]
            address_str = ', '.join(p for p in parts if p)
            encoded = quote(address_str)
            return {
                'map': {
                    'address': address_str,
                    'embed_url': f"https://maps.google.com/maps?q={encoded}&output=embed",
                    'directions_url': f"https://maps.google.com/?q={encoded}",
                    'bg_color': self.bg_color,
                }
            }
                        
        # text mode
        content = ''
        if self.content_slot:
            block = self.content_slot.get_active_block()
            if block:
                content = block.body

        result = {
            'title': self.title,
            'content': content,
            'bg_color': self.bg_color,
            'text_color': self.text_color,
            'vertical_align': self.vertical_align,
            'horziontal_align': self.horizontal_align,
            'text_align': self.HALIGN_TO_TEXT.get(self.horizontal_align, 'left'),
        }

        if self.button_label and self.button_href:
            result['button'] = {
                'label': self.button_label,
                'href': self.button_href,
                'bg_color': self.button_bg_color,
                'text_color': self.button_text_color,
            }

        return result