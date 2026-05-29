# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack

Django 6.0, PostgreSQL, Tailwind CSS 3 (CLI build), Alpine.js (vendored at `static/js/alpine.min.js`). No webpack/bundler — Tailwind is compiled directly via its CLI.

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

### direnv (dev machine)

This project uses `direnv` to auto-set `DJANGO_SETTINGS_MODULE` when entering the project directory. A `.envrc` file at the project root contains:

```bash
export DJANGO_SETTINGS_MODULE=config.settings.development
```

If `.envrc` is blocked, run `direnv allow` from the project root. With direnv active, all `manage.py` commands work without passing `--settings` explicitly. The PostgreSQL service for this project runs on port **5433**.

## Architecture

### Settings split
`config/settings/base.py` → `development.py` / `production.py`. Settings module is selected via `DJANGO_SETTINGS_MODULE`.

### Apps

| App | Responsibility |
|-----|---------------|
| `apps.core` | Site settings singleton, page views, banners, 50/50 panels, home page, color schemes, site popup, event inquiries |
| `apps.menu` | Menu items, categories, menus, promotions; full/limited menu mode |
| `apps.content` | Content slot/block CMS system for editable copy |
| `apps.events` | Event calendar driving limited-menu mode (game days, etc.) |
| `apps.media` | Site-wide media library — images and video. Drives the public `/gallery/` page and supplies media to banners, menu items, categories, popups, and any other use point. Replaces `apps.gallery`. |
| `apps.members` | Mailing list, member accounts, future photo submissions |
| `apps.reviews` | Third-party and member reviews with moderation and aggregate ratings |
| `apps.bookings` | **Planned — not yet built.** Private event lifecycle: inquiry → booking → planning → confirmed → completed. Replaces `EventInquiry` in `apps.core` when built. Covers customer communications, audit trail, templated emails, custom event menus, and staff assignment. |
| `apps.staff` | Purpose-built staff portal — no Django admin required for day-to-day ops |

`django-media-manager` has been removed from the project — do not reference it.

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

### Design system enforcement — CRITICAL

**The single most important rule for all template work:**

Page templates (`about.html`, `home.html`, etc.) must NEVER contain inline color styles, hardcoded CSS variable references, or layout decisions that belong in a component template. All color and presentation logic lives in the component templates.

**The correct pattern:**
```django
{# about.html — correct #}
{% include "core/components/banner_full.html" with banner=about_banner %}
{% include "core/components/50_50.html" with left_panel=left_panel right_panel=right_panel %}
```

**The forbidden pattern — never do this in a page template:**
```django
{# about.html — WRONG #}
<section style="background-color: var(--color-bg-primary);">
  <h1 style="color: var(--color-text-primary);">About SoHo</h1>
</section>
```

**Rules Claude Code must follow without exception:**

- Color values (`var(--color-bg-primary)`, `var(--color-text-secondary)`, hex codes, etc.) must NEVER appear in page-level templates. They belong only in component templates (`banner_full.html`, `50_50.html`, `_panel_side.html`) where they are driven by model fields (`banner.bg_color`, `panel.text_color`).
- If a section needs color control, it must be a `Banner` or `PanelSide` record — not an inline-styled `<section>` tag in the page template.
- If the existing component templates cannot accommodate a layout need, raise it as a question rather than working around them with inline styles. The fix is to extend the component template, not bypass it.
- `btn btn-primary`, `btn btn-secondary`, `btn btn-ghost` are the only button styles. Never inline-style a button.
- When Claude Code is tempted to write `style="background-color:..."` or `style="color:..."` in a page template, it must stop and use a Banner or PanelSide component instead.
- Structural layout (padding, grid, flex) may appear in page templates. Color never does.

**How to check your own work:** Before committing any template change, grep the page template for `background-color`, `color:`, and `var(--color-`. If any appear outside a component template, they are wrong.

```bash
grep -n "background-color\|color:" templates/about.html
grep -n "background-color\|color:" templates/home.html
```

The result should be zero matches in page templates. All matches should live only in component templates and `theme.css`.

### Menu color rules — CRITICAL

Menu templates have an additional specific rule about color sources:

**Only `menu_type='promo'` menus may use custom colors.** All other menu types use standard theme variables exclusively.

| menu_type | Color source | How |
|-----------|-------------|-----|
| `promo` | `PromoColorScheme` | `menu.resolve_colors()` → `--color-promo-*` CSS vars |
| `food` | Standard theme | `var(--color-bg-*)`, `var(--color-text-*)` only |
| `drink` | Standard theme | Same as above |
| `weekly_specials` | Standard theme | Same as above |
| `event_food` | Standard theme | Same as above |
| `event_drinks` | Standard theme | Same as above |

**The `--color-promo-*` compatibility shim** — `homepage_item_card.html` and `promo_subcat_card.html` use `var(--color-promo-*)` CSS variables internally. Non-promo menu sections that reuse these card templates must map those variables to standard theme colors on the section wrapper:

```django
{#
  Color note: --color-promo-* mapped to STANDARD THEME COLORS.
  Compatibility shim so card templates can be reused unchanged.
  Do NOT replace with custom colors — weekly_specials uses site branding only.
#}
<section style="
  --color-promo-primary: var(--color-text-heading);
  --color-promo-accent:  var(--color-text-accent);
  --color-promo-text:    var(--color-text-primary);
  --color-promo-bg:      var(--color-bg-secondary);
  background-color: var(--color-bg-secondary);
">
```

This mapping must NEVER be replaced with hardcoded hex values, custom color picks, or any value not drawn from the standard `--color-*` theme variables.

**If Claude Code is tempted to choose colors for a non-promo menu** — stop. The colors are not a choice. They are always the standard theme variables listed above. Raise a question if the layout requires something that can't be achieved with theme variables.

---

### Menu mode (`apps/menu/`, `apps/events/`)

The menu has two modes — **standard** and **event** — controlled by `EventDay.get_current_menu_mode()`:
1. `SiteSettings.force_full_menu` → standard (highest priority)
2. `SiteSettings.force_game_day_mode` → event
3. Active `EventDay` with `limited_menu=True` and within lead time → event
4. Default → standard

In event mode, views switch to the menus with `role='event_food'` and `role='event_drinks'` instead of `role='default_food'` and `role='default_drinks'`. See the **Menu restructure** section for full detail.

**Note:** `available_game_day` on `MenuItemCategoryAssignment` is deprecated and being removed — do not use it in new code. Item-level filtering is replaced by role-based menu switching.

### Menu data model

Items (`MenuItem`) are a shared library — not owned by any menu. Placement is via two through-tables:
- `MenuCategoryAssignment` — declares which categories a `Menu` shows, and in what order
- `MenuItemCategoryAssignment` — places an item into a category with per-placement `order`, `override_price`, `note`. The `available_game_day` field on this model is deprecated — do not reference it in new code.

The same item can appear in multiple categories at different prices.

`MenuCategory` has a `display_name` field (see Menu enhancements section) — use it in templates instead of `category.name` for public-facing display. `Weekly specials` is a first-class `menu_type` with date bounds — see Menu enhancements section.

### Page components

`Banner` and `PanelSide` models (in `apps.core`) drive reusable page sections. See the **Banner and PanelSide restructure** section for full model and template spec.

**Key architectural principle:** `Banner` and `PanelSide` are presentation wrappers only. Content (text, titles, buttons) lives in `ContentGroup` → `ContentSlot` → `ContentBlock`. Colors, images, and layout settings live on the display component. This separation allows the same `ContentGroup` to be assigned to a banner today and a panel tomorrow with no content duplication.

**`as_context()` is removed** from `Banner` and `PanelSide`. Templates access content directly via `banner.content_group.all_slots`. Do not re-implement `as_context()`.

**Button system (`apps/core/templatetags/ui_tags.py` + `button.html`):**
- `render_button(button)` accepts a dict with `label`, `href`, `bg_color`, `text_color`, and optionally `x_on_click`.
- If `x_on_click` is set on the button dict, `button.html` renders a `<button @click="...">` instead of an `<a>` tag — use this to open Alpine modals from `PanelSide` buttons injected in views.
- Example: `catering_right['button'] = {'label': 'Inquire', 'x_on_click': 'inquiryOpen = true'}`
- Button slots in ContentBlocks use `block.button_url == '#open-contact'` sentinel pattern — see content system section.

**CSS button classes (`static/src/input.css`):**
- `btn btn-primary` — gold fill; hover goes transparent with gold border/text.
- `btn btn-secondary` / `btn btn-outline` — same definition (gold outline); hover fills bright gold with lift + shadow.
- `btn btn-ghost` — white outline for use on dark/image backgrounds.
- Always use these classes. Never inline-style buttons.

### `SiteSettings` notable fields

Key fields beyond the obvious (name, contact, social): `map_embed_url` (URLField) — Google Maps embed URL shown on the contact/about page. When blank, the embed URL is derived from the address. Editable only via Django admin (not the staff portal) because it rarely changes and the format is sensitive. `reservations_url`, `notification_email`, `force_game_day_mode`, `force_full_menu`, `maintenance_mode`.

### Context processors

`apps.core.context_processors.site_settings` injects `site_settings`, `restaurant_name`, `restaurant_phone`, `restaurant_email`, and `restaurant_address` into every template automatically.

### Theming

Colors are CSS custom properties (`--color-bg-primary`, etc.) referenced in `tailwind.config.js` as `brand.*` and `text.*` utility classes. Color choices for admin-editable fields use slug strings like `bg-primary` / `text-secondary` that map to these variables.

### Color schemes (`apps/core` — `ColorScheme` model)

`ColorScheme` was moved from `apps.menu` to `apps.core` (migration `core/0032`). It is shared across promo menus and site popups. Fields: `name`, `primary_color`, `accent_color`, `text_color`, `bg_color`, `is_default`. Only one scheme can have `is_default=True` — the `save()` method enforces this. Import from `apps.core.models`.

### Site popup (`SitePopup` model in `apps.core`)

Singleton-style: only one popup is active at a time (`get_active()` class method). Fields include `title`, `body`, `cta_text`, `cta_url`, `show_subscribe_form`, `primary_color`, `color_scheme` FK, `delay_seconds`, `is_active`. The popup uses `sessionStorage` (not `localStorage`) for per-session dismissal. A separate `localStorage` key `soho_subscribed` suppresses the popup permanently once a user subscribes or confirms — set on form success, already-subscribed response, and the confirmation page.

### Event inquiries (`EventInquiry` model in `apps.core`)

Captures event booking requests from the public site. Fields: `name`, `email`, `phone`, `preferred_contact`, `event_type`, `guest_count`, `preferred_date`, `menu_preference`, `message`, `status` (new/contacted/closed). Managed via the staff portal inquiries section.

---

## ⚠️ `apps/gallery/` — DEPRECATED, DO NOT EXTEND

`apps.gallery` is being replaced by `apps.media`. Do not add features, models, or views to `apps.gallery`. See the **Media app** section below for the full spec.

**Migration status:** `apps.gallery` exists on disk and in the database. The physical image files in `media/gallery/` and subdirectories are the authoritative source — they are kept. The existing `GalleryItem` and `GalleryCategory` database records will be dropped and rebuilt under the new `apps.media` models. The public `/gallery/` URL is preserved — it moves to `apps.media` views.

**What to do with `apps.gallery` during the build:**
- Do not delete it until `apps.media` is fully built and verified
- Run both apps simultaneously during transition
- Once `apps.media` is live and all files re-imported, delete `apps.gallery` entirely (models, views, urls, templates, migrations)

---

## Members app (`apps/members/`)

### Decision log

