# Plan: Menu Option Groups + Staff Category Editor (rev 6)

**Project:** SoHo Pittsburgh website (`jjennings308/soho-website`)
**Revision note:** Phases 1–6 are built. Rev 5 added **Phase 7**: option groups styled like printed-menu entries. Rev 6 folds in Claude Code's review of rev 5: two Sides groups get different names, group entries get their own unclamped text style and a full row at the bottom of the section, the three-way price setting is dropped for now, and the note is defined as the price shown on the right. Phase 7 **starts with a review and status report**; nothing changes until James approves. If this plan and the code or CLAUDE.md disagree, stop and flag it.

---

## Decisions

| # | Question | Decision |
|---|---|---|
| D1 | Item add-ons | **Use the existing `MenuItemAddon`.** No new text field. Show the item's `is_available` add-ons as a muted line on the item card. The formatting is done in Python (a model property or helper) and shared by the card and the item modal, whose add-on data is built in `menu_tags.py`. Don't use a template filter. Prices are formatted with `menu_filters.currency`. Entering the remaining printed-menu add-ons is content work in E2. |
| D2 | Category subtitle | **Add `MenuCategory.subtitle`** (a short CharField). Subtitle is the small-caps tagline by the heading; description is an optional body-text paragraph below it. No data migration: after deploy, James moves the tagline-style descriptions into `subtitle` through the categories CSV or the portal. |
| D3 | Base class / names | New models inherit `TimeStampedModel` and use the menu app's ordering field name (`order`), per CLAUDE.md. |
| D4 | "Imports never delete" | Keep the rule. `OptionGroup`, `OptionChoice` and `CategoryOptionGroup` get `is_active`. |
| D5 | CSV layout | New kinds in `apps/menu/importers.py`: `option_groups`, `option_choices` (match on group + name), and `category_option_groups`, placed after `categories` in the kind order. The whole-menu sheet does **not** carry option groups. |
| D6 | Upcharge format | **`menu_filters.currency` is the only formatter**, the same one `display_price` uses, giving "+7". `display_upcharge` returns `""` when the upcharge is null **or 0**, so a bare "+" never appears. Change the duplicate `_currency` in `menu_tags.py` to call `menu_filters.currency` so the two can't drift apart. |
| D7 | Category rendering | **No merge.** `menu_detail.html` is the promo / single-menu landing page (`--color-promo-*`, promo cards) and stays separate. The main menu pages already render through `menu_sections.html` → `menu_category_section.html`, so Phase 4 changes **only** `menu_category_section.html`. Optional: move the duplicated disclaimer snippet into a tiny shared partial that both include. |
| D8 | Portal category settings | Intentional scope change. Update the menu builder spec in CLAUDE.md first. |
| D9 | Portal styling | Portal convention for Phases 5–6: inline styles with brand CSS variables. |
| D10 | Commits | Run the release checks, then **ask before committing**. |
| D11 | Empty groups | Don't require a group to have choices. |
| D12 | `*` on item add-ons | **Content workaround.** Put the `*` in the add-on name ("Substitute steak*"). No new field on `MenuItemAddon`. Only one item on the printed menu needs it. |
| D13 | Subtitle on the whole-menu sheet | **No.** The sheet stays about placements. `subtitle` goes only in the `categories` kind. |
| D14 | Hidden headings | When `display_name` is blank (header hidden), **hide only the subtitle**, since it belongs to the heading. The description keeps its current behavior and still shows. Option groups still render. This means no visible change on deploy: 19 of 22 categories on dev have a blank `display_name` plus a description. |
| D15 | Groups-only categories | A category renders when it has items **or** active option groups. This supports D11 and the open Sides/Drinks question. |

