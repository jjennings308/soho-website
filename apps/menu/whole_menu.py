"""
"Whole menu" sheet — Phase M3 of the menu CSV import (see CLAUDE.md).

One row per item on a menu. Each row is split into rows for five of the
per-kind imports (categories, items, menus, menu_categories, placements),
which run through the normal engine in that order inside one transaction —
so new categories, items and menus exist before the rows that refer to them.

    result = parse_sheet(csv_text)   # runs every stage, then rolls back: an exact preview
    result = apply_sheet(csv_text)   # runs every stage and keeps it, or raises SheetRefused

Values repeated across rows (an item in several categories, a category on
several menus) must agree; blank cells never conflict. Cell rules are the
engine's: blank keeps, '-' clears, codes or labels, yes/no.
"""
import csv
import io
from dataclasses import dataclass, field

from django.db import transaction
from django.db.models import Max
from django.utils.text import slugify

from . import importers as im
from .models import Menu, MenuCategory, MenuCategoryAssignment, MenuItem, MenuItemCategoryAssignment

KIND = 'whole_menu'
KEY_COLUMNS = ('menu', 'category', 'item')

# Sheet column → (stage kind, that kind's column).
COLUMN_MAP = {
    'menu_type': ('menus', 'menu_type'),
    'category_type': ('categories', 'category_type'),
    'category_order': ('menu_categories', 'display_order'),
    'subcategory': ('placements', 'subcategory'),
    'price': ('items', 'price'),
    'special_price': ('placements', 'override_price'),
    'item_order': ('placements', 'order'),
    'short_description': ('items', 'short_description'),
    'note': ('placements', 'note'),
    'available': ('items', 'is_available'),
    'featured': ('items', 'is_featured'),
    'new': ('items', 'is_new'),
    'chef_special': ('items', 'is_chef_special'),
    'seasonal': ('items', 'is_seasonal'),
    'vegan': ('items', 'is_vegan'),
    'gluten_free': ('items', 'is_gluten_free'),
    'dairy_free': ('items', 'is_dairy_free'),
    'nut_free': ('items', 'is_nut_free'),
    'shown': ('placements', 'is_active'),
}
COLUMNS = ['menu', 'menu_type', 'category', 'category_type', 'category_order', 'subcategory', 'item',
           'price', 'special_price', 'item_order', 'short_description', 'note', 'available',
           'featured', 'new', 'chef_special', 'seasonal', 'vegan', 'gluten_free', 'dairy_free',
           'nut_free', 'shown']
STAGES = ['categories', 'items', 'menus', 'menu_categories', 'placements']

DESCRIPTION = ('Everything on one sheet: one row per item on a menu — creates or updates menus, '
               'categories, items and placements together.')
EXAMPLE = {
    'menu': 'food-menu', 'menu_type': 'food', 'category': 'burgers', 'category_type': 'food',
    'category_order': '1', 'item': 'classic-burger', 'price': '14.50', 'item_order': '1',
    'short_description': 'Half-pound patty, cheddar, house sauce', 'available': 'yes', 'shown': 'yes',
}


@dataclass
class Stage:
    kind: str
    result: object                                   # importers.Result
    sheet_lines: dict = field(default_factory=dict)  # stage CSV line → [sheet lines]


@dataclass
class SheetResult:
    errors: list = field(default_factory=list)       # file-level
    row_errors: dict = field(default_factory=dict)   # sheet line → [messages]
    stages: list = field(default_factory=list)
    stopped_at: str = ''                             # stage with errors; later stages not checked

    @property
    def ok(self):
        return not self.errors and not self.row_errors and all(s.result.ok for s in self.stages)

    def count(self, action):
        return sum(s.result.count(action) for s in self.stages)


class SheetRefused(Exception):
    def __init__(self, result):
        self.result = result
        super().__init__('whole menu: import refused — fix the errors and try again')


# ── Splitting the sheet ──────────────────────────────────────────────────────

def _resolve(model, name_field, cell):
    """('existing', obj) / ('new', slug) for a menu, category or item cell; raises CellError."""
    obj = model.objects.filter(slug=cell).first()
    if obj:
        return obj.slug, obj
    matches = list(model.objects.filter(**{f'{name_field}__iexact': cell})[:2])
    if len(matches) > 1:
        raise im.CellError(f'"{cell}" matches more than one — use its slug')
    if matches:
        return matches[0].slug, matches[0]
    slug = slugify(cell)
    if not slug:
        raise im.CellError(f'"{cell}" is not a usable name')
    return slug, None