- Named `members` not `newsletter` or `maillist` — the app will grow to cover member accounts and photo submissions; the name reflects the full scope not just Phase 1.
- **Phase 1:** Mailing list only. `SoHoMember` is not linked to a Django `User` yet.
- **Phase 2:** Account activation — Django `User` linked optionally to `SoHoMember` via `OneToOneField(null=True)`. Members who only want emails never need a login.
- **Phase 3:** Customer photo submissions — `GallerySubmission` model, moderation queue in admin.
- Email sending uses Django's standard `send_mail()` and `EmailMessage` throughout — never SMTP-specific code. This keeps the backend swappable: currently Option A (own mail server via `EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'`); future Option C (Brevo/Mailgun via `django-anymail`) is a settings-only change, no code changes required.
- All outbound site email (verification, notifications, newsletters, password resets) routes through `EMAIL_BACKEND` — one setting controls everything.

### Email verification — double opt-in

Signup flow:
1. Customer submits email via subscribe form → `SoHoMember` created with `is_active=False`
2. Verification email sent immediately: *"It looks like you signed up for our email list — please confirm."* Contains a confirm link only (no reject link — anyone who didn't sign up simply ignores the email; a reject link would be a harassment vector).
3. Customer clicks confirm → `is_active=True`, `confirmed_at` set
4. Unconfirmed records older than 7 days are excluded from all sends; a management command can purge them periodically.

### Models

#### `SoHoMember`
Inherits `TimeStampedModel`.

| Field | Type | Notes |
|-------|------|-------|
| `email` | EmailField(unique=True) | Primary identifier |
| `first_name` | CharField(100) | Required at signup |
| `last_name` | CharField(100, blank=True) | Optional |
| `is_email_subscribed` | BooleanField(default=True) | False after unsubscribe |
| `is_active` | BooleanField(default=False) | True after email confirmation |
| `confirmation_token` | UUIDField(default=uuid.uuid4, unique=True) | Used in confirm URL |
| `unsubscribe_token` | UUIDField(default=uuid.uuid4, unique=True) | Used in unsubscribe URL; separate from confirm token |
| `confirmed_at` | DateTimeField(null=True, blank=True) | Set on confirmation |
| `user` | OneToOneField(User, null=True, blank=True) | Phase 2 — linked Django auth user; add then, not now |

#### `Newsletter`
Inherits `TimeStampedModel`. Used to compose and track email sends.

| Field | Type | Notes |
|-------|------|-------|
| `subject` | CharField(200) | Email subject line |
| `body` | CKEditor5Field | Rich text body; composed in Django admin |
| `sent_at` | DateTimeField(null=True, blank=True) | Null = draft; set when send is triggered |
| `recipient_count` | PositiveIntegerField(default=0) | Recorded at send time |
| `sent_by` | FK → User(null=True) | Staff user who triggered the send |

### Admin (`apps/members/admin.py`)

#### `SoHoMemberAdmin`
- `list_display`: email, first_name, last_name, is_active, is_email_subscribed, confirmed_at, created_at
- `list_filter`: is_active, is_email_subscribed
- `search_fields`: email, first_name, last_name
- `readonly_fields`: confirmation_token, unsubscribe_token, confirmed_at
- Bulk actions: `mark_active`, `mark_inactive`, `unsubscribe_selected`
- Export action: CSV export of active subscribers (for backup / future Mailchimp migration)

#### `NewsletterAdmin`
- `list_display`: subject, sent_at, recipient_count, sent_by, created_at
- `readonly_fields`: sent_at, recipient_count, sent_by
- Custom admin action: **"Send to all active subscribers"** — only available on draft newsletters (sent_at is null). Sends via Django's `send_mail()`, records sent_at, recipient_count, sent_by. Filters on `is_active=True` and `is_email_subscribed=True`. Does NOT use a task queue in Phase 1 — acceptable for small lists. Add Celery if list exceeds ~500 and send times become a problem.

### URLs / views

| URL | View | Name | Notes |
|-----|------|------|-------|
| `/subscribe/` | `SubscribeView` | `members:subscribe` | POST only; renders inline success/error |
| `/subscribe/confirm/<uuid:token>/` | `ConfirmView` | `members:confirm` | GET; activates member |
| `/unsubscribe/<uuid:token>/` | `UnsubscribeView` | `members:unsubscribe` | GET; sets is_email_subscribed=False |

Subscribe form is embedded in other pages — not a standalone page. `SubscribeView` returns a partial HTML response for Alpine.js swap. Currently embedded in `templates/partials/_footer.html` inside `<div data-subscribe-widget>`. To embed elsewhere: `{% include 'members/partials/subscribe_form.html' %}` inside a `<div data-subscribe-widget>` container.

### Template structure

```
apps/members/templates/members/
    emails/
        confirm_subscription.html   # verification email (HTML)
        confirm_subscription.txt    # verification email (plain text)
        newsletter.html             # newsletter send wrapper
    partials/
        subscribe_form.html         # embeddable signup widget
    confirm_success.html            # shown after clicking confirm link
    unsubscribe_success.html        # shown after unsubscribing
```

### Email settings — current state (as implemented)

`base.py` sets:
```python
DEFAULT_FROM_EMAIL = 'SoHo Pittsburgh <noreply@sohopittsburgh.com>'
EMAIL_SUBJECT_PREFIX = ''
```

`development.py` sets:
```python
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# prints emails to terminal — no real sends in dev
```

`production.py` hardcodes the SMTP backend and overrides `DEFAULT_FROM_EMAIL` to match the authenticated SMTP user (mail servers reject sends where From ≠ authenticated account):
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
DEFAULT_FROM_EMAIL = config('EMAIL_HOST_USER')  # must match SMTP auth user
EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
```

`.env` on the VPS holds `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, etc. Do NOT set `EMAIL_BACKEND` in `.env` — production.py hardcodes smtp; development.py hardcodes console.

**Future Option C (Brevo via django-anymail) — settings-only swap, no code changes:**
```python
# pip install django-anymail[brevo]
EMAIL_BACKEND = 'anymail.backends.brevo.EmailBackend'
ANYMAIL = {'BREVO_API_KEY': env('BREVO_API_KEY')}
```

### Phase 2 — Account activation (future, do not build yet)

When photo submissions open, members can activate a login:
- Member visits `/members/activate/` and enters their email
- If a `SoHoMember` exists: send a set-password link; on completion create Django `User` and link via `SoHoMember.user`
- If no record exists: create `SoHoMember` + offer email subscription opt-in during activation
- Members who only want emails are never prompted to activate

### Phase 3 — Customer photo submissions (future, do not build yet)

`GallerySubmission` model (location TBD — `apps.members` or `apps.gallery`):

```python
class GallerySubmission(TimeStampedModel):
    member = models.ForeignKey('members.SoHoMember', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='submissions/')
    caption = models.CharField(max_length=255, blank=True)
    status = models.CharField(choices=['pending','approved','rejected'], default='pending')
    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
```

Admin "Approve" action promotes the submission to a `GalleryItem` and notifies the member by email via `send_mail()`.

Pre-screening plan:
- Phase 3 launch: file type + size validation only
- If abuse occurs: add AWS Rekognition or Google Vision API for automated content moderation

---

## Staff portal (`apps/staff/`)

Purpose-built dashboard for customer's staff. Intentionally simpler than Django admin — only exposes day-to-day operations.

### Access

- URL: `/staff/` — **not linked anywhere in the public site**. Staff navigate there directly.
- Login: `/staff/login/` — uses Django's built-in auth. Requires `is_staff=True` on the user account.
- `StaffRequiredMixin` enforces `is_staff` on every view; non-staff authenticated users get 403.

### Sections

| URL | What it does |
|-----|-------------|
| `/staff/` | Dashboard — menu mode, subscriber count, draft newsletters, unpublished photos, new inquiries, popup status, today's events, upcoming events, promo menus panel |
| `/staff/menu-mode/` | Toggle menu mode: Automatic / Force Full / Force Game Day. POSTs to `SiteSettings` |
| `/staff/events/` | List upcoming + last 20 past events; add, edit, activate/deactivate, delete |
| `/staff/media/` | Media library — thumbnail grid; publish/hide toggle; upload; import from disk; edit (name, category, alt text); page-retention via `?next=` |
| `/staff/menu/items/` | Menu item list with filters (name, availability, flags); Images button per row |
| `/staff/menu/items/<pk>/images/` | Formset to assign, order, and set primary image for a menu item |
| `/staff/newsletter/` | List drafts and sent newsletters; compose new draft; review and send |
| `/staff/popups/` | List, add, edit, delete site popups |
| `/staff/inquiries/` | List event inquiries; filter by status; update status (new/contacted/closed); delete |
| `/staff/settings/` | Edit `SiteSettings` (notification email, phone, reservations URL, etc.); manage color schemes (add/edit/delete) |

**Media library page retention:** Edit/cancel/delete on the media edit page all return to the URL that launched the edit. The list page passes `?next={{ request.get_full_path|urlencode }}` on edit links; the edit view threads it through a hidden `<input name="next">` field so POST redirects land back on the same filtered/paginated page. `safe='/'` on the `urlencode` filter keeps path slashes readable.

**Soft-delete for media files:** Deleting a media item via the staff portal moves the physical file to `media/gallery/deleted/` rather than permanently deleting it. The `MediaItem` database record is removed; the file is kept as a safety net. The `import_media_files` command skips `gallery/deleted/` so re-importing does not resurrect deleted items.

### Design decisions

- No models of its own — no migrations needed for this app.
- All styles are inline CSS using brand CSS custom properties (`--color-gold-primary`, etc.) — no dependency on Tailwind compilation order when adding new templates.
- Alpine.js collapsible sidebar sections (Operations, Content, Tools) with state persisted in `sessionStorage`.
- Newsletter body is a plain `<textarea>` in the staff portal (the `Newsletter` model stores it as `CKEditor5Field`, but staff don't need rich text for basic sends). Django admin still available for rich-text composition if needed.

### Deployment

VPS: `209.46.125.163`, app root `/var/www/soho/`, runs as `www-data`. Service name: `soho.service`.

`main` branch = what's deployed. Work on `dev`, merge to `main` before deploying.

**Standard deploy** — `soho_full` alias on the VPS:
```bash
sudo -u www-data git pull \
  && sudo -u www-data /var/www/soho/.venv/bin/python manage.py migrate \
  && sudo -u www-data /var/www/soho/.venv/bin/python manage.py collectstatic --noinput \
  && sudo systemctl restart soho.service
