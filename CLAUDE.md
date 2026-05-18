# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack

Django 5.0, PostgreSQL, Tailwind CSS 3 (CLI build), Alpine.js (vendored at `static/js/alpine.min.js`). No webpack/bundler — Tailwind is compiled directly via its CLI.

## Commands

### Django dev server
```bash
DJANGO_SETTINGS_MODULE=config.settings.development python manage.py runserver
```

### Tailwind CSS (watch during development)
```bash
npm run dev
# builds static/src/input.css → static/dist/output.css
```

### Tailwind CSS (production build)
```bash
npm run build
```

### Database migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Run tests
```bash
python manage.py test
python manage.py test apps.core  # single app
```

### Collect static files
```bash
python manage.py collectstatic
```

## Environment setup

Copy `.env.example` to `.env`. Required variables:
- `SECRET_KEY`
- `DB_PASSWORD` (PostgreSQL; dev also uses `DB_NAME`, `DB_USER`, `DB_HOST`, `DB_PORT`)
- `DJANGO_SETTINGS_MODULE` — use `config.settings.development` locally

Both dev and prod use PostgreSQL. SQLite config is commented out in the settings files.

## Architecture

### Settings split
`config/settings/base.py` → `development.py` / `production.py`. Settings module is selected via `DJANGO_SETTINGS_MODULE`.

### Apps

| App | Responsibility |
|-----|---------------|
| `apps.core` | Site settings singleton, page views, banners, 50/50 panels, home page |
| `apps.menu` | Menu items, categories, menus, promotions; full/limited menu mode |
| `apps.content` | Content slot/block CMS system for editable copy |
| `apps.events` | Event calendar driving limited-menu mode (game days, etc.) |
| `apps.gallery` | Photo/video gallery with category filtering and lightbox |

Third-party app `media_manager` is loaded from a private GitHub package (`jjennings308/django-media-manager`).

### Base models (`apps/core/models.py`)

All domain models inherit from one of:
- `TimeStampedModel` — adds `created_at` / `updated_at`
- `ScheduledModel(TimeStampedModel)` — adds `is_active`, `active_from`, `active_until`; exposes `.objects.active()` queryset and `.is_currently_active` property
- `RecurrenceMixin` — adds `days_of_week` JSONField; use alongside `ScheduledModel`

### Content system (`apps/content/`)

Copy is managed through a slot/block pattern:
- **`ContentSlot`** — a named placeholder referenced in templates by slug (e.g. `about_header`)
- **`ContentBlock`** — a versioned, schedulable piece of rich-text content assigned to a slot; only one block per slot is active at a time
- **`ContentGroup`** — groups related slots into a named surface (e.g. a banner); fetched via `{% get_content_group 'slug' as group %}` in 3 queries with all slots+blocks prefetched

Template usage:
```django
{% load content_tags %}
{% get_active_block 'about_header' as block %}
{% if block %}<h1>{{ block.body|safe }}</h1>{% endif %}

{% render_content_block 'catering_body' css_class='prose' %}

{% get_content_group 'hero_banner' as group %}
{% for slot in group.title_slots %}...{% endfor %}
```

### Menu mode (`apps/menu/`, `apps/events/`)

The menu has two modes — **full** and **limited** — controlled by `EventDay.get_current_menu_mode()`:
1. `SiteSettings.force_full_menu` → full (highest priority)
2. `SiteSettings.force_game_day_mode` → limited
3. Active `EventDay` with `limited_menu=True` and within lead time → limited
4. Default → full

In limited mode, only `MenuItemCategoryAssignment` records with `available_game_day=True` are shown. Views pass `limited_menu=True/False` into context; templates filter accordingly.

### Menu data model

Items (`MenuItem`) are a shared library — not owned by any menu. Placement is via two through-tables:
- `MenuCategoryAssignment` — declares which categories a `Menu` shows, and in what order
- `MenuItemCategoryAssignment` — places an item into a category with per-placement `order`, `override_price`, `note`, and `available_game_day`

The same item can appear in multiple categories at different prices.

### Page components

`Banner` and `PanelSide` models (in `apps.core`) drive reusable page sections. Views call `get_banner(slug)` and `get_panel_side(slug)` from `apps/core/utils.py`, which return context dicts consumed by `banner_full.html` and `50_50.html` partials.

### Context processors

`apps.core.context_processors.site_settings` injects `site_settings`, `restaurant_name`, `restaurant_phone`, `restaurant_email`, and `restaurant_address` into every template automatically.

### Theming

Colors are CSS custom properties (`--color-bg-primary`, etc.) referenced in `tailwind.config.js` as `brand.*` and `text.*` utility classes. Color choices for admin-editable fields use slug strings like `bg-primary` / `text-secondary` that map to these variables.

---

## Gallery app (`apps/gallery/`)