def _canonical(kind, column, value):
    """Comparable form of a cell (so 12 == 12.00, Y == yes); raw if unreadable."""
    if value == im.CLEAR:
        return value
    col = im.KINDS[kind].by_name[column]
    if col.type == 'ref':
        return value.lower()
    try:
        return col.canonical(value)
    except im.CellError:
        return value


class _StageRows:
    """Merged rows for one stage, keyed by record."""

    def __init__(self, kind):
        self.kind = kind
        self.rows = {}        # key → {column: value}
        self.lines = {}       # key → [sheet lines]
        self.sources = {}     # (key, column) → (sheet line, sheet column)

    def add(self, key, values, line, sheet_columns, conflicts):
        row = self.rows.setdefault(key, {})
        self.lines.setdefault(key, []).append(line)
        for column, value in values.items():
            if not value:
                continue
            if column in row and _canonical(self.kind, column, row[column]) != _canonical(self.kind, column, value):
                first_line, sheet_col = self.sources[(key, column)]
                conflicts.setdefault(line, []).append(
                    f'{sheet_columns.get(column, column)}: "{value}" here but "{row[column]}" on line {first_line}')
                continue
            row.setdefault(column, value)
            self.sources.setdefault((key, column), (line, sheet_columns.get(column, column)))

    def csv(self):
        columns = []
        for row in self.rows.values():
            columns += [c for c in row if c not in columns]
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=columns)
        writer.writeheader()
        writer.writerows(self.rows.values())
        line_map = {n: lines for n, lines in enumerate(self.lines.values(), start=2)}
        return out.getvalue(), line_map


def _split(csv_text, result):
    reader = csv.DictReader(io.StringIO(csv_text.lstrip('﻿')))
    headers = [(h or '').strip().lower() for h in (reader.fieldnames or [])]
    if not headers:
        result.errors.append('The file is empty.')
        return None
    unknown = [h for h in headers if h not in COLUMNS]
    if unknown:
        result.errors.append(f'Unknown column(s): {", ".join(unknown)}. Allowed: {", ".join(COLUMNS)}.')
    missing = [c for c in KEY_COLUMNS if c not in headers]
    if missing:
        result.errors.append(f'Missing required column(s): {", ".join(missing)}.')
    if result.errors:
        return None

    stages = {kind: _StageRows(kind) for kind in STAGES}
    # Display names of stage columns, for conflict messages.
    names = {kind: {} for kind in STAGES}
    for sheet_col, (kind, column) in COLUMN_MAP.items():
        names[kind][column] = sheet_col
    new_links = {'menu_categories': [], 'placements': []}

    for line, raw in enumerate(reader, start=2):
        cells = {(k or '').strip().lower(): (v or '').strip() for k, v in raw.items() if k is not None}
        if not any(cells.values()):
            continue
        errors = []
        keys = {}
        for col, model, name_field in (('menu', Menu, 'title'), ('category', MenuCategory, 'name'),
                                       ('item', MenuItem, 'name')):
            cell = cells.get(col, '')
            if not cell or cell == im.CLEAR:
                errors.append(f'{col}: required')
                continue
            try:
                keys[col] = _resolve(model, name_field, cell)
            except im.CellError as exc:
                errors.append(f'{col}: {exc}')
        if errors:
            result.row_errors[line] = errors
            continue
        (menu_slug, menu), (cat_slug, category), (item_slug, item) = keys['menu'], keys['category'], keys['item']
        if menu is None and not cells.get('menu_type'):
            result.row_errors.setdefault(line, []).append(
                f'menu_type: required to create the new menu "{cells["menu"]}"')
            continue

        per_stage = {kind: {} for kind in STAGES}
        for sheet_col, (kind, column) in COLUMN_MAP.items():
            per_stage[kind][column] = cells.get(sheet_col, '')
        per_stage['categories'].update({'slug': cat_slug} if category else {'name': cells['category']})
        per_stage['items'].update({'slug': item_slug} if item else {'name': cells['item']})
        per_stage['menus'].update({'slug': menu_slug} if menu else {'title': cells['menu']})
        per_stage['menu_categories'].update({'menu': menu_slug, 'category': cat_slug})
        per_stage['placements'].update({'item': item_slug, 'category': cat_slug})

        conflicts = result.row_errors
        stages['categories'].add(cat_slug, per_stage['categories'], line, names['categories'], conflicts)
        stages['items'].add(item_slug, per_stage['items'], line, names['items'], conflicts)
        stages['menus'].add(menu_slug, per_stage['menus'], line, names['menus'], conflicts)
        stages['menu_categories'].add((menu_slug, cat_slug), per_stage['menu_categories'], line,
                                      names['menu_categories'], conflicts)
        stages['placements'].add((item_slug, cat_slug), per_stage['placements'], line,
                                 names['placements'], conflicts)

        if not (menu and category and MenuCategoryAssignment.objects.filter(menu=menu, category=category).exists()):
            new_links['menu_categories'].append((menu_slug, cat_slug, menu))
        if not (item and category and MenuItemCategoryAssignment.objects.filter(menu_item=item, category=category).exists()):
            new_links['placements'].append((item_slug, cat_slug, category))

    _append_orders(stages, new_links)
    return stages