```

**After a Django version upgrade** — pip install first, then `soho_full`, then force a fresh static collect:
```bash
sudo -u www-data git pull
sudo -u www-data /var/www/soho/.venv/bin/pip install -r requirements/base.txt
soho_full
# if admin CSS looks wrong, force full recollect:
sudo -u www-data /var/www/soho/.venv/bin/python manage.py collectstatic --clear --noinput
sudo systemctl restart soho.service
```

Media directory must be owned by `www-data` for uploads to work:
```bash
sudo chown -R www-data:www-data /var/www/soho/media/
```

Do not set `EMAIL_BACKEND` in the VPS `.env` — `production.py` hardcodes smtp.

### Timezone

`TIME_ZONE = 'America/New_York'` with `USE_TZ = True`. Timestamps stored as UTC in the database; `timezone.localdate()` / `timezone.localtime()` return Eastern time. Always use these in views and templates rather than `datetime.date.today()`.

---

## Reviews app (`apps/reviews/`)

### Decision log

- Single `Review` model handles both third-party (Google, Yelp, OpenTable, Rewards Network) and future member-written reviews. They share display logic and are differentiated by `source` field — not separate models.
- Ratings normalized to 1–5 decimal scale on ingest regardless of source platform scale.
- Display: half-star rendering (SVG, no JS library needed). Numeric value stored as `DecimalField(max_digits=3, decimal_places=1)` — supports 3.5, 4.5 etc.
- Homepage widget: 3–4 featured reviews from mixed sources + aggregate rating summary (pulled from Google Places API separately).
- Dedicated `/reviews/` page: all published reviews, filterable by source, with aggregate summary header.
- Source badges: platform logo (Google, Yelp, OpenTable, Rewards Network) displayed on each card for attribution. Fair use for attribution is acceptable.
- Scraping strategy: one-time import script for initial population; manual curation via admin thereafter. Ongoing automated scraping is fragile and not worth maintaining at restaurant scale.
- **Phase 2 (future, do not build yet):** member-written reviews linked to `SoHoMember`. Rewards Network reviews are verified-diner by nature (card-linked transaction); member reviews use honor system initially.

### Model

#### `Review`
Inherits `TimeStampedModel`.

| Field | Type | Notes |
|-------|------|-------|
| `source` | CharField(choices) | `google` / `yelp` / `opentable` / `rewards_network` / `member` |
| `source_id` | CharField(200, blank=True) | Platform's own review ID — used for dedup on re-import |
| `source_url` | URLField(blank=True) | Link back to original review on the platform |
| `author_name` | CharField(200, blank=True) | Display name for third-party reviews |
| `member` | FK → `members.SoHoMember` (null=True, blank=True) | Phase 2 — member-written reviews only |
| `rating` | DecimalField(max_digits=3, decimal_places=1) | Normalized to 1.0–5.0 regardless of source |
| `title` | CharField(200, blank=True) | Not all platforms include titles |
| `body` | TextField | Review text |
| `review_date` | DateField | When the customer wrote it — not when we imported it |
| `is_published` | BooleanField(default=False) | Third-party: hand-curated. Member: set True after approval |
| `is_featured` | BooleanField(default=False) | Pins to homepage widget and top of /reviews/ |
| `is_verified_diner` | BooleanField(default=False) | True for OpenTable (reservation) and Rewards Network (card transaction). Always False for Google/Yelp. Phase 2: cross-reference for member reviews TBD |
| `display_order` | PositiveIntegerField(default=0) | Manual ordering within published set |
| `is_approved` | BooleanField(default=False) | Phase 2 member reviews — starts False, set True by staff |
| `is_flagged` | BooleanField(default=False) | Phase 2 — flagged for review |
| `flagged_reason` | TextField(blank=True) | Phase 2 |
| `approved_by` | FK → User (null=True, blank=True) | Staff user who approved |
| `approved_at` | DateTimeField(null=True, blank=True) | |
| `scraped_at` | DateTimeField(null=True, blank=True) | Null for member reviews |
| `raw_data` | JSONField(default=dict, blank=True) | Original scraped/imported payload — for reference, not displayed |

Default ordering: `['-is_featured', 'display_order', '-review_date']`

#### `AggregateRating`
Stores the platform-level summary rating (e.g. "4.7 stars based on 312 Google reviews"). Updated periodically via management command, not per review import.

| Field | Type | Notes |
|-------|------|-------|
| `source` | CharField(choices) | Same choices as `Review.source` (excludes `member`) |
| `rating` | DecimalField(max_digits=3, decimal_places=1) | Platform aggregate, e.g. 4.7 |
| `review_count` | PositiveIntegerField | Total reviews on the platform |
| `last_updated` | DateTimeField(auto_now=True) | |
| `source_url` | URLField(blank=True) | Link to the business profile on the platform |

One record per source. Used in the homepage widget header and `/reviews/` page aggregate summary bar.

### Admin (`apps/reviews/admin.py`)

#### `ReviewAdmin`
- `list_display`: author (name or member email), source (with icon), star_display, review_date, is_published, is_featured, is_verified_diner
- `list_filter`: source, is_published, is_featured, is_verified_diner, is_approved
- `search_fields`: author_name, body, member__email
- `list_editable`: is_published, is_featured, display_order
- `readonly_fields`: source_id, scraped_at, raw_data, approved_by, approved_at
- Bulk actions: `publish_selected`, `unpublish_selected`, `feature_selected`, `unfeature_selected`
- Custom method `star_display` renders a text approximation of the star rating in list view (e.g. `★★★★½`)

#### `AggregateRatingAdmin`
- `list_display`: source, rating, review_count, last_updated, source_url
- `readonly_fields`: last_updated
- Simple — mainly used to verify the refresh command ran correctly

### URLs / views

| URL | View | Name | Notes |
|-----|------|------|-------|
| `/reviews/` | `ReviewListView` | `reviews:index` | All published reviews; filterable by source via `?source=` param |

No detail view needed — review body is shown in full on the list page (cards).

Homepage widget is a template partial included in the homepage view context — not a separate URL.

### Template structure

```
apps/reviews/templates/reviews/
    index.html              # /reviews/ page — aggregate summary + full card grid
    partials/
        review_card.html    # single review card (shared by homepage and /reviews/)
        star_rating.html    # SVG half-star renderer — takes `rating` variable (1.0–5.0)
        aggregate_bar.html  # summary row: "4.7 ★ · 312 Google reviews · View on Google"
        homepage_widget.html # 3–4 featured cards + link to /reviews/
```

Homepage includes:
```django
{% include 'reviews/partials/homepage_widget.html' %}
```

### Star rating rendering

SVG-based, no JS library. `star_rating.html` takes a `rating` float and renders 5 stars with full, half, or empty fill. Use inline SVG with CSS custom properties for color theming. Example logic:

```
For each of 5 positions:
  if rating >= position → full star
  elif rating >= position - 0.5 → half star
  else → empty star
```

Pass as template tag or include with context: `{% include 'reviews/partials/star_rating.html' with rating=review.rating %}`.

Do NOT use a JS star library — SVG keeps it server-rendered, no flash of unstyled content, works without JS.

### Source badges

Each platform has a badge shown on the review card. Use inline SVG or a small PNG for logos. Badge includes the platform name as alt text for accessibility. Displayed in the card footer alongside the verified diner checkmark (if applicable).

```
[Google logo] Google   ✓ Verified Diner
```

SVG logos for Google, Yelp, OpenTable, Rewards Network — store in `apps/reviews/static/reviews/img/`. Do not hotlink from platform CDNs.

### Scraper architecture (`apps/reviews/scrapers/`)

```
apps/reviews/scrapers/
    __init__.py
    base.py           # BaseReviewScraper — normalize_rating(), build_Review_dict(), dedup check
    google.py         # Google Places API client
    yelp.py           # Yelp Fusion API client
    opentable.py      # Playwright-based (fragile — use for one-time import only)
    rewards_network.py # Portal export parser (CSV or Playwright TBD — check merchant portal)
```

#### `base.py`
```python
class BaseReviewScraper:
    source: str  # subclasses set this

    def normalize_rating(self, raw_rating: float, scale: float = 5.0) -> Decimal:
        """Normalize any platform scale to 1.0–5.0."""
        return round(Decimal(raw_rating / scale * 5), 1)

    def is_duplicate(self, source_id: str) -> bool:
        return Review.objects.filter(source=self.source, source_id=source_id).exists()

    def fetch(self) -> list[dict]:
        raise NotImplementedError

    def run(self) -> tuple[int, int]:
        """Returns (imported_count, skipped_count)."""
```

#### `google.py`
Uses Google Places API (requires `GOOGLE_PLACES_API_KEY` in `.env`). Returns up to 5 reviews per call (API limit). Also fetches aggregate rating and review count for `AggregateRating`.

```python
GOOGLE_PLACE_ID = env('GOOGLE_PLACE_ID')  # find via Places API or Google Maps URL
```

#### `yelp.py`
Uses Yelp Fusion API (requires `YELP_API_KEY` in `.env`). Returns up to 3 reviews. Also fetches aggregate rating.

```python
YELP_BUSINESS_ID = env('YELP_BUSINESS_ID')  # from Yelp business URL slug
```

#### `opentable.py` and `rewards_network.py`
Playwright-based for one-time import. Mark clearly in code as fragile/manual-use-only. Check Rewards Network merchant portal first — if CSV export is available, parse that instead of scraping.

### Management commands

`python manage.py import_reviews --source=google`
`python manage.py import_reviews --source=yelp`
`python manage.py import_reviews --source=opentable`
`python manage.py import_reviews --source=rewards_network`
`python manage.py import_reviews --source=all`

All imported reviews arrive with `is_published=False` — staff curates which to publish via admin. Command prints import/skip counts. Safe to re-run (dedup via `source_id`).

`python manage.py refresh_aggregate_ratings`

Calls Google Places API and Yelp Fusion API to update `AggregateRating` records. Run periodically (weekly cron or manual). Does not touch individual `Review` records.

### Environment variables to add to `.env.example`

```
GOOGLE_PLACES_API_KEY=
GOOGLE_PLACE_ID=
YELP_API_KEY=
YELP_BUSINESS_ID=
```

### Homepage widget context

The homepage view (`apps/core/views.py`) should pass:
```python
context['featured_reviews'] = (
    Review.objects
    .filter(is_published=True, is_featured=True)
    .select_related('member')
    .order_by('display_order', '-review_date')[:4]
)
context['aggregate_ratings'] = AggregateRating.objects.all()
```

### Phase 2 — Member reviews (future, do not build yet)

When member accounts are active (`apps.members` Phase 2 complete):
- Add `/reviews/submit/` — `MemberReviewSubmitView`, requires member login
- `Review.member` FK populated; `Review.author_name` left blank (display uses `member.first_name`)
- `is_published=False` on submit; staff approves via admin approval queue (filter: `source=member, is_approved=False`)
- Approval triggers email notification to member via `send_mail()`
- `is_verified_diner` logic TBD — honor system at launch, possible Rewards Network cross-reference later
- Add `MemberReviewForm` to `apps/reviews/forms.py` — fields: rating (1–5 integer selector), title (optional), body (required, min 20 chars)

---

## Menu restructure (`apps/menu/`)

### Decision log

- `menu_type` field already exists on `Menu` — the `weekly_specials` type has been added. See Menu enhancements section for full spec. Do not add other new types without a spec.
- Add a `role` field to `Menu` — this is the only model change to `Menu`.
- The combined `all` menu type is retired. The full menu page renders default food and default drink menus together in the view — no combined menu record is needed. Remove the `all` option from `menu_type` choices only after confirming no menus currently use it and no views/templates reference it. Grep before removing.
- `available_game_day` on `MenuItemCategoryAssignment` is deprecated and replaced entirely by role-based menu switching. Do NOT use `available_game_day` as the basis for populating event menus — the flag was experimental and the menus have evolved since it was introduced. Event menus are built fresh in the admin with deliberate item selections.
- "Game day" terminology replaced throughout by "event" — not all events are games.
- `SiteSettings.force_game_day_mode` rename to `force_event_mode` is desirable for consistency but only if the field rename doesn't break existing references — grep first, treat as a separate step if widely referenced.

### `Menu.role` field

Add to `Menu` model in `apps/menu/models.py`:

```python
ROLE_CHOICES = [
    ('none', 'No special role'),
    ('default_food', 'Default Food Menu'),
    ('default_drinks', 'Default Drinks Menu'),
    ('event_food', 'Event Food Menu'),
    ('event_drinks', 'Event Drinks Menu'),
]

role = models.CharField(
    max_length=20,
    choices=ROLE_CHOICES,
    default='none',
)
```

**Uniqueness enforcement** — only one menu can hold each non-`none` role at a time. Enforce in `Menu.save()`, same pattern as `ColorScheme.is_default`:

```python
def save(self, *args, **kwargs):
    if self.role != 'none':
        # Demote any other menu currently holding this role
        Menu.objects.filter(role=self.role).exclude(pk=self.pk).update(role='none')
    super().save(*args, **kwargs)