### Decision log
- Self-contained app — does NOT use `django-media-manager` models. The package is present in the project for other uses but the gallery manages its own files via Django's standard `ImageField`. Reason: `media_manager.Media` is user-scoped and carries album/moderation complexity not needed for Phase 1. When Ionos S3 storage is configured, the gallery `ImageField` upload path will point to the same S3 backend via `DEFAULT_FILE_STORAGE`.
- Lightbox: **GLightbox** (MIT license, ~10KB, no jQuery, mobile swipe support, handles images and video). Loaded via CDN in the gallery template.
- Grid: 4-column, loads 8 items (2 rows) at a time. "Load more" via simple JS fetch or HTMX if HTMX is added to the project.
- Hover effect: CSS scale transform via Tailwind (`group` / `group-hover:scale-110 transition-transform`) — no JS required.
- Category filtering: pill/tab nav at top of gallery page; "All" tab always present. Filtering triggers a page reload or HTMX swap — do NOT construct Tailwind class names dynamically at runtime (use inline `style` with CSS `var()` instead, per project convention).

### Models

#### `GalleryCategory`
Inherits `TimeStampedModel`.

| Field | Type | Notes |
|-------|------|-------|
| `name` | CharField(100) | Display name |
| `slug` | SlugField(unique=True) | Auto-generated; used in URL filter param |
| `description` | CharField(255, blank=True) | Optional subtitle shown on gallery page |
| `display_order` | PositiveIntegerField(default=0) | Controls tab order |
| `is_published` | BooleanField(default=True) | Unpublished = hidden from public; still visible in admin |

Seeded categories (in display order):
1. `food` — Food
2. `sides` — Sides
3. `desserts` — Desserts
4. `drinks` — Drinks
5. `interior` — Interior
6. `exterior` — Exterior
7. `atmosphere` — Atmosphere

#### `GalleryItem`
Inherits `TimeStampedModel`.

| Field | Type | Notes |
|-------|------|-------|
| `category` | FK → GalleryCategory | `on_delete=SET_NULL, null=True, blank=True` |
| `media_type` | CharField, choices: `image` / `video` | Default `image` |
| `image` | ImageField(upload_to='gallery/') | Used when `media_type='image'` |
| `video_url` | URLField(blank=True) | Used when `media_type='video'`; GLightbox auto-detects YouTube/Vimeo/TikTok/MP4 |
| `caption` | CharField(255, blank=True) | Shown in lightbox overlay |
| `display_order` | PositiveIntegerField(default=0) | Order within category |
| `is_published` | BooleanField(default=True) | Unpublished = hidden from public |

Default ordering: `['category__display_order', 'display_order']`

**Phase 2 fields to add when customer submissions open:**
```python
submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
is_approved = models.BooleanField(default=False)
is_flagged = models.BooleanField(default=False)
flagged_reason = models.TextField(blank=True)
```

### Admin (`apps/gallery/admin.py`)

- `GalleryCategoryAdmin`: `list_display` = name, slug, display_order, is_published, item count. `list_editable` = display_order, is_published.
- `GalleryItemAdmin`: `list_display` = thumbnail preview, caption, category, media_type, display_order, is_published. `list_filter` = category, media_type, is_published. `search_fields` = caption. `list_editable` = display_order, is_published. Image thumbnail rendered via `readonly_fields`.

### URL / view

- URL: `/gallery/` with optional `?category=<slug>` filter param
- View: `GalleryView(ListView)` — filters `GalleryItem.objects.filter(is_published=True)` by category slug if provided; passes all published categories to context for the tab nav
- Use `select_related('category')` on the queryset
- Pagination: 8 items per page
- URL name: `gallery:index`

### Template structure

```
apps/gallery/templates/gallery/
    index.html          # main gallery page
    partials/
        grid.html       # the photo grid (reused for "load more" if HTMX added)
        item_card.html  # single photo card with hover effect
```

### GLightbox integration

Load via CDN in `index.html` (or base template if used elsewhere):
```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/glightbox/dist/css/glightbox.min.css">
<script src="https://cdn.jsdelivr.net/npm/glightbox/dist/js/glightbox.min.js"></script>
```

Initialize after DOM ready:
```html
<script>
  const lightbox = GLightbox({ selector: '.glightbox' });
</script>
```

Each item card anchor:
```html
<a href="{{ item.image.url }}"
   class="glightbox"
   data-gallery="soho-gallery"
   data-description="{{ item.caption }}">
  <img src="{{ item.image.url }}" alt="{{ item.caption }}">
</a>
```

For video items, `href` is `item.video_url` — GLightbox auto-detects and renders inline player.

### Management command

`python manage.py seed_gallery_categories`

Creates the 7 seeded categories if they don't already exist. Safe to re-run (uses `get_or_create`).

### Upload workflow (initial photo migration)

20 photos downloaded from the existing GoDaddy site into `soho_gallery_originals/` on the dev machine. All are JPGs (iPhone VSCO-processed). To load them into the new gallery:

1. Upload files to the VPS media directory: `scp soho_gallery_originals/* user@209.46.125.163:/var/www/soho/media/gallery/`
2. Use Django admin to create `GalleryItem` records and assign categories, OR write a one-off management command to bulk-create them.

### Future: Ionos S3 storage

When Ionos S3 is configured, update `production.py`:
```python
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_ACCESS_KEY_ID = env('IONOS_ACCESS_KEY')
AWS_SECRET_ACCESS_KEY = env('IONOS_SECRET_KEY')
AWS_STORAGE_BUCKET_NAME = env('IONOS_BUCKET_NAME')
AWS_S3_ENDPOINT_URL = env('IONOS_S3_ENDPOINT')  # Ionos S3-compatible endpoint
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = 'public-read'
```

No model changes required — `ImageField` uses `DEFAULT_FILE_STORAGE` automatically.
