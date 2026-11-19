# Fix: Happy Hour subcategory boxes (homepage grid + full promo page)

**Project:** SoHo Pittsburgh website (`jjennings308/soho-website`), branch `dev`
**Decision (James, 2026-11-19):** Option (a). On the homepage, each subcategory box counts as **one** grid slot, and a box shows **all** of its items.
**How to work:** Follow CLAUDE.md. Make surgical edits. Run the release checks (`python manage.py test`), then **ask before committing**. If this doc and the code or CLAUDE.md disagree, stop and flag it.

---

## The problem

The homepage Happy Hour section (`promo_grid.html`, built by `_build_promo_grid()` in `apps/core/views.py`) shows:

- **Weekday Happy Hour:** 6 food items
- **From the Bar:** a **Half-Price Drafts** box with Coors Light, Miller Lite and Bud Light

What's missing: **Yuengling** from the drafts box, and the whole **Half-Price Well Spirit** box (Svedka, Bacardi Superior, Tanqueray, Jose Cuervo Gold). The data is correct. All 8 drinks are active in `Happy Hour Drinks` with their subcategories.

### Cause 1: homepage slot counting (`apps/core/views.py`)

```python
PROMO_GRID_LIMIT = 9
PROMO_SUBCATEGORY_LIMIT = 3
PROMO_SUBCATEGORY_ITEM_LIMIT = 3
```

`_pick_promo_items()` counts every item **inside** a subcategory box against `PROMO_GRID_LIMIT`. Here's how this menu fills the grid:

1. 6 food items use 6 of the 9 slots.
2. Drafts is capped at 3 items, which drops Yuengling. That uses 3 more slots, so 9 of 9 are taken.
3. Well spirits get nothing.

A box takes up one cell in the 3-column grid, so the limit should count boxes, not the items inside them.

### Cause 2: typo in the full promo page (`apps/menu/templates/menu/menu_detail.html`, ~line 46)

```django
{% regroup subcat_items by subcategory.name as subcategory %}
{% for subcat in subcategories %}
```

The regroup is stored as `subcategory`, but the loop reads `subcategories`, which is undefined. So **no** subcategory boxes render on `/menu/<slug>/` (the "Full Happy Hour Menu" page). The other templates (`promo_card.html`, `promo_grid.html`, `menu_category_section.html`, `simple.html`, `popup.html`, both specials widgets) spell it correctly.

---

## Changes

### 1. Homepage grid: a box is one slot (`apps/core/views.py`)

- Rework `_pick_promo_items()` so that:
  - Each **plain item** costs 1 slot.
  - Each **subcategory** costs 1 slot, and **all** of its items are included.
  - At most `PROMO_SUBCATEGORY_LIMIT` (3) subcategory boxes across the whole grid. Keep this cap.
  - The total cost stays at most `PROMO_GRID_LIMIT` (9).
- Keep the current priority and order inside a category: subcategories first, in `subcategory__order` then `order`, then plain items. `_promo_grid_sort_key` and the sort in `_build_promo_grid()` stay as they are.
- `_build_promo_grid()` currently tracks `total += len(items)`. Change it to track **slots used**. For example, have `_pick_promo_items()` return `(picked, slots_used, subcategories_used)`, and pass the remaining slots and remaining subcategory slots into the next category.
- Remove `PROMO_SUBCATEGORY_ITEM_LIMIT` (it's no longer used). Grep first to confirm nothing else imports it.
- Update the `_build_promo_grid()` and `_pick_promo_items()` docstrings to describe slot counting.
- No template changes are needed. `promo_grid.html` already renders one `promo_subcat_card.html` per subcategory.

**Expected result for the current Happy Hour menu:** 6 food cards plus a Drafts box (4 items) and a Well Spirit box (4 items) = **8 slots**.

### 2. Full promo page typo (`menu_detail.html`)

- Change `as subcategory` to `as subcategories`. That's the only change in this file. It stays a promo template (D7 in `plans/menu-option-groups.md`: no merge with the main menu templates).

### 3. Tests

In `apps/core/tests/test_home_promo_grid.py`:

- **Replace** `test_grid_shows_up_to_three_items_per_subcategory` with `test_grid_shows_all_items_in_each_subcategory`. With the existing setUp (6 drafts plus 6 wells), expect all 12 assignments, 6 for each subcategory.
- **Update** `test_grid_uses_at_most_three_subcategories`. Still 3 boxes at most, and `extra_2` is excluded, but the assignment count is now 6 + 6 + 3 = 15. Assert on the set of subcategory ids, not a hard-coded 9.
- **Add** `test_subcategory_box_counts_as_one_slot`. This reproduces the real bug: add a second category to the menu, ordered **before** the drinks category, with 6 plain items. Expect the grid to include both the drafts and the wells boxes, with all their items.
- **Add** a test that plain items stop once the slots run out. For example, 8 plain items plus 2 boxes: only 7 plain items show, because the 2 boxes use 2 of the 9 slots.
- `test_homepage_groups_subcategories_like_the_menu` should still pass unchanged.

For the full page (put it in the menu app tests that already hit `menu:menu_detail`, e.g. `apps/menu/tests/test_availability.py`, or a new small test file):

- **Add** a test that `menu_detail` for a promo menu with subcategorized items renders `promo-subcat-card` once per subcategory and includes each subcategory's `display_name` and item names.

---

## Done when

- The release checks pass.
- On dev, the homepage Happy Hour section shows the 6 food cards plus **Half-Price Drafts** (Coors Light, Miller Lite, Bud Light, Yuengling) and **Half-Price Well Spirit** (Svedka Vodka, Bacardi Superior Rum, Tanqueray Gin, Jose Cuervo Gold).
- On dev, `/menu/happy-hour/` (the full menu page) shows both drink boxes.
- The homepage slot 2 promo and the other promo/specials templates look unchanged.
- Summarize the diff, then **ask James before committing**. Suggested commits: (1) the homepage slot counting change and its tests, (2) the `menu_detail.html` typo fix and its test.