```

Reassigning a role to a new menu automatically demotes the previous holder to `role='none'` — no orphaned duplicate roles possible.

### `EventDay.save()` smart default

`EventDay` has `event_type` (choices include `game_day`) and `home_away` (optional, choices include `home` and `away`). Add to `EventDay.save()` **before** `super().save()`:

```python
def save(self, *args, **kwargs):
    # Smart default for limited_menu on creation only — never overrides staff changes
    if not self.pk and self.event_type == 'game_day':
        if self.home_away == 'home':
            self.limited_menu = True
        elif self.home_away == 'away':
            self.limited_menu = False
        # home_away is None: no default set — leave limited_menu at its field default
    super().save(*args, **kwargs)
```

Key rules:
- `if not self.pk` — fires on creation only, never on subsequent saves
- Only applies to `event_type == 'game_day'` — concerts, private parties, and other event types are unaffected and get no automatic default
- Staff can override `limited_menu` freely after creation — the smart default is a convenience, not a constraint
- Example: Steelers make the Super Bowl — away game defaults to `limited_menu=False` on creation; staff flips it to `True` for the watch party. Both steps work correctly
- This logic belongs in the model `save()` not in admin `save_model()` — it must apply everywhere (admin, management commands, shell)

### View logic — `get_active_menus()` helper

Add to `apps/menu/utils.py`:

```python
def get_active_menus() -> dict:
    """
    Returns the correct food and drink menus based on current event mode.
    Always returns a dict — values may be None if no menu holds that role.
    Templates must handle None gracefully.
    """
    from apps.events.models import EventDay
    from apps.menu.models import Menu

    event_mode = EventDay.get_current_menu_mode() == 'limited'

    food_role = 'event_food' if event_mode else 'default_food'
    drinks_role = 'event_drinks' if event_mode else 'default_drinks'

    return {
        'food': Menu.objects.filter(role=food_role).first(),
        'drinks': Menu.objects.filter(role=drinks_role).first(),
        'event_mode': event_mode,
    }
```

Use `.first()` not `.get()` — if no menu holds a role the view receives `None` rather than an exception. This is important during the transition period when roles are being assigned.

Views pass both menus to context:

```python
menus = get_active_menus()
context['food_menu'] = menus['food']
context['drink_menu'] = menus['drinks']
context['event_mode'] = menus['event_mode']
```

### Full menu page template

Render food then drinks sequentially — no combined menu record:

```django
{% if food_menu %}
    {% include 'menu/partials/menu_sections.html' with menu=food_menu %}
{% else %}
    <p>Food menu coming soon.</p>
{% endif %}

{% if drink_menu %}
    {% include 'menu/partials/menu_sections.html' with menu=drink_menu %}
{% else %}
    <p>Drinks menu coming soon.</p>
{% endif %}
```

### Event day menu preview URL

Add a `/menu/event-day/` URL that always shows event menus regardless of current mode. Useful for customers planning around upcoming events.

```python
# apps/menu/urls.py
path('event-day/', EventDayMenuView.as_view(), name='event_day_menu'),
# Full name: menu:event_day_menu
```

```python
class EventDayMenuView(TemplateView):
    template_name = 'menu/event_day_menu.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['food_menu'] = Menu.objects.filter(role='event_food').first()
        context['drink_menu'] = Menu.objects.filter(role='event_drinks').first()
        context['is_preview'] = not (EventDay.get_current_menu_mode() == 'limited')
        return context
```

Template shows a banner when `is_preview=True`:
> "This is our event day menu — available during select events. Check our events calendar to see what's coming up."

When `is_preview=False` (event mode is actually active), no banner — this is just the regular menu view.

### Promo menus

Promo menus use `menu_type='promo'` and `role='none'` — unaffected by this restructure. Homepage slot assignment via `homepage_slot` field is unchanged. A future `show_in_event_mode` boolean on `Menu` may be needed to control promo visibility during events — do not add it now, flag with a `# TODO` comment in the promo display logic.

### Migration sequence — follow this order exactly

**Step 1 — Grep first.** Search entire codebase for every reference to:
- `available_game_day`
- `menu_type='all'` and `default='all'`
- `force_game_day_mode`
- `limited_menu` (understand all usages before changing anything)

Document every file and line. Do not proceed until the full list is known.

**Step 2 — Add `Menu.role` field.** `makemigrations`, `migrate`. All existing menus get `role='none'` — no data loss. Commit.

**Step 3 — Add `EventDay.save()` smart default logic.** No migration needed. Commit.

**Step 4 — Add `get_active_menus()` helper** to `apps/menu/utils.py`. Commit.

**Step 5 — Update views and templates.** Replace all `available_game_day` filtering with `get_active_menus()`. Update every template that references `available_game_day`. Commit.

**Step 6 — Add event day preview URL** (`/menu/event-day/`). Commit.

**Step 7 — Staff assigns roles in admin.** Set `default_food`, `default_drinks`, `event_food`, `event_drinks` on the appropriate menus. Build event menus fresh — do not derive from `available_game_day` data.

**Step 8 — Verify both modes.** Use `SiteSettings.force_game_day_mode=True` to simulate event mode without waiting for a real event. Confirm menu pages render correctly in both modes. Confirm preview URL works.

**Step 9 — Remove `available_game_day`.** Only after Step 5 is confirmed working. Remove field from `MenuItemCategoryAssignment`. `makemigrations`, `migrate`. Commit.

**Step 10 — Remove `all` from `menu_type` choices.** Only after confirming no menus use it. Delete the combined menu record from the database. Commit.

**Do not combine steps into a single commit** — each step must be independently revertable.

---

## Media app (`apps/media/`)

### Guiding principle

> **Media is what it is. Gallery is how it's used.**

`MediaItem` is the single source of truth for every image and video on the site. The public `/gallery/` page, menu item images, banner images, category backgrounds, and popups are all consumers of `MediaItem` — none of them own their own files.

### Decision log

- `apps.gallery` is fully replaced by `apps.media` — see deprecation notice above.
- `django-media-manager` is removed — do not reference it.
- `MenuItem` images use a `MenuItemImage` through model (not a direct FK). One item can have multiple images; `is_primary` enforces a single primary image via `save()`. The old `GalleryItem.menu_item` reverse FK is dropped with `apps.gallery`.
- Files on disk in `media/gallery/` and subdirectories are preserved exactly as-is. The import command scans these directories to create `MediaItem` records. No files are moved or renamed.
- `owner_type` separates staff-controlled media from future member submissions at the model level. Staff pickers only ever show `owner_type='staff'` items. Member submissions (`owner_type='member'`) go through a moderation queue before appearing anywhere public.
- Physical file separation: staff files upload to `media/library/` (or existing `media/gallery/` subdirs for re-imported files). Member submissions upload to `media/submissions/`. This makes S3 bucket policy and filesystem permissions straightforward.
- GLightbox is retained for the public gallery lightbox — same CDN, same initialisation pattern.
- `apps.media` is not a Django admin app — all staff interaction is through the staff portal at `/staff/media/`. Django admin registration is for superuser emergency access only.

### Models (`apps/media/models.py`)

All models inherit `TimeStampedModel` from `apps.core.models`.

#### `MediaCategory`

Replaces `GalleryCategory`. Adds `is_gallery_visible` to distinguish public-facing categories from internal library organisation.

| Field | Type | Notes |
|-------|------|-------|
| `name` | CharField(100) | Display name |
| `slug` | SlugField(unique=True) | Auto-generated from name on first save |
| `description` | CharField(255, blank=True) | Shown as subtitle on public gallery page |
| `display_order` | PositiveIntegerField(default=0) | Controls tab order on public gallery |
| `is_published` | BooleanField(default=True) | False = hidden from public gallery; still visible in staff portal |
| `is_gallery_visible` | BooleanField(default=True) | False = internal library category only (e.g. "Banner Images"); never shown as a gallery tab |

```python
class Meta:
    ordering = ['display_order', 'name']
    verbose_name = 'Media Category'
    verbose_name_plural = 'Media Categories'
```

Seeded categories (run `python manage.py seed_media_categories`):

| Order | Slug | Name | is_gallery_visible |
|-------|------|------|--------------------|
| 1 | starters | Starters | True |
| 2 | soups-and-salads | Soups & Salads | True |
| 3 | wraps-and-tacos | Wraps & Tacos | True |
| 4 | sandwiches | Sandwiches | True |
| 5 | burgers | Burgers | True |
| 6 | sides | Sides | True |
| 7 | pizza | Pizza | True |
| 8 | kids | Kids | True |
| 9 | desserts | Desserts | True |
| 10 | drinks | Drinks | True |
| 11 | interior | Interior | True |
| 12 | exterior | Exterior | True |
| 13 | atmosphere | Atmosphere | True |

#### `MediaItem`

The core model. Every image and video on the site is a `MediaItem`.

| Field | Type | Notes |
|-------|------|-------|
| `name` | CharField(200) | Human-readable library name — staff-entered, renameable. E.g. "Burger Hero Shot Summer 2025". Separate from `caption` which is public-facing. |
| `slug` | SlugField(unique=True, blank=True) | Auto-generated from `name` on save. Used internally, not in URLs. |
| `owner_type` | CharField choices: `staff` / `member` | Default `staff`. Controls which pickers can see this item and which moderation rules apply. |
| `media_type` | CharField choices: `image` / `video` | Default `image`. |
| `file` | ImageField(upload_to=`media_upload_path`, blank=True, max_length=500) | Used when `media_type='image'`. |
| `video_url` | URLField(blank=True) | Used when `media_type='video'`. GLightbox auto-detects YouTube / Vimeo / TikTok / MP4. |
| `alt_text` | CharField(255, blank=True) | Accessibility. Also used as fallback caption. |
| `caption` | CharField(255, blank=True) | Public-facing caption shown in gallery lightbox. |
| `category` | FK → MediaCategory (null=True, blank=True, on_delete=SET_NULL) | Primary category for gallery display. |
| `display_order` | PositiveIntegerField(default=0) | Order within category on public gallery. |
| `is_published` | BooleanField(default=False) | False = not shown on public gallery. Staff items default False — must be explicitly published. |
| `uploaded_by` | FK → User (null=True, blank=True, on_delete=SET_NULL) | Staff user who uploaded. Null for imported files. |
| `member` | FK → `members.SoHoMember` (null=True, blank=True, on_delete=SET_NULL) | Populated for member submissions only. |
| `is_approved` | BooleanField(default=True) | Staff items: always True. Member submissions: starts False, set True by staff. |
| `is_flagged` | BooleanField(default=False) | Moderation flag for member submissions. |
| `flagged_reason` | TextField(blank=True) | |

```python
def media_upload_path(instance, filename):
    if instance.owner_type == 'member':
        return f'media/submissions/{filename}'
    return f'media/library/{filename}'
```

**Note on re-imported files:** Files already on disk under `media/gallery/` keep their existing paths when imported — the `file` field stores the relative path as-is. The `media_upload_path` function applies only to new uploads through the staff portal or member submission form.

`save()` auto-generates `slug` from `name` if not set, with collision handling (append `-2`, `-3` etc.). `file_size_display` is a read-only property that returns a human-readable file size string (e.g. "1.2 MB") for use in the staff portal.

```python
class Meta:
    ordering = ['category__display_order', 'display_order', 'name']
```

#### Models that reference `MediaItem`

Each of the following gets a nullable FK to `MediaItem`. All use `on_delete=PROTECT` — attempting to delete a `MediaItem` that is referenced raises an error rather than silently breaking the site. Staff must remove assignments before deleting a media item.

All FKs use `limit_choices_to={'owner_type': 'staff'}` — member submissions never appear in staff assignment pickers.