**Still open (don't implement unless James says yes):** should Sides and Drinks become option groups?

---

## How to work

- One phase at a time. At the end of each phase, summarize, run the release checks, and wait for James before committing or continuing.
- Read the existing code first and reuse it: the `Kind` definitions in `importers.py`, `MenuItemAddon`, `sync_option_flags()`, `MenuCategoryAssignment`, and the existing portal pages.
- Make surgical edits. Put validation on the model.
- Each phase updates a **Menu option groups** section in CLAUDE.md (implementation notes in the style of the existing built features: new models, the D1/D6/D14/D15 rules, Phase 6's detach-deactivates choice, the new CSV kinds), so the next session knows these rules exist.

---

## Phase 1: Models and migration

Add to `MenuCategory`: `subtitle = models.CharField(max_length=150, blank=True)`

```python
class OptionGroup(TimeStampedModel):
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=80, unique=True)  # CSV match key
    note = models.CharField(max_length=200, blank=True)
    is_add_on = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    categories = models.ManyToManyField(
        "MenuCategory", through="CategoryOptionGroup", related_name="option_groups", blank=True
    )

class OptionChoice(TimeStampedModel):
    group = models.ForeignKey(OptionGroup, related_name="choices", on_delete=models.CASCADE)
    name = models.CharField(max_length=80)
    upcharge = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    cooked_to_order = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]
        unique_together = [("group", "name")]

    @property
    def display_upcharge(self):
        # "" for None or 0; otherwise "+" + currency(upcharge)
        ...

class CategoryOptionGroup(TimeStampedModel):
    category = models.ForeignKey("MenuCategory", on_delete=models.CASCADE)
    group = models.ForeignKey(OptionGroup, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]
        unique_together = [("category", "group")]
```

- Add the `MenuItemAddon` add-on formatter here too (D1): a property or helper that lists `is_available` add-ons as "Name +2 · Name +6", using the same zero/null rule as D6.
- Auto-fill `slug` from `name` when blank. Add `__str__` methods.
- Point `_currency` in `menu_tags.py` at `menu_filters.currency` (D6).
- **Done when:** the migration applies, `manage.py check` passes, the release checks pass, and the formatters have unit tests. Test zero on `OptionChoice.display_upcharge`, where a zero upcharge really can happen. `MenuItemAddon.price` has a 0.01 minimum, so a zero add-on only exists if written straight to the DB; keep that test as a guard.

## Phase 2: Django admin

- `OptionGroupAdmin`: an `OptionChoice` inline; slug prepopulated; list shows the choice count and attached categories.
- `MenuCategoryAdmin`: add `subtitle` next to `description`, plus a `CategoryOptionGroup` inline.
- **Done when:** the three printed-menu groups can be created and attached entirely in the admin.

## Phase 3: CSV import/export

- Add an optional `subtitle` column to the `categories` kind **only** (D13).
- Add the three kinds from D5 using the existing `Kind` machinery and conventions.
- Match on slugs and names, never DB ids. Respect "imports never delete" by deactivating through `is_active`.
- Older files without the new columns must still import.
- Write tests matching the existing importer tests.
- **Done when:** export → import into a fresh DB reproduces the data, and re-importing changes nothing.

## Phase 4: Public menu templates (`menu_category_section.html` only)

1. **Heading:** render `subtitle` as smaller small caps beside or under the category heading, and `description` as a body paragraph below. Each one renders only when set. When `display_name` is blank, hide the heading and subtitle; the description renders as it does today (D14).
2. **Option groups:** a partial (e.g. `menu/partials/_option_group.html`) placed at the end of the section. Show a group only if **both** `group.is_active` and the link's `is_active` are true. Choices are filtered to `is_active` and ordered by `order`. Choices go on one line separated by " · ", with `display_upcharge` when `is_add_on` and `*` when `cooked_to_order`. Style it as a compact callout, not a card.
3. **Query pattern:** add a `get_category_option_groups category` template tag in `menu_tags.py`, in the same style as `get_category_assignments`. It returns the category's active groups (both `is_active` flags), with a `Prefetch` for the active, ordered choices, so each category costs a small fixed number of queries. That matches the existing per-category pattern; removing the per-category queries altogether is out of scope.
3a. **Groups-only categories (D15):** in `menu_sections.html`, change the `{% if assignments %}` check to "items or active option groups", so a category with only groups still renders.
4. **Item add-ons line:** a muted line under the description from the D1 formatter. The modal uses the same formatter via `menu_tags.py`.
5. **Consumer advisory:** `*` relies on the `menu_footer` advisory (`show_disclaimer`). Note for James: turn `show_disclaimer` on for **Soups and Salads**.
6. **Promo pages (`menu_detail.html`):** not changed. Ask James whether option groups should appear there; the default is **no**.
7. Optional (D7): move the duplicated disclaimer snippet into a shared partial that both templates include.
8. Check on mobile widths.

- **Done when:** Starters shows Sauces & Rubs; Soups and Salads shows Dressings and Add to Any Salad with the advisory; items with add-ons show the muted line; existing category descriptions still show; a test category with only an option group renders; promo pages look unchanged.

## Phase 5: Staff portal category settings editor

- First update the CLAUDE.md menu builder spec (D8), with James's OK on the wording.
- Build an edit screen with every category setting: name / `display_name`, subtitle, description, background image, disclaimer / `show_disclaimer`, order, and visibility. It's reached from the category list in the menu builder. Propose whether B2's "+ New category" stays as is or uses this form.
- Access: MANAGER edits; Tier 2 is read-only.
- Add help tips to new pages (tests require them). Styling per D9.
- **Done when:** staff can fully edit a category without the admin, and the portal tests pass.

## Phase 6: Staff portal option group editing

- On the category screen: attach a group (the picker lists **all** groups, including ones whose link to this category is inactive), reorder, and detach.
- **Detach / re-attach:** detach sets the link's `is_active=False`. Re-attaching the same group **reactivates the existing row**; it never creates a new one, which `unique_together` would reject anyway. Note: this differs from `MenuCategoryAssignment` / B2 "Remove from this menu", which delete rows. It's deliberate, so CSV links follow "never delete".
- Group editor: name, note, `is_add_on`, plus inline choices (name, upcharge, cooked-to-order, order, active). Use a formset and an Alpine add/remove-row component written as a plain global function.
- Warn when a group is shared: "Also used in: …". Don't require at least one choice (D11).
- Access, help tips and styling as in Phase 5.
- **Done when:** staff create Dressings in the portal, attach it to two categories, edit one choice and see the change in both, then detach and re-attach without an error.

---

## Phase 7: Printed-menu look

**Goal:** option groups on the public menu read like the printed menu. "Signature Sauces & Dry Rubs", "Dressings" and "Add to Any Salad" appear as entries styled like items: bold name, the list where the description goes, no photo, no "View details". Each group takes **a full row at the bottom of the category section**, after the items and subcategory groups, like on the printed menu. Sides at two price levels can be shown cleanly (see *Content follow-up*).

### 7.0 Review first: report, don't change

Before editing anything, review the code as built in Phases 1–6 and report back to James:

1. **Status of Phases 1–6:** anything incomplete, skipped, or different from the plan, and any tests failing.
2. **How option groups render today:** template, position in the section, styling. Include a **description** of Starters and Soups and Salads on dev (Claude Code can't take screenshots here; the dev machine's headless browser lacks system libraries). James takes screenshots if needed.
3. **How item cards render today:** photo, border, price position, "View details", and the description's 3-line clamp (`.t-description`). Propose how a text-only group entry matches: the same card frame without photo or button, or a plain text entry.
4. **Item add-ons line:** what separator it uses, and whether it already matches the printed style ("Substitute steak* +4").
5. **Data on dev:** which option groups exist, and what's in the Sides and Non-Alcoholic Beverages categories (item names and prices), so James can decide how to split them into groups.
6. Anything else that blocks or affects 7.1–7.2.

Then **stop and wait** for James to pick what goes ahead.

**7.0 done (2026-11-18). James's decisions:**
1. **Layout as recommended:** a plain `<div>` entry (not a clickable card, no pop-up), same padding and title/price row as an item card: group name in the item title style, note on the right where the price goes, choices underneath in a new unclamped class that looks like `.menu-item__desc`. Full row (`md:col-span-3`). No photo, badges, "View details", hover shadow or pointer cursor.
2. **Separators follow "Choices cost extra" (`is_add_on`):** on → " | ", off → ", ". Not decided per choice.
3. **Build both 7.1 and 7.2.**
4. **Leave the portal's choice summary as it is** (" · ").
5. Start 7.1 only after James has deployed Phases 5–6 and says go.
6. Content for James, found in the review: Starters and Soups and Salads have no heading on dev (blank "heading customers see"); Caesar Salad's own add-ons (Chicken +8, Steak +10, Salmon +12) conflict with Add to Any Salad; the Soups and Salads disclaimer is still off.

### 7.1 Group entries at the bottom of the section (public templates)

- In `menu_category_section.html`, render active option groups as **entries in the section grid, each spanning a full row** (`md:col-span-3`), after the items and subcategory groups. They use item-like styling: bold name, the list underneath. No photo, no "View details", no modal.
- **Own unclamped text style:** the list must not use `.t-description` (it clamps to 3 lines and would cut long sauce or dressing lists). Add a group text class in `input.css` that matches the description's look without the clamp, using theme variables only.
- Match the item card frame only as far as the 7.0 review recommends and James approves.
- **Group note in the price position:** the note shows on the right, where an item's price goes ("Sides | 7"). The note is now defined as **the price or a short note shown on the right**, e.g. "7" or "Prices vary". Update the portal help text for `note` (Phase 6 says "e.g. 'Choose one' or 'Prices vary'"), the staff help topic and CLAUDE.md to match.
- **Separators:** choices with upcharges are joined with " | " ("Steak* +8 | Six shrimp* +8"). Unpriced lists (sauces, dressings) are joined with ", ".
- Promo pages stay unchanged (D7).
- **Done when:** Starters and Soups and Salads on dev read like the printed menu; long lists aren't cut off; groups sit in full rows at the bottom; mobile still reads cleanly; promo pages are unchanged.

### 7.2 Separator for item add-ons

- Switch the D1 add-on formatter (`MenuItem.addons_display`) from " · " to " | ", and update its tests. The card and the modal still share the one formatter.

**Status (2026-11-18):** 7.0 reported; 7.1 built (`5f75a9f`); 7.2 built. Remaining: the content follow-up below, and a look in a real browser (including phone widths).

### Not now: a three-way price display setting

Replacing `is_add_on` with `none` / `upcharge` / `price` (so choices could show standalone prices such as "Onion rings $5") is **dropped for now**. Sides don't need it: two groups with the price in the note cover them. If it comes back, note that reading the old `is_add_on` / `upcharge` CSV columns would need **column aliases in the import engine** (`importers.py` treats unknown columns as errors and ties each column to one model field), which every kind would get.

### Content follow-up (James, after Phase 7)

- **Sides:** to match the printed menu, use one group per price level with the price in the note: **"Sides"** note "7" (French fries … Rice pilaf) and **"Premium sides"** note "8" (Mashed potatoes with gravy, Gravy fries). The names differ because group names must be unique (spreadsheets look groups up by name). Then switch off the old side items. That's reversible, since imports never delete.
- **Soft drinks:** one group with the note "4", if they never have a drink special price.
- Single-serve drinks, beer, wine, and anything with sizes or specials stay as items.

---

## Reference data (printed menu, March 2026)

For testing, or a seed command **only if James asks.**

**Signature Sauces & Dry Rubs** (`is_add_on=False`), attached to **Starters**
Buffalo · Mango Habanero · Sweet BBQ · Sweet Chili · Garlic Parmesan · Honey Garlic · Cajun Dry Rub · Old Bay

**Dressings** (`is_add_on=False`), attached to **Soups and Salads**
Italian Herb Vinaigrette · Buttermilk Ranch · Spicy Ranch · Smokey Ranch · Balsamic Vinaigrette · Caesar · Honey Mustard · Bleu Cheese

**Add to Any Salad** (`is_add_on=True`), attached to **Soups and Salads**
Grilled or Crispy Chicken +7 · Steak* +8 · Six Shrimp* +8 · Salmon* +10 (`*` = `cooked_to_order`)

**Item add-ons:** content entered as `MenuItemAddon` rows through E2. Seven add-ons on four items already exist, so compare first. From the printed menu: Cheese Quesadilla (Grilled chicken +5, Pulled pork +6, Steak +7); SoHo Nachos (Guacamole +2, Grilled chicken +6, BBQ pulled pork +6, Chili +4); SoHo Sampler (Cheese fries +2, Gravy fries +2); Pittsburgh Chicken Salad ("Substitute steak*" +4, with `*` in the name per D12); Grilled Chicken Sandwich and Cheeseburger (Bacon +2); Pub Fish and Impossible Burger (Cheese +2); Steak & Cheese (Mushrooms +2, Lettuce/tomato/onion +2); SoHo Super Dogs (Chili +2).