def _append_orders(stages, new_links):
    """New links with a blank order go after the existing ones, in sheet order."""
    next_order = {}
    for menu_slug, cat_slug, menu in new_links['menu_categories']:
        row = stages['menu_categories'].rows[(menu_slug, cat_slug)]
        if row.get('display_order'):
            continue
        if menu_slug not in next_order:
            existing = MenuCategoryAssignment.objects.filter(menu=menu).aggregate(m=Max('display_order'))['m'] if menu else None
            next_order[menu_slug] = (existing or 0) + 1
        row['display_order'] = str(next_order[menu_slug])
        next_order[menu_slug] += 1
    next_order = {}
    for item_slug, cat_slug, category in new_links['placements']:
        row = stages['placements'].rows[(item_slug, cat_slug)]
        if row.get('order'):
            continue
        if cat_slug not in next_order:
            existing = (MenuItemCategoryAssignment.objects.filter(category=category).aggregate(m=Max('order'))['m']
                        if category else None)
            next_order[cat_slug] = (existing or 0) + 1
        row['order'] = str(next_order[cat_slug])
        next_order[cat_slug] += 1


# ── Running the stages ───────────────────────────────────────────────────────

def _run(csv_text, keep):
    result = SheetResult()
    with transaction.atomic():
        stages = _split(csv_text, result)
        if stages is None or result.row_errors:
            return result
        for kind in STAGES:
            text, line_map = stages[kind].csv()
            stage_result = im.parse(kind, text)
            for row in stage_result.rows:
                row.sheet_lines = line_map.get(row.line, [])
            result.stages.append(Stage(kind, stage_result, line_map))
            if not stage_result.ok:
                result.stopped_at = kind
                break
            # Save now so the next stage can find what this one created.
            for row in stage_result.rows:
                if row.action in ('new', 'update'):
                    row.instance = row.form.save()
        if not (keep and result.ok):
            transaction.set_rollback(True)
    return result


def parse_sheet(csv_text):
    """Exact preview: runs every stage, then rolls back. Saves nothing."""
    return _run(csv_text, keep=False)


def apply_sheet(csv_text):
    """Run every stage and keep the result, or raise SheetRefused (nothing saved)."""
    result = _run(csv_text, keep=True)
    if not result.ok:
        raise SheetRefused(result)
    return result


# ── Export / template ────────────────────────────────────────────────────────

def _export_value(kind, column, obj):
    return im.KINDS[kind].by_name[column].export(obj)


def export_rows():
    """One row per item placement in each category on each menu, in display order."""
    links = (MenuCategoryAssignment.objects.select_related('menu', 'category')
             .order_by('menu__menu_type', 'menu__title', 'display_order', 'category__name'))
    for link in links:
        placements = (MenuItemCategoryAssignment.objects.filter(category=link.category)
                      .select_related('menu_item', 'subcategory')
                      .order_by('subcategory__order', 'order', 'menu_item__name'))
        for placement in placements:
            sources = {'menus': link.menu, 'categories': link.category, 'menu_categories': link,
                       'items': placement.menu_item, 'placements': placement}
            row = {'menu': link.menu.slug, 'category': link.category.slug, 'item': placement.menu_item.slug}
            for sheet_col, (kind, column) in COLUMN_MAP.items():
                row[sheet_col] = _export_value(kind, column, sources[kind])
            yield [row[c] for c in COLUMNS]


def export_csv():
    out = io.StringIO()
    out.write('﻿')
    writer = csv.writer(out)
    writer.writerow(COLUMNS)
    writer.writerows(export_rows())
    return out.getvalue()


def template_csv():
    out = io.StringIO()
    out.write('﻿')
    writer = csv.writer(out)
    writer.writerow(COLUMNS)
    writer.writerow([EXAMPLE.get(c, '') for c in COLUMNS])
    return out.getvalue()