```python
# apps/core/models.py — PanelSide
image = models.ForeignKey(
    'media.MediaItem', null=True, blank=True,
    on_delete=models.PROTECT,
    limit_choices_to={'owner_type': 'staff'},
    related_name='panels',
)

# apps/core/models.py — SitePopup
image = models.ForeignKey(
    'media.MediaItem', null=True, blank=True,
    on_delete=models.PROTECT,
    limit_choices_to={'owner_type': 'staff'},
    related_name='popups',
)

# apps/menu/models.py — MenuCategory
background_image = models.ForeignKey(
    'media.MediaItem', null=True, blank=True,
    on_delete=models.PROTECT,
    limit_choices_to={'owner_type': 'staff'},
    related_name='menu_category_backgrounds',
)
```

**`Banner`** uses a `BannerImage` through model (not a direct FK) — supports a pool of images for random selection. See Page components section.

**`MenuItem`** uses a `MenuItemImage` through model — supports multiple images per item with `is_primary`. Staff manages these via `/staff/menu/items/<pk>/images/`.

Remove the old `GalleryItem.menu_item` reverse FK entirely when `apps.gallery` is deleted.

### Upload path helper

```python
def media_upload_path(instance, filename):
    """Route uploads to the correct subdirectory by owner type."""
    if instance.owner_type == 'member':
        return f'media/submissions/{filename}'
    return f'media/library/{filename}'
```

### Management commands (`apps/media/management/commands/`)

#### `seed_media_categories`

Creates the seeded categories above. Safe to re-run (`get_or_create`). Replaces `seed_gallery_categories`.

```bash
python manage.py seed_media_categories
```

#### `import_media_files`

Replaces `import_gallery_images`. Scans `media/gallery/` (and all subdirectories) for image files. Creates a `MediaItem` record for each file not already in the database (dedup by `file` path). Sets `owner_type='staff'`, `is_published=False`, `is_approved=True`. Populates `name` from the filename — strips extension, replaces underscores/hyphens with spaces, title-cases the result. Staff renames from there.

Automatically skips `media/gallery/deleted/` — files moved there by the staff delete action are not re-imported.

```bash
python manage.py import_media_files
python manage.py import_media_files --publish   # set is_published=True immediately
python manage.py import_media_files --dir=media/gallery/burgers  # single subdir
```

The staff portal "Import from Disk" button calls this via `call_command('import_media_files')` — same pattern as the existing `GalleryImportView`.

### Public gallery (`/gallery/`)

URL, views, and templates live inside `apps/media/` — not a separate app.

```
apps/media/templates/media/
    gallery/
        index.html          # public gallery page
        partials/
            grid.html       # photo grid
            item_card.html  # single card with hover zoom + GLightbox anchor
```

**URL:** `/gallery/` with optional `?category=<slug>` filter. URL name: `media:gallery`.

**View:** `GalleryView(ListView)` — filters `MediaItem.objects.filter(is_published=True, owner_type='staff', is_approved=True)` plus category filter. `select_related('category')`. Pagination: 8 items per page (2 rows of 4).

Category tabs: all published `MediaCategory` records where `is_gallery_visible=True`. "All" tab always first.

GLightbox: same CDN and initialisation as before. For images: `href="{{ item.file.url }}"`. For videos: `href="{{ item.video_url }}"`. GLightbox auto-detects.

Hover effect: Tailwind `group` / `group-hover:scale-110 transition-transform` — no JS.

**Future member photo tab:** When member submissions are live, add a second tab section filtered by `owner_type='member', is_approved=True`. Staff and member photos are visually separated — not interleaved. Do not build this now.

### Staff portal — media section (`/staff/media/`)

All views use `StaffRequiredMixin`. The media section of the staff portal has four sub-sections accessible from the left nav:

#### 1. Library (`/staff/media/`)

Grid/list of all `MediaItem` records (`owner_type='staff'`). Each card shows:
- Thumbnail (larger than Django admin default — at least 200px wide)
- `name` field (editable inline or via edit view)
- Category badge
- Published/unpublished status toggle
- Usage count — how many banners, menu items, etc. reference this item (annotated query)
- Edit / Delete buttons

Filters: by category, by `is_published`, by `media_type`. Search by name.

Delete protection: if a `MediaItem` is referenced by any FK (`on_delete=PROTECT`), show a clear error listing what references it rather than a generic 500. Catch `ProtectedError` in the delete view.

#### 2. Upload (`/staff/media/upload/`)

Single or multi-file upload form. Fields:
- `name` — required, human-readable. For multi-file upload: staff enters a base name; files are named `{base_name} 1`, `{base_name} 2`, etc. Staff renames individually after upload.
- `category` — optional, select from `MediaCategory`
- `alt_text` — optional
- `file(s)` — `<input type="file" multiple accept="image/*,video/*">`
- `is_published` — checkbox, default unchecked

No client-side preview required for Phase 1 — keep it simple.

After upload: redirect to library with success message showing count of files uploaded.

#### 3. Import from disk (`/staff/media/import/`)

POST-only view. Calls `call_command('import_media_files')`, captures stdout, shows result as a flash message. Redirects to library. Same pattern as existing `GalleryImportView`.

Staff uses SFTP (WinSCP on Windows, Cyberduck on Mac, scp/sftp on Linux) to put files in `media/gallery/` or subdirectories on the server, then clicks "Import from Disk" in the portal. The import command scans and creates records.

#### 4. Menu item image assignment (`/staff/menu/items/<pk>/images/`)

Menu item images are managed via a dedicated page per menu item — not an inline section on the main edit form. Staff navigates here from an "Images" button/link on the menu item list row.

**Approach:** Django inline formset (`inlineformset_factory`). Standard page-based form, one Save button, redirect back to menu item list on success. No AJAX, no modal picker.

**Formset:** `inlineformset_factory(MenuItem, MenuItemImage, fields=['media_item', 'display_order', 'is_primary'], extra=1, can_delete=True)`

**`media_item` widget queryset:** Always filtered to `MediaItem.objects.filter(owner_type='staff').order_by('name')` — member submissions never appear. Display shows `MediaItem.name` (human-readable) not filename.

**Page layout:**
```
Edit Images — {menu item name}
─────────────────────────────────────
Primary  Order  Image              Delete
◉        1      [Burger Hero ▾]    □
○        2      [Burger Side ▾]    □
○        3      [Burger Close ▾]   □
─────────────────────────────────────
[+ Add another image row]
[Save]  [Cancel → back to list]
```

- Primary is a radio input — one per formset. `MenuItemImage.save()` already enforces single primary; do not re-implement in the view.
- Order is a number input.
- Delete checkbox uses Django formset standard deletion.
- If no images exist yet, formset shows one empty row (`extra=1`).

**URL:** `menu:item_images` — `/staff/menu/items/<pk>/images/`
**View:** `MenuItemImagesView` — `LoginRequiredMixin` + `is_staff` check, same auth pattern as all staff portal views.
**On save:** redirect to menu item list. On cancel link: same redirect.
**On error:** re-render formset with validation messages.

#### 5. Other model image assignment

`Banner`, `PanelSide`, `SitePopup`, `MenuCategory` all use single `MediaItem` FKs — edited directly on their existing staff portal edit forms as a standard select dropdown filtered to `owner_type='staff'`. No separate assignment page needed for single-image models.

**`BannerImage` through model** (multiple images for random selection):
Banner uses `BannerImage` through model instead of single FK. The banner edit page in the staff portal includes an inline formset for `BannerImage` records — same pattern as `MenuItemImage`. Fields: `media_item`, `display_order`, `is_active` (controls whether image is in the random pool).

View logic selects a random active banner image:
```python
image = banner.images.filter(is_active=True).order_by('?').first()
```
This runs in `get_banner()` in `apps/core/utils.py` and is passed in the context dict.

#### 6. Member submissions (`/staff/media/submissions/`) — Phase 2, do not build yet

Moderation queue for `owner_type='member'` items. Shows pending submissions (`is_approved=False, is_flagged=False`). Staff approves (sets `is_approved=True`, `is_published=True`) or rejects (sets `is_flagged=True`, sends notification email to member). Approved submissions appear in the member photo section of the public gallery.



### Migration sequence — follow this order exactly

**Step 1 — Build `apps.media` alongside `apps.gallery`.** Do not touch `apps.gallery` yet. Create `apps/media/`, define `MediaCategory` and `MediaItem` models, write migrations, `makemigrations media`, `migrate`. Commit.

**Step 2 — Seed categories.** `python manage.py seed_media_categories`. Commit.

**Step 3 — Import files.** `python manage.py import_media_files`. Verify records created. Commit.

**Step 4 — Add FK fields to consumer models.** Add `MediaItem` FKs to `Banner`, `PanelSide`, `SitePopup`, `MenuCategory`, `MenuItem`. All nullable. `makemigrations`, `migrate`. Commit.

**Step 5 — Build staff portal media section.** Library view, upload view, import view, assignment picker. Commit.

**Step 6 — Move public gallery views to `apps.media`.** Update `config/urls.py` to point `/gallery/` at `apps.media` views. Verify public gallery works. Keep `apps.gallery` urls registered temporarily as a fallback. Commit.

**Step 7 — Verify everything.** Public gallery renders. Staff portal library works. Upload works. Import works. Assignment picker works. No references to `apps.gallery` in active code paths.

**Step 8 — Delete `apps.gallery`.** Remove from `INSTALLED_APPS`, delete the app directory, remove URL registration, drop migrations. `makemigrations`, `migrate` to clean up. Commit.

**Step 9 — Remove old `GalleryItem.menu_item` FK references** from any remaining templates or views. These should already be gone after Step 6 but grep to confirm.

**Do not combine steps** — each must be independently revertable.

### Future: Ionos S3 storage

When Ionos S3 is configured, update `production.py`. No model changes required — `ImageField`/`FileField` uses `DEFAULT_FILE_STORAGE` automatically.

```python
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_ACCESS_KEY_ID = env('IONOS_ACCESS_KEY')
AWS_SECRET_ACCESS_KEY = env('IONOS_SECRET_KEY')
AWS_STORAGE_BUCKET_NAME = env('IONOS_BUCKET_NAME')
AWS_S3_ENDPOINT_URL = env('IONOS_S3_ENDPOINT')
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = 'public-read'
```

### Member photo submissions — Phase 2 (do not build yet)

When `SoHoMember` gains a Django `User` link and login capability:

- Member logs in, navigates to `/gallery/submit/`
- Uploads image(s) with optional caption
- `MediaItem` created with `owner_type='member'`, `member=FK`, `is_approved=False`, `is_published=False`
- File saved to `media/submissions/`
- Staff sees submission in `/staff/media/submissions/` moderation queue
- Approval: `is_approved=True`, `is_published=True` → appears in member photo section of public gallery
- Rejection: `is_flagged=True` → email notification to member
- Member submissions never appear in staff assignment pickers (`limit_choices_to={'owner_type': 'staff'}` on all FKs)

---

## Banner and PanelSide restructure (`apps/core/`)

### Guiding principle

`Banner` and `PanelSide` are **presentation wrappers** — they control how content looks (colors, images, layout) but not what it says. Content lives in `ContentGroup` → `ContentSlot` → `ContentBlock`. The same `ContentGroup` can be assigned to a banner, a panel, or both simultaneously. No content duplication ever.

### Decision log

- `Banner.as_context()` is removed entirely — do not re-implement it. Templates access content directly via `banner.content_group.all_slots`.
- `Banner.title` and `Banner.content` text fields are removed — content moves to `ContentGroup`.
- `PanelSide` `mode`, `title`, `body`, `button_*` fields are removed — content moves to `ContentGroup`.
- Colors (`bg_color`, `text_color`) stay on `Banner` and `PanelSide` — presentation, not content. `ContentGroup` is color-agnostic so it can be reused across surfaces with different color schemes.
- `Banner` uses `BannerImage` through model for random image selection — unchanged from current spec.
- `PanelSide.component` field controls what each side renders: `content` (uses ContentGroup), `map` (renders Google Maps embed from `SiteSettings`), or `image` (full-bleed MediaItem).
- Google Maps embed URL lives in `SiteSettings` — not in ContentGroup, not in ContentBlock. The map is infrastructure, not content.
- Clean break on data — existing `Banner` and `PanelSide` records are rebuilt in admin under the new architecture. No data migration needed.
- `get_banner(slug)` and `get_panel_side(slug)` in `apps/core/utils.py` are updated to return the model instance directly (or None) rather than a context dict. Views pass the instance to templates. Templates access fields and ContentGroup directly.

### `Banner` model

Remove: `title`, `content` (text fields)
Keep: `slug`, `label`, `bg_color`, `text_color`, `image_opacity`, `image_only`, `is_active`
Add: `content_group` FK

```python
class Banner(TimeStampedModel):
    slug = models.SlugField(max_length=100, unique=True)
    label = models.CharField(max_length=200)

    content_group = models.ForeignKey(
        'content.ContentGroup',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='banners',
        help_text="Content group supplying title, body, and button slots for this banner.",
    )

    bg_color = models.CharField(max_length=50, choices=BANNER_COLOR_CHOICES, default='bg-primary')
    text_color = models.CharField(max_length=50, choices=BANNER_COLOR_CHOICES, default='text-primary')
    image_opacity = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('0.40'))
    image_only = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # BannerImage through model handles images (multiple, random selection)
    # Access via: banner.images.filter(is_active=True).order_by('?').first()
```

### `BannerImage` through model (unchanged)

```python
class BannerImage(TimeStampedModel):
    banner = models.ForeignKey(Banner, on_delete=models.CASCADE, related_name='images')
    media_item = models.ForeignKey(
        'media.MediaItem', on_delete=models.PROTECT,
        limit_choices_to={'owner_type': 'staff'}
    )
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['display_order']
        unique_together = [('banner', 'media_item')]
```

### `PanelSide` model

Remove: `mode`, `title`, `body`, `button_label`, `button_url`, `button_bg_color`, `button_text_color`, `image` (direct FK)
Keep: `slug`, `label`, `side`, `bg_color`, `text_color`, `is_active`
Add: `component`, `content_group`, `image` (FK → MediaItem, for component='image')

```python
class PanelSide(TimeStampedModel):

    class Component(models.TextChoices):
        CONTENT = 'content', 'Content (uses ContentGroup)'
        MAP     = 'map',     'Google Maps Embed'
        IMAGE   = 'image',   'Full-bleed Image'

    class Side(models.TextChoices):
        LEFT  = 'left',  'Left'
        RIGHT = 'right', 'Right'

    slug  = models.SlugField(max_length=100, unique=True)
    label = models.CharField(max_length=200)
    side  = models.CharField(max_length=10, choices=Side.choices, default=Side.LEFT)

    component = models.CharField(
        max_length=20,
        choices=Component.choices,
        default=Component.CONTENT,
        help_text="What this panel side renders.",
    )

    # Used when component='content'
    content_group = models.ForeignKey(
        'content.ContentGroup',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='panel_sides',
        help_text="Content group for this panel side. Only used when component is Content.",
    )

    # Used when component='image'
    image = models.ForeignKey(
        'media.MediaItem',
        null=True, blank=True,
        on_delete=models.PROTECT,
        limit_choices_to={'owner_type': 'staff'},
        related_name='panel_sides',
        help_text="Full-bleed image. Only used when component is Image.",
    )

    # Presentation — applies to all component types
    bg_color   = models.CharField(max_length=50, choices=BANNER_COLOR_CHOICES, default='bg-primary')
    text_color = models.CharField(max_length=50, choices=BANNER_COLOR_CHOICES, default='text-primary')
    is_active  = models.BooleanField(default=True)
```

### `get_banner()` and `get_panel_side()` in `apps/core/utils.py`

Updated to return the model instance directly, not a context dict.

```python
def get_banner(slug: str) -> Banner | None:
    return (
        Banner.objects
        .filter(slug=slug, is_active=True)
        .select_related('content_group')
        .prefetch_related('content_group__slots__blocks', 'images__media_item')
        .first()
    )

def get_panel_side(slug: str) -> PanelSide | None:
    return (
        PanelSide.objects
        .filter(slug=slug, is_active=True)
        .select_related('content_group', 'image')
        .prefetch_related('content_group__slots__blocks')
        .first()
    )
```

Views pass the instance to context:
```python
context['hero_banner'] = get_banner('hero')
context['left_panel'] = get_panel_side('home-events-image')
context['right_panel'] = get_panel_side('home-events-text')
```

### Template pattern — `banner_full.html`

Slots render in `order` sequence via `all_slots`. Each slot's `component_type` determines how it renders. Colors come from banner fields, not ContentGroup.

```django
{% if banner %}
<section style="background-color: var(--color-{{ banner.bg_color }}); position:relative;">

  {# Background image — random from BannerImage pool #}
  {% with img=banner.images.filter_active_random %}
    {% if img %}
    <div class="absolute inset-0">
      <img src="{{ img.media_item.file.url }}"
           alt="{{ img.media_item.alt_text }}"
           class="w-full h-full object-cover"
           style="opacity: {{ banner.image_opacity }};">
    </div>
    {% endif %}
  {% endwith %}

  <div class="relative z-10 max-w-7xl mx-auto px-6 py-12
              {% if banner.image_only %}sr-only{% endif %}">

    {% if banner.content_group %}
      {% for slot in banner.content_group.all_slots %}
        {% with block=slot.get_active_block %}
          {% if block %}
            {% if slot.component_type == 'title' %}
              <h1 style="color: var(--color-{{ banner.text_color }});">
                {{ block.body|safe }}
              </h1>
            {% elif slot.component_type == 'subtitle' %}
              <p class="text-lg" style="color: var(--color-{{ banner.text_color }});">
                {{ block.body|safe }}
              </p>
            {% elif slot.component_type == 'body' %}
              <div class="prose" style="color: var(--color-{{ banner.text_color }});">
                {{ block.body|safe }}
              </div>
            {% elif slot.component_type == 'button' %}
              {% if block.button_label %}
                {% if block.button_url == '#open-contact' %}
                  <button @click="$dispatch('open-contact')" class="btn btn-primary">
                    {{ block.button_label }}
                  </button>
                {% elif block.button_url == '#open-reserve' %}
                  <button @click="$dispatch('open-reserve')" class="btn btn-primary">
                    {{ block.button_label }}
                  </button>
                {% else %}
                  <a href="{{ block.button_url }}" class="btn btn-primary">
                    {{ block.button_label }}
                  </a>
                {% endif %}
              {% endif %}
            {% endif %}
          {% endif %}
        {% endwith %}
      {% endfor %}
    {% endif %}

  </div>
</section>
{% endif %}
```

Note: `banner.images.filter_active_random` — add a model method or manager method on `BannerImage` to avoid calling `.filter().order_by('?').first()` in the template. Put the random selection in `get_banner()` and pass `image` separately in context, or add a `@property` on `Banner`:

```python
@property
def random_image(self):
    return self.images.filter(is_active=True).order_by('?').first()
```

### Template pattern — `50_50.html`

Two `PanelSide` instances passed as `left_panel` and `right_panel`. Each renders based on its `component` field.

```django
{% if left_panel or right_panel %}
<section class="grid md:grid-cols-2">

  {# Left panel #}
  {% if left_panel %}
  <div style="background-color: var(--color-{{ left_panel.bg_color }});">
    {% include "core/components/_panel_side.html" with panel=left_panel %}
  </div>
  {% endif %}

  {# Right panel #}
  {% if right_panel %}
  <div style="background-color: var(--color-{{ right_panel.bg_color }});">
    {% include "core/components/_panel_side.html" with panel=right_panel %}
  </div>
  {% endif %}

</section>
{% endif %}
```

### Template pattern — `_panel_side.html` partial

```django
{% if panel.component == 'content' and panel.content_group %}

  <div style="display:flex;align-items:center;padding:3rem 2.5rem;">
    <div style="max-width:28rem;">
      {% for slot in panel.content_group.all_slots %}
        {% with block=slot.get_active_block %}
          {% if block %}
            {% if slot.component_type == 'title' %}
              <h2 style="color: var(--color-{{ panel.text_color }});">{{ block.body|safe }}</h2>
            {% elif slot.component_type == 'subtitle' %}
              <p style="color: var(--color-{{ panel.text_color }});">{{ block.body|safe }}</p>
            {% elif slot.component_type == 'body' %}
              <div class="prose" style="color: var(--color-{{ panel.text_color }});">
                {{ block.body|safe }}
              </div>
            {% elif slot.component_type == 'button' %}
              {% if block.button_label %}
                {% if block.button_url == '#open-contact' %}
                  <button @click="$dispatch('open-contact')" class="btn btn-primary mt-4">
                    {{ block.button_label }}
                  </button>
                {% else %}
                  <a href="{{ block.button_url }}" class="btn btn-primary mt-4">
                    {{ block.button_label }}
                  </a>
                {% endif %}
              {% endif %}
            {% endif %}
          {% endif %}
        {% endwith %}
      {% endfor %}
    </div>
  </div>

{% elif panel.component == 'map' %}

  {# Google Maps embed — URL from SiteSettings, not ContentGroup #}
  <div class="relative w-full" style="min-height:24rem;">
    <iframe
      src="{{ site_settings.map_embed_url }}"
      class="absolute inset-0 w-full h-full border-0"
      allowfullscreen loading="lazy"
      referrerpolicy="no-referrer-when-downgrade">
    </iframe>
    {% if site_settings.map_directions_url %}
    <a href="{{ site_settings.map_directions_url }}"
       target="_blank" rel="noopener"
       class="absolute top-4 left-4 z-10 btn btn-primary">
      &#10148; Get Directions
    </a>
    {% endif %}
  </div>

{% elif panel.component == 'image' and panel.image %}

  <div class="relative w-full h-full" style="min-height:24rem;">
    <img src="{{ panel.image.file.url }}"
         alt="{{ panel.image.alt_text }}"
         class="absolute inset-0 w-full h-full object-cover">
  </div>

{% endif %}
```

### `SiteSettings` additions

The map component pulls embed URL from `SiteSettings` — add these fields if not already present:

```python
map_embed_url = models.URLField(blank=True, help_text="Google Maps embed URL for the map panel component.")
map_directions_url = models.URLField(blank=True, help_text="Google Maps directions URL.")
```

`site_settings` is already injected into every template via context processor — no view changes needed to access these.

### Content system note — `button_url` sentinel values

Button slots in ContentBlocks use sentinel URL values to trigger Alpine modals:
- `#open-contact` → dispatches `open-contact` window event
- `#open-reserve` → dispatches `open-reserve` window event (add more as needed)

Document these in the `button_url` field help text in `ContentBlock`. Templates check for sentinel values before rendering as a standard `<a>` tag.

### Migration sequence — clean break

**Step 1 — Add new fields.** Add `content_group` FK to `Banner`. Add `component`, `content_group`, `image` FK to `PanelSide`. All nullable. `makemigrations`, `migrate`. Commit.

**Step 2 — Update `get_banner()` and `get_panel_side()`** in `apps/core/utils.py` to return model instances with prefetch. Update all views that call these to pass instances not dicts. Commit.

**Step 3 — Update templates.** Replace `banner_full.html` and `50_50.html` with slot-based patterns above. Add `_panel_side.html` partial. Remove all references to `banner.title`, `banner.content`, `panel.mode`, `panel.title`, `panel.body` etc. Grep before editing. Commit.

**Step 4 — Add `SiteSettings.map_embed_url` and `map_directions_url`** if not present. Update the about page contact section to use `panel.component == 'map'` pattern. Commit.

**Step 5 — Remove `as_context()`.** Grep entire codebase for `as_context` calls. Remove the method from `Banner` and `PanelSide`. Fix any remaining callers. Commit.

**Step 6 — Remove old fields.** Remove `Banner.title`, `Banner.content`. Remove `PanelSide.mode`, `PanelSide.title`, `PanelSide.body`, `PanelSide.button_*`. `makemigrations`, `migrate`. Commit.

**Step 7 — Rebuild content in admin.** Create `ContentGroup` records for each banner and panel. Add slots in desired order. Add ContentBlocks with copy. Assign ContentGroups to Banner and PanelSide records.

**Do not combine steps** — each must be independently revertable.

---

## Bookings app (`apps/bookings/`) — PLANNED, NOT YET BUILT

Do not build this app yet. This section documents the intended architecture so future Claude Code sessions have full context.

### Purpose

Private events that happen *at* the restaurant — not events that happen *to* it. A Pirates game affects operations (menu mode, staffing). A private birthday party is a customer relationship with a full planning lifecycle. These are fundamentally different concerns and live in different apps.

`apps.bookings` owns the customer-facing private event lifecycle. `apps.events` stays lean and operational.

### Relationship to existing apps

- **Replaces `EventInquiry` in `apps.core`** — when built, migrate `EventInquiry` data into `Booking` and remove `EventInquiry` from `apps.core`. This cleans up `apps.core` as a side effect.
- **Connects to `apps.events`** — a confirmed booking optionally creates an `EventDay`. `EventDay` gets an optional `OneToOneField` back to `Booking` so staff can navigate between operational calendar and booking detail.
- **Uses `apps.menu`** — each booking can have a custom `Menu` (type `promo`, role `none`) built specifically for that event. No new menu infrastructure needed.
- **Uses `EMAIL_BACKEND`** — all outbound emails go through the same Django email backend as newsletters and member notifications. No new email infrastructure.

### Booking lifecycle

```
new → contacted → planning → confirmed → completed → cancelled
```

Each status transition auto-creates a `BookingAuditEntry`. Some transitions suggest a templated email in the staff portal — staff always reviews before sending.

### Planned models

#### `Booking`
| Field | Type | Notes |
|-------|------|-------|
| `status` | CharField choices | `new` / `contacted` / `planning` / `confirmed` / `completed` / `cancelled` |
| `customer_name` | CharField | |
| `customer_email` | EmailField | |
| `customer_phone` | CharField | |
| `preferred_contact` | CharField | `email` / `phone` |
| `event_type` | CharField | `private_party` / `corporate` / `birthday` / `rehearsal_dinner` / `other` |
| `event_date` | DateField(null=True) | |
| `guest_count` | PositiveIntegerField(null=True) | |
| `message` | TextField | Original inquiry text |
| `internal_notes` | TextField(blank=True) | Staff-only notes |
| `assigned_to` | FK → User (null=True) | Staff member owning this booking |
| `event_day` | OneToOneField → `events.EventDay` (null=True) | Created when booking is confirmed |
| `event_menu` | FK → `menu.Menu` (null=True) | Custom menu for this event |
| `member` | FK → `members.SoHoMember` (null=True) | If the customer is a known member |

#### `BookingMessage`
| Field | Type | Notes |
|-------|------|-------|
| `booking` | FK → Booking | |
| `direction` | CharField | `inbound` / `outbound` |
| `subject` | CharField | |
| `body` | CKEditor5Field | |
| `sent_by` | FK → User (null=True) | Null for inbound messages |
| `sent_at` | DateTimeField(null=True) | Null = draft |
| `is_draft` | BooleanField(default=True) | |

#### `BookingAuditEntry`
| Field | Type | Notes |
|-------|------|-------|
| `booking` | FK → Booking | |
| `user` | FK → User | Staff member who triggered the action |
| `action` | CharField | E.g. "Status changed to confirmed", "Menu assigned", "Email sent to customer" |
| `detail` | TextField(blank=True) | Additional context |

#### `MessageTemplate`
| Field | Type | Notes |
|-------|------|-------|
| `name` | CharField | E.g. "Initial inquiry response" |
| `template_type` | CharField | `inquiry_response` / `confirmation` / `reminder` / `followup` |
| `subject` | CharField | Supports tokens: `{{customer_name}}`, `{{event_date}}`, `{{guest_count}}` |
| `body` | CKEditor5Field | Same tokens available |

### Staff portal integration

When built, `apps.bookings` adds a Bookings section to the staff portal left nav with:
- Booking list filtered by status (new / active / upcoming / past)
- Booking detail — full communication thread, audit trail, menu assignment, status controls
- Compose message — pick template, edit, preview, send
- Message templates — CRUD for reusable templates

### What NOT to build in `apps.bookings`

- Payment processing — out of scope
- Online booking form for customers (Phase 1 is staff-created from inquiry; customer-facing booking form is a future phase)
- Calendar UI — the `apps.events` calendar handles operational display; bookings appear there via the `EventDay` link

---

## Template cleanup — page templates (`about.html`, `home.html`)

### Context

Both page templates accumulated inline color styles as features were added. This section documents the cleanup work to bring them into compliance with the design system enforcement rule above. All color logic must live in component templates, not page templates.

### Three new partials to create

#### `content_section.html`

Location: `templates/core/components/content_section.html`

A simple reusable partial for content-driven page sections that need a background color but no database record. Parameter-driven — the caller passes `bg` and `text` color slug choices directly. Renders `ContentGroup.all_slots` in order, handling title, subtitle, body, and button component types.

```django
{# Usage #}
{% include "core/components/content_section.html" with group=about_mission bg="bg-secondary" text="text-secondary" %}
{% include "core/components/content_section.html" with group=about_vision bg="bg-primary" text="text-primary" %}
{% include "core/components/content_section.html" with group=about_values bg="bg-secondary" text="text-secondary" %}
```

Template structure:
```django
{% if group %}
<section class="w-full" style="background-color: var(--color-{{ bg|default:'bg-primary' }});">
  <div class="max-w-3xl mx-auto px-6 py-12">
    {% for slot in group.all_slots %}
      {% with block=slot.get_active_block %}
        {% if block %}
          {% if slot.component_type == 'title' %}
            <h2 class="text-3xl font-bold mb-4"
                style="color: var(--color-{{ text|default:'text-primary' }});">
              {{ block.body|safe }}
            </h2>
          {% elif slot.component_type == 'subtitle' %}
            <p class="text-xl mb-4"
               style="color: var(--color-{{ text|default:'text-primary' }});">
              {{ block.body|safe }}
            </p>
          {% elif slot.component_type == 'body' %}
            <div class="prose max-w-none mb-6"
                 style="color: var(--color-{{ text|default:'text-primary' }});">
              {{ block.body|safe }}
            </div>
          {% elif slot.component_type == 'button' %}
            {% if block.button_label %}
              {% if block.button_url == '#open-contact' %}
                <button @click="$dispatch('open-contact')" class="btn btn-primary mt-2">
                  {{ block.button_label }}
                </button>
              {% else %}
                <a href="{{ block.button_url }}" class="btn btn-primary mt-2">
                  {{ block.button_label }}
                </a>
              {% endif %}
            {% endif %}
          {% endif %}
        {% endif %}
      {% endwith %}
    {% endfor %}
  </div>
</section>
{% endif %}
```

**When to use `content_section.html` vs `db_banner_full.html`:**
- `content_section.html` — no database record needed, colors fixed by developer, simple content only, no background images
- `db_banner_full.html` — has a `Banner` record, staff controls colors via portal/admin, may have background images

#### `promo_grid.html`

Location: `templates/menu/partials/promo_grid.html`

Extracts the promo slot rendering logic from `home.html`. Currently duplicated identically for slot 1 and slot 2 — approximately 40 lines of color logic repeated. This partial eliminates the duplication and owns all color styling for promo sections.

```django
{# Usage #}
{% include "menu/partials/promo_grid.html" with promo=promo_slot_1 grid=promo_slot_1_grid %}
{% include "menu/partials/promo_grid.html" with promo=promo_slot_2 grid=promo_slot_2_grid %}
```

Template receives `promo` (a `Menu` instance with `resolve_colors()`) and `grid` (the grouped item assignments). All `style=` color attributes referencing `promo-primary`, `promo-accent`, `promo-text`, `promo-bg` move inside this partial. The `home.html` promo sections become two identical one-line includes.

#### `reviews_section.html`

Location: `templates/core/components/reviews_section.html`

Extracts the reviews display section from `home.html`. Owns the section wrapper background color, heading styles (`color: var(--color-text-accent)`, `color: var(--color-text-heading)`), card grid, and "Read All Reviews" link.

```django
{# Usage #}
{% include "core/components/reviews_section.html" with reviews=featured_reviews %}
```

### `about.html` changes

After the Banner/PanelSide restructure is complete:

1. **Banner section** — replace the hand-rolled `<section>` with `{% include "core/components/db_banner_full.html" with banner=about_banner %}`. Remove the inline `background-color`, `color` on h1, and inline-styled button entirely.

2. **Mission section** — replace with `{% include "core/components/content_section.html" with group=about_mission bg="bg-secondary" text="text-secondary" %}`

3. **Vision section** — replace with `{% include "core/components/content_section.html" with group=about_vision bg="bg-primary" text="text-primary" %}`

4. **Values section** — replace with `{% include "core/components/content_section.html" with group=about_values bg="bg-secondary" text="text-secondary" %}`

5. **Info + Map 50/50** — replace the hand-rolled grid with `{% include "core/components/50_50.html" with left=about_info_panel right=about_map_panel %}`. The left `PanelSide` (`about_info_panel`) has `component='content'` pointing at the `about_info` ContentGroup. The right `PanelSide` (`about_map_panel`) has `component='map'`. Remove all inline color styles from this section — `50_50.html` and `_panel_side.html` own them. Keep `id="contact"` and `scroll-margin-top: 64px` on the outer section — these are structural, not color.

6. **Bottom banner** — already correct, no change needed.

**After cleanup, `about.html` should have zero `background-color` or `color:` style references.** Run the grep check before committing:
```bash
grep -n "background-color\|color:" templates/about.html
```
Expected result: zero matches.

### `home.html` changes

1. **Reservations bar** — keep as-is. Add a comment: `{# intentional — fixed UI element, not content-driven #}`. This is the one documented exception to the no-inline-color rule.

2. **Promo slot 1** — replace the entire `{% if promo_slot_1 %}...{% endif %}` block (~20 lines) with `{% include "menu/partials/promo_grid.html" with promo=promo_slot_1 grid=promo_slot_1_grid %}`

3. **Promo slot 2** — same: replace with `{% include "menu/partials/promo_grid.html" with promo=promo_slot_2 grid=promo_slot_2_grid %}`

4. **Reviews section** — replace the entire `{% if featured_reviews %}...{% endif %}` block with `{% include "core/components/reviews_section.html" with reviews=featured_reviews %}`

5. **Everything else** — hero, catering 50/50, middle banner — already correct, no changes.

**After cleanup, `home.html` should have zero `background-color` or `color:` style references outside the documented reservations bar exception.** Run the grep check:
```bash
grep -n "background-color\|color:" templates/home.html
```
Expected result: one match only — the reservations bar `bg-[var(--color-bg-secondary)]`.

### Execution order — do Banner/PanelSide restructure first

This template cleanup depends on the Banner/PanelSide restructure being complete because:
- `about.html` banner section needs `db_banner_full.html` to be slot-based (already done)
- `about.html` 50/50 section needs `PanelSide.component` field to exist
- `_panel_side.html` needs to handle `component='content'` and `component='map'`

**Do not start this template cleanup until the Banner/PanelSide restructure migration sequence is complete and verified.**

---

## Banner and PanelSide legacy field cleanup

### Context

The audit script (`audit_legacy.py`) identified legacy fields still in use across 7 files. Live data exists in those fields and must be migrated to ContentGroups before the fields can be dropped. This is a two-phase operation.

### Live data inventory (from database check)

| Model | Field | Count | Action |
|-------|-------|-------|--------|
| Banner | title | 3 records | Migrate to ContentGroup title slot |
| Banner | content | 1 record | Migrate to ContentGroup body slot |
| BannerButton | (model) | 4 records | Migrate to ContentGroup button slots |
| PanelSide | title | 4 records | Migrate to ContentGroup title slot |
| PanelSide | button_label | 3 records | Migrate to ContentGroup button slots |

### Phase 1 — Data migration management command

Create `apps/core/management/commands/migrate_legacy_banner_content.py`

The command migrates all legacy field data into the ContentGroup system. Safe to re-run (uses get_or_create). Run in development first, verify in admin, then run on production.

Logic:

```python
# For each Banner with title or content or buttons:
#   1. Get or create a ContentGroup named after the banner slug
#   2. Get or create a title ContentSlot (order=1) if title exists
#      → Get or create a ContentBlock with body=banner.title, is_active=True
#   3. Get or create a body ContentSlot (order=2) if content exists
#      → Get or create a ContentBlock with body=banner.content, is_active=True
#   4. For each BannerButton on this banner (ordered by order):
#      → Get or create a button ContentSlot (order=10+button.order)
#      → Get or create a ContentBlock with button_label=btn.label,
#        button_url=btn.href, is_active=True
#   5. Assign content_group to the Banner if not already set
#
# For each PanelSide with title or button_label:
#   1. Get or create a ContentGroup named after the panel slug
#   2. Get or create a title ContentSlot (order=1) if title exists
#      → Get or create a ContentBlock with body=panel.title, is_active=True
#   3. If content_slot FK exists, get its active block body → body ContentSlot (order=2)
#   4. If button_label and button_href exist:
#      → Get or create a button ContentSlot (order=3)
#      → Get or create a ContentBlock with button_label=panel.button_label,
#        button_url=panel.button_href, is_active=True
#   5. Assign content_group to the PanelSide if not already set
```

Command output must clearly show:
- Which banners/panels were processed
- Which ContentGroups were created vs already existed
- Which slots and blocks were created
- A final count: X banners migrated, Y panels migrated

Usage:
```bash
python manage.py migrate_legacy_banner_content
python manage.py migrate_legacy_banner_content --dry-run  # show what would happen without saving
```

### Phase 2 — Remove legacy fields (only after Phase 1 verified)

**Do not start Phase 2 until:**
1. Phase 1 command has run successfully
2. Admin/portal review confirms all ContentGroups are correct
3. Site renders correctly with content_group-based templates

**Files to update in order:**

1. `templates/core/components/db_banner_full.html` — remove the entire `{% else %}` legacy block (title, content, buttons fallback). Only the `{% if banner.content_group %}` branch remains.

2. `templates/core/components/banner_full.html` — this template uses only legacy fields (`banner.title`, `banner.content`, `render_button`). Assess whether it is still used anywhere. If not used, delete it. If used, rewrite to use `banner.content_group.all_slots` pattern matching `db_banner_full.html`.

3. `templates/core/components/hero_with_promos.html` — remove the `{% else %}` legacy block (hero_banner.title, hero_banner.content fallback).

4. `templates/core/components/_panel_side.html` — remove: `panel.title` block, `panel.content_slot` block, `panel.button_label`/`panel.button_href` block.

5. `apps/core/models.py`:
   - Remove `Banner.title` field
   - Remove `Banner.content` field
   - Remove `Banner.as_context()` method
   - Remove `BannerButton` model entirely
   - Remove `PanelSide.title` field
   - Remove `PanelSide.button_label` field
   - Remove `PanelSide.button_href` field
   - Remove `PanelSide.button_bg_color` field
   - Remove `PanelSide.button_text_color` field
   - Remove `PanelSide.content_slot` FK field
   - Remove `PanelSide.mode` field
   - Remove `PANEL_MODE_CHOICES` list
   - Remove `PanelSide.as_dict()` method
   - Keep: `PanelSide.component`, `content_group`, `image`, `bg_color`, `text_color`, `horizontal_align`, `vertical_align`, `image_fallback_url`, `image_alt`, `is_active`

6. `apps/core/admin.py` — remove `BannerButtonInline`, remove `BannerButton` from imports and `BannerAdmin.inlines`.

7. `apps/core/management/commands/load_banners.py` — remove `BannerButton` import and all `BannerButton.objects.get_or_create` calls.

8. `makemigrations` — review migration before running. It will drop columns and the BannerButton table. Flag any data loss warnings.

9. `migrate`

10. Run grep verification:
```bash
grep -rn "banner\.title\|banner\.content\|BannerButton\|as_context\|panel\.title\|panel\.button_label\|panel\.mode\|as_dict\|content_slot\|PANEL_MODE_CHOICES\|full_img" \
  --include="*.py" --include="*.html" \
  --exclude-dir={migrations,.venv,__pycache__} .
```
Expected: zero matches (excluding audit_legacy.py itself).

### render_button template tag

`render_button` in `ui_tags.py` is still valid — it renders button dicts passed from views. Do NOT remove it. The legacy usage is `BannerButton.as_dict()` feeding it, which goes away. The tag itself stays for any view that constructs button dicts manually.

---

## Menu enhancements (`apps/menu/`)

### `Menu.display_name` field

Add to `Menu` model in `apps/menu/models.py`:

```python
display_name = models.CharField(
    max_length=200,
    blank=True,
    help_text=(
        "Public-facing name shown on the menu page and nav. "
        "Leave blank to use the internal name field. "
        "Use for seasonal or time-sensitive labels e.g. 'Summer Cocktails' or 'Week of May 25 Specials'."
    )
)
```

Template usage — always use `display_name` for public-facing menu titles, falling back to `name`:

```django
{{ menu.display_name|default:menu.name }}
```

Three states:
- `display_name = "Summer Cocktails"` → shows "Summer Cocktails"
- `display_name = ""` (blank) → falls back to `menu.name`
- Weekly specials: `display_name = "Week of May 25 Specials"` → shows the week label

`name` is the internal admin/staff identifier and never changes. `display_name` is the public-facing label staff update freely.

Requires a migration. Safe addition — all existing records get `display_name=''`, no visible change until staff populate it.

---

### `MenuCategory.display_name` field

Add to `MenuCategory` model:

```python
display_name = models.CharField(
    max_length=100,
    blank=True,
    help_text=(
        "Public-facing name shown on the menu page. "
        "Leave blank to hide the category header entirely. "
        "Use for time-sensitive labels e.g. 'Week of May 25'."
    )
)
```

Template usage — always use `display_name` for public-facing category headers, never `name`:

```django
{% if category.display_name %}
    <h3 class="menu-category-header">{{ category.display_name }}</h3>
{% endif %}
```

Three states with one field:
- `display_name = "Burgers"` → shows "Burgers"
- `display_name = "Week of May 25"` → shows that instead of the internal name
- `display_name = ""` (blank) → no header rendered at all

`name` is the internal admin/staff label and never changes. `display_name` is what visitors see and can be updated freely.

Requires a migration. Safe addition — all existing records get `display_name=''`, no visible change on the public site until staff populate it.

---

### Weekly specials (`menu_type='weekly_specials'`)

#### Decision log

- `menu_type='weekly_specials'`, `role='none'`. Type describes content (rotating, time-sensitive). Role not needed — views find current specials by type + date range.
- Uses full existing menu hierarchy: `Menu` → `MenuCategoryAssignment` → `MenuCategory` → `MenuItemCategoryAssignment` → `MenuItem`. No new models needed.
- Categories within specials use `display_name` for public headers (e.g. "Entrees", "Dirty Sodas"). Leave blank where no header is wanted.
- Items come from three sources — all handled by the existing `MenuItem` library:
  - New items — created fresh, assigned to this week's specials
  - Featured existing items — assigned from library with optional `override_price`
  - Rotating items — a pool of `MenuItem` records reused week to week
- `override_price` on `MenuItemCategoryAssignment` handles price differences from the regular menu.
- Auto-hides when `valid_until` is in the past — staff must set new dates to publish next week's specials. Intentional friction prevents stale specials showing.
- Staff portal freshness indicator — passive reminder when specials haven't been updated.
- Nav link only appears when a current valid specials menu exists — context processor driven.

#### `Menu` model additions

Add to `menu_type` choices:

```python
('weekly_specials', 'Weekly Specials'),
```

Add fields (nullable — no behaviour change for existing menus):

```python
valid_from = models.DateField(
    null=True, blank=True,
    help_text="First day this specials menu is valid. Leave blank for non-specials menus."
)
valid_until = models.DateField(
    null=True, blank=True,
    help_text="Last day this specials menu is valid. Menu auto-hides after this date."
)
```

Add classmethod:

```python
@classmethod
def get_current_specials(cls):
    from django.utils import timezone
    today = timezone.localdate()
    return cls.objects.filter(
        menu_type='weekly_specials',
        is_published=True,
        valid_from__lte=today,
        valid_until__gte=today,
    ).first()
```

#### Context processor

Add to `apps/core/context_processors.py` so `current_specials` is available on every page:

```python
from apps.menu.models import Menu
context['current_specials'] = Menu.get_current_specials()
```

Nav template:
```django
{% if current_specials %}
    <a href="{% url 'menu:weekly_specials' %}" class="nav-dropdown__link">
        This Week's Specials
    </a>
{% endif %}
```

#### Staff portal freshness indicator

On the staff portal menu list, weekly specials menus show a badge based on `updated_at`:

```python
days_since = (timezone.now() - menu.updated_at).days
# green  = <= 7 days
# amber  = 8-14 days
# red    = 15+ days
```

Use existing badge/pill CSS. No new styles needed.

#### View and URL

```python
# apps/menu/urls.py
path('specials/', WeeklySpecialsView.as_view(), name='weekly_specials'),
```

View fetches `Menu.get_current_specials()`. If None — renders a "check back soon" template. If found — passes menu and prefetched categories/items to `menu/weekly_specials.html`.

#### Homepage integration

`current_specials` is already in context via context processor. Homepage includes:

```django
{% if current_specials %}
    {% include "menu/partials/specials_homepage_widget.html" with menu=current_specials %}
{% endif %}
```

`specials_homepage_widget.html` — shows specials menu name, date range ("Week of May 25 – May 31"), category list preview, and "See Full Specials Menu" link.

#### Staff workflow — updating weekly specials

Each week:
1. Open the weekly specials `Menu` record in the staff portal
2. Update `valid_from` and `valid_until` to the new week's dates
3. Remove last week's `MenuItemCategoryAssignment` records
4. Add this week's items from the `MenuItem` library (or create new ones)
5. Update `display_name` on categories if the label changes
6. Save — goes live automatically when `valid_from` is reached

**Future enhancement (post-launch):** Staff portal weekly specials editor with side-by-side "current specials" and "item library" for fast assignment.

#### Migration sequence

1. Add `display_name` to `Menu` — `makemigrations`, `migrate`. Commit.
2. Add `display_name` to `MenuCategory` and `MenuSubCategory` — `makemigrations`, `migrate`. Commit.
3. Add `weekly_specials` choice and `valid_from`/`valid_until` to `Menu` — combine with step 1 if not yet migrated, otherwise separate migration. `makemigrations`, `migrate`. Commit.
3. Add `get_current_specials()` classmethod. Commit.
4. Update context processor. Commit.
5. Add `WeeklySpecialsView` and URL. Commit.
6. Create `weekly_specials.html` and `specials_homepage_widget.html`. Commit.
7. Update nav to show specials link conditionally. Commit.
8. Update homepage to include specials widget. Commit.
9. Add freshness indicator to staff portal menu list. Commit.
10. Update all public menu category templates to use `display_name` not `name`. Commit.

Do not combine steps. Template changes (6–10) need no migrations and can be done in any order after 1–5 are deployed.
