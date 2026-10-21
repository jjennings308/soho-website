"""
Menu CSV import / export engine (CLAUDE.md "Menu CSV import / export", Phase M1).

One CSV per kind, imported in KIND_ORDER; each kind finds the records before
it by slug or name. Export writes the same columns, so an export can be edited
and re-imported.

    result = parse('items', csv_text)    # validate only — nothing saved
    result = apply('items', csv_text)    # re-validate and save all rows or none

Cell rules:
  - blank  → keep the existing value (on create: the model default)
  - '-'    → clear the field
  - choices accept the code or the label; booleans yes/no, true/false, 1/0, y/n
  - numbers plain (12.50), dates YYYY-MM-DD, times HH:MM, date-times
    'YYYY-MM-DD HH:MM' in local (Eastern) time
Rows are validated by ModelForms built from exactly the fields a row sets, so
imports obey the same field and unique rules as manual edits. Imports never
delete; any row error refuses the whole file.
"""
import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from html import escape, unescape

from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction
from django.forms import modelform_factory
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.text import slugify
from django_ckeditor_5.fields import CKEditor5Field

from apps.core.models import ColorScheme

from .models import (
    Menu, MenuCategory, MenuCategoryAssignment, MenuItem, MenuItemAddon,
    MenuItemCategoryAssignment, MenuItemVariation, MenuSubCategory,
)

CLEAR = '-'
BOOL_TRUE = {'yes', 'y', 'true', '1'}
BOOL_FALSE = {'no', 'n', 'false', '0'}


class CellError(ValueError):
    """A cell that can't be read; the message is shown to the user."""


# ── Rich text ↔ plain text ────────────────────────────────────────────────────

def html_to_text(html):
    """Plain text for export: paragraphs separated by a blank line."""
    text = re.sub(r'<br\s*/?>', '\n', html or '', flags=re.IGNORECASE)
    text = re.sub(r'</(p|div|h[1-6]|li|blockquote)>', '\n\n', text, flags=re.IGNORECASE)
    return normalize_text(unescape(strip_tags(text)).replace('\xa0', ' '))


def normalize_text(text):
    paragraphs = re.split(r'\n\s*\n', (text or '').replace('\r\n', '\n').replace('\r', '\n'))
    cleaned = ['\n'.join(line.strip() for line in p.strip().split('\n')) for p in paragraphs]
    return '\n\n'.join(p for p in cleaned if p)


def text_to_html(text):
    """Imported plain text → one <p> per paragraph, line breaks kept."""
    paragraphs = normalize_text(text).split('\n\n') if text else []
    return ''.join(f'<p>{"<br>".join(escape(line) for line in p.split(chr(10)))}</p>' for p in paragraphs if p)


# ── Columns ───────────────────────────────────────────────────────────────────

class Column:
    """
    One CSV column. `type` is inferred from the model field unless given:
    text, bool, choice, decimal, int, date, time, datetime, html, ref.
    For type 'ref', `ref` names a resolver in RESOLVERS and `ref_field` the
    attribute used when exporting the related object (slug or name).
    """

    def __init__(self, name, field=None, type=None, ref=None, ref_field='slug'):
        self.name = name
        self.field = field or name
        self.type = type
        self.ref = ref
        self.ref_field = ref_field

    def bind(self, model):
        self.model_field = model._meta.get_field(self.field)
        if self.type:
            return
        f = self.model_field
        if isinstance(f, models.ForeignKey):
            self.type = 'ref'
        elif isinstance(f, CKEditor5Field):
            self.type = 'html'
        elif isinstance(f, models.BooleanField):
            self.type = 'bool'
        elif f.choices:
            self.type = 'choice'
        elif isinstance(f, models.DecimalField):
            self.type = 'decimal'
        elif isinstance(f, models.IntegerField):
            self.type = 'int'
        elif isinstance(f, models.DateTimeField):
            self.type = 'datetime'
        elif isinstance(f, models.DateField):
            self.type = 'date'
        elif isinstance(f, models.TimeField):
            self.type = 'time'
        else:
            self.type = 'text'

    # Canonical text: what export writes, and what a cell is normalised to,
    # so "unchanged" is a plain string comparison.

    def export(self, instance):
        value = getattr(instance, self.field, None) if self.type != 'ref' else self._related(instance)
        if value is None:
            return ''
        if self.type == 'ref':
            return getattr(value, self.ref_field)
        if self.type == 'bool':
            return 'yes' if value else 'no'
        if self.type == 'html':
            return html_to_text(value)
        if self.type == 'date':
            return value.isoformat()
        if self.type == 'time':
            return value.strftime('%H:%M')
        if self.type == 'datetime':
            return timezone.localtime(value).strftime('%Y-%m-%d %H:%M')
        if self.type == 'decimal':
            return str(value.quantize(Decimal(1).scaleb(-self.model_field.decimal_places)))
        return str(value)

    def _related(self, instance):
        try:
            return getattr(instance, self.field)
        except ObjectDoesNotExist:
            return None

    def canonical(self, cell):
        """Normalise a non-blank, non-'-' cell to export format, or raise CellError."""
        t = self.type
        if t == 'bool':
            low = cell.lower()
            if low in BOOL_TRUE:
                return 'yes'
            if low in BOOL_FALSE:
                return 'no'
            raise CellError(f'"{cell}" is not yes/no')
        if t == 'choice':
            for code, label in self.model_field.choices:
                if cell == str(code) or cell.lower() == str(label).lower():
                    return str(code)
            allowed = ', '.join(str(code) for code, _ in self.model_field.choices)
            raise CellError(f'"{cell}" is not one of: {allowed}')
        if t == 'decimal':
            try:
                value = Decimal(cell.replace(',', ''))
            except InvalidOperation:
                raise CellError(f'"{cell}" is not a number (use e.g. 12.50, no currency sign)')
            return str(value.quantize(Decimal(1).scaleb(-self.model_field.decimal_places)))
        if t == 'int':
            try:
                return str(int(cell))
            except ValueError:
                raise CellError(f'"{cell}" is not a whole number')
        if t == 'date':
            try:
                return date.fromisoformat(cell).isoformat()
            except ValueError:
                raise CellError(f'"{cell}" is not a date (use YYYY-MM-DD)')
        if t == 'time':
            for fmt in ('%H:%M', '%H:%M:%S'):
                try:
                    return datetime.strptime(cell, fmt).strftime('%H:%M')
                except ValueError:
                    pass
            raise CellError(f'"{cell}" is not a time (use HH:MM, 24-hour)')
        if t == 'datetime':
            for fmt in ('%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
                try:
                    return datetime.strptime(cell, fmt).strftime('%Y-%m-%d %H:%M')
                except ValueError:
                    pass
            raise CellError(f'"{cell}" is not a date and time (use YYYY-MM-DD HH:MM)')
        if t == 'html':
            return normalize_text(cell)
        return cell

    def form_value(self, canonical):
        """Canonical text → value for the ModelForm's data dict."""
        if self.type == 'bool':
            return canonical == 'yes'
        if self.type == 'html':
            return text_to_html(canonical)
        return canonical


# ── Lookups (slug or name) ────────────────────────────────────────────────────

def _one(queryset, value, what):
    matches = list(queryset[:2])
    if not matches:
        raise CellError(f'no {what} "{value}"')
    if len(matches) > 1:
        raise CellError(f'"{value}" matches more than one {what} — use its slug')
    return matches[0]


def _by_slug_or_name(model, name_field, what):
    def resolve(value, row):
        obj = model.objects.filter(slug=value).first()
        if obj:
            return obj
        return _one(model.objects.filter(**{f'{name_field}__iexact': value}), value, what)
    return resolve


def _subcategory(value, row):
    category = row.refs.get('category')
    if category is None:
        if row.raw.get('category'):
            return None                     # the category's own error is reported
        raise CellError('needs a category to look up the subcategory')
    qs = MenuSubCategory.objects.filter(category=category)
    obj = qs.filter(slug=value).first()
    return obj or _one(qs.filter(name__iexact=value), value, f'subcategory in "{category.slug}"')


RESOLVERS = {
    'category': _by_slug_or_name(MenuCategory, 'name', 'category'),
    'item': _by_slug_or_name(MenuItem, 'name', 'item'),
    'menu': lambda value, row: _one(Menu.objects.filter(slug=value), value, 'menu (by slug)'),
    'color_scheme': lambda value, row: _one(ColorScheme.objects.filter(name__iexact=value), value, 'color scheme'),
    'subcategory': _subcategory,
}


# ── Kinds ─────────────────────────────────────────────────────────────────────

@dataclass
class Kind:
    name: str
    model: type
    columns: list
    # Columns that identify a record; a row matching an existing record updates it.
    key: tuple
    export_order: tuple
    # (row) → existing instance or None, given row.values / row.refs.
    find: object = None
    # (row) → slug for a new record whose slug cell is blank, or None.
    default_slug: object = None

    def __post_init__(self):
        for col in self.columns:
            col.bind(self.model)
        self.by_name = {c.name: c for c in self.columns}


def _slug_key(name_col):
    """Match by slug, else by the slugified name/title (spec)."""
    def find(kind, row):
        slug = row.values.get('slug') or slugify(row.values.get(name_col, ''))
        return kind.model.objects.filter(slug=slug).first() if slug else None
    return find


def _ref_key(*cols, name_col=None):
    """Match by referenced records (+ case-insensitive name)."""
    def find(kind, row):
        if any(row.refs.get(c) is None for c in cols):
            return None
        lookup = {kind.by_name[c].field: row.refs[c] for c in cols}
        if name_col:
            if not row.values.get(name_col):
                return None
            lookup[f'{name_col}__iexact'] = row.values[name_col]
        return kind.model.objects.filter(**lookup).first()
    return find


C = Column
KINDS = {k.name: k for k in [
    Kind('categories', MenuCategory, [
        C('name'), C('display_name'), C('slug'), C('category_type'), C('description'),
        C('order'), C('is_active'), C('show_disclaimer'),
    ], key=('slug',), export_order=('order', 'name'),
        find=_slug_key('name'),
        default_slug=lambda row: slugify(row.values.get('name', ''))),

    Kind('subcategories', MenuSubCategory, [
        C('category', ref='category'), C('name'), C('display_name'), C('slug'), C('description'),
        C('order'), C('is_active'),
    ], key=('category', 'name'), export_order=('category__order', 'category__name', 'order', 'name'),
        find=_ref_key('category', name_col='name'),
        default_slug=lambda row: (f"{row.refs['category'].slug}-{slugify(row.values.get('name', ''))}"
                                  if row.refs.get('category') else None)),

    Kind('items', MenuItem, [
        C('name'), C('slug'), C('short_description'), C('description'), C('price_display'),
        C('price'), C('sale_price'), C('dietary_type'), C('is_gluten_free'), C('is_vegan'),
        C('is_dairy_free'), C('is_nut_free'), C('contains_shellfish'), C('allergen_info'),
        C('spice_level'), C('calories'), C('preparation_time'), C('is_featured'),
        C('is_chef_special'), C('is_new'), C('is_seasonal'), C('is_available'),
        C('available_from'), C('available_until'), C('has_variations'), C('has_addons'),
    ], key=('slug',), export_order=('name', 'slug'),
        find=_slug_key('name'),
        default_slug=lambda row: slugify(row.values.get('name', ''))),

    Kind('variations', MenuItemVariation, [
        C('item', field='menu_item', ref='item'), C('name'), C('description'), C('price'),
        C('size'), C('quantity'), C('order'), C('is_default'), C('is_available'),
    ], key=('item', 'name'), export_order=('menu_item__name', 'order', 'name'),
        find=_ref_key('item', name_col='name')),

    Kind('addons', MenuItemAddon, [
        C('item', field='menu_item', ref='item'), C('name'), C('description'), C('price'),
        C('order'), C('is_default'), C('is_available'),
    ], key=('item', 'name'), export_order=('menu_item__name', 'order', 'name'),
        find=_ref_key('item', name_col='name')),

    Kind('menus', Menu, [
        C('title'), C('display_name'), C('slug'), C('description'), C('menu_type'), C('role'),
        C('is_default'), C('color_scheme', ref='color_scheme', ref_field='name'), C('homepage_slot'),
        C('valid_from'), C('valid_until'), C('is_active'), C('active_from'), C('active_until'),
    ], key=('slug',), export_order=('menu_type', 'title'),
        find=_slug_key('title'),
        default_slug=lambda row: slugify(row.values.get('title', ''))),

    Kind('menu_categories', MenuCategoryAssignment, [
        C('menu', ref='menu'), C('category', ref='category'), C('display_order'),
    ], key=('menu', 'category'), export_order=('menu__menu_type', 'menu__title', 'display_order'),
        find=_ref_key('menu', 'category')),

    Kind('placements', MenuItemCategoryAssignment, [
        C('item', field='menu_item', ref='item'), C('category', ref='category'),
        C('subcategory', ref='subcategory', ref_field='name'), C('order'), C('override_price'),
        C('note'), C('is_active'),
    ], key=('item', 'category'),
        export_order=('category__order', 'category__name', 'subcategory__order', 'order', 'menu_item__name'),
        find=_ref_key('item', 'category')),
]}
KIND_ORDER = list(KINDS)


# ── Parse / apply ─────────────────────────────────────────────────────────────

@dataclass
class Row:
    line: int
    raw: dict
    action: str = ''            # new / update / unchanged / error
    label: str = ''
    values: dict = field(default_factory=dict)    # column → canonical text (non-blank cells)
    refs: dict = field(default_factory=dict)      # ref column → resolved object
    changes: dict = field(default_factory=dict)   # column → (old, new) canonical text
    notes: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    instance: object = None
    form: object = None


@dataclass
class Result:
    kind: str
    columns: list = field(default_factory=list)
    rows: list = field(default_factory=list)
    errors: list = field(default_factory=list)    # file-level

    @property
    def ok(self):
        return not self.errors and not any(r.errors for r in self.rows)

    def count(self, action):
        return sum(1 for r in self.rows if r.action == action)


class ImportRefused(Exception):
    def __init__(self, result):
        self.result = result
        super().__init__(f'{result.kind}: import refused — fix the errors and try again')


def read_csv_bytes(data):
    """Decode an uploaded/opened CSV: UTF-8 (with or without Excel's BOM), else Windows-1252."""
    try:
        return data.decode('utf-8-sig')
    except UnicodeDecodeError:
        return data.decode('cp1252')


def parse(kind_name, csv_text):
    """Validate a CSV for one kind. Saves nothing."""
    kind = KINDS[kind_name]
    result = Result(kind=kind_name)
    reader = csv.DictReader(io.StringIO(csv_text.lstrip('﻿')))
    headers = [(h or '').strip().lower() for h in (reader.fieldnames or [])]
    result.columns = headers
    if not headers:
        result.errors.append('The file is empty.')
        return result
    unknown = [h for h in headers if h not in kind.by_name]
    if unknown:
        result.errors.append(
            f'Unknown column(s): {", ".join(unknown)}. Allowed: {", ".join(c.name for c in kind.columns)}.')
        return result

    seen_keys = {}
    for line, raw in enumerate(reader, start=2):
        cells = {(k or '').strip().lower(): (v or '').strip() for k, v in raw.items() if k is not None}
        if not any(cells.values()):
            continue
        row = Row(line=line, raw=cells)
        result.rows.append(row)
        _parse_row(kind, row)
        row.label = row.label or _label(kind, row)
        if not row.errors:
            key = tuple(_key_part(kind, row, c) for c in kind.key)
            if key in seen_keys:
                row.errors.append(f'same record as line {seen_keys[key]} ({", ".join(kind.key)})')
            else:
                seen_keys[key] = line

    if kind_name == 'menus':
        _check_menu_roles(result)
    for row in result.rows:
        if row.errors:
            row.action = 'error'
    return result


def _key_part(kind, row, col):
    if col in row.refs:
        return row.refs[col].pk
    if col == 'slug':
        return row.instance.slug if row.instance else row.changes.get('slug', ('', ''))[1].lower()
    return row.values.get(col, '').lower()


def _parse_row(kind, row):
    # 1. Normalise cells and resolve lookups, in column order (a subcategory
    #    lookup needs the row's category resolved first).
    unreadable = []
    for col in kind.columns:
        name, cell = col.name, row.raw.get(col.name, '')
        if not cell:
            continue
        try:
            if cell == CLEAR:
                row.values[name] = CLEAR
            elif col.type == 'ref':
                row.refs[name] = RESOLVERS[col.ref](cell, row)
                row.values[name] = cell
            else:
                row.values[name] = col.canonical(cell)
        except CellError as exc:
            if col.type == 'ref':
                row.errors.append(f'{name}: {exc}')
            else:
                unreadable.append((col, cell, exc))
    if row.errors:
        return

    # 2. Find the existing record; build the before/after picture.
    row.instance = kind.find(kind, row)
    for col, cell, exc in unreadable:
        # A value that is no longer valid but is exactly what's stored (e.g. a
        # legacy choice, re-imported from an export) is simply unchanged.
        if not (row.instance and cell == col.export(row.instance)):
            row.errors.append(f'{col.name}: {exc}')
    if row.errors:
        return
    base = row.instance or kind.model()
    data, fields = {}, []
    for col in kind.columns:
        if col.name not in row.values:
            continue
        old = col.export(base)
        value = row.values[col.name]
        if value == CLEAR:
            new = ''
        elif col.type == 'ref':
            new = getattr(row.refs[col.name], col.ref_field)
        else:
            new = value
        if row.instance and new == old:
            continue                                   # unchanged cell
        row.changes[col.name] = (old, new)
        fields.append(col.field)
        if col.type == 'ref':
            data[col.field] = row.refs[col.name].pk if value != CLEAR else ''
        else:
            data[col.field] = col.form_value(new)

    if not row.instance:
        # New record: blank cells take the model's defaults; slug may be derived.
        if not row.values.get('slug') and kind.default_slug and 'slug' in kind.by_name:
            slug = kind.default_slug(row)
            if slug:
                row.changes['slug'] = ('', slug)
                data['slug'] = slug
                fields.append('slug')
        for col in kind.columns:
            if col.field not in fields:
                fields.append(col.field)
                # Blank lookups go in empty so the form reports required ones.
                data[col.field] = '' if col.type == 'ref' else col.form_value(col.export(base))
    row.label = _label(kind, row)

    if row.instance and not fields:
        row.action = 'unchanged'
        return

    # 3. Validate through a ModelForm of exactly these fields.
    form_class = modelform_factory(kind.model, form=forms.ModelForm, fields=fields)
    row.form = form_class(data=data, instance=row.instance)
    if not row.form.is_valid():
        for fname, errs in row.form.errors.items():
            col = next((c.name for c in kind.columns if c.field == fname), fname)
            for err in errs:
                row.errors.append(f'{col}: {err}' if fname != '__all__' else err)
        return
    row.action = 'update' if row.instance else 'new'


def _label(kind, row):
    v, refs, inst = row.values, row.refs, row.instance
    def ref(name):
        obj = refs.get(name) or (kind.by_name[name]._related(inst) if inst else None)
        return getattr(obj, 'slug', None) or getattr(obj, 'name', '') if obj else row.raw.get(name, '?')
    if kind.name in ('categories', 'items'):
        return v.get('name') or (inst.name if inst else v.get('slug', ''))
    if kind.name == 'menus':
        return v.get('title') or (inst.title if inst else v.get('slug', ''))
    if kind.name == 'subcategories':
        return f"{ref('category')} / {v.get('name', '')}"
    if kind.name in ('variations', 'addons'):
        return f"{ref('item')} / {v.get('name', '')}"
    if kind.name == 'menu_categories':
        return f"{ref('menu')} / {ref('category')}"
    return f"{ref('item')} in {ref('category')}"


def _check_menu_roles(result):
    """One menu per non-'none' role; note roles taken from menus not in the file."""
    labels = dict(Menu.ROLE_CHOICES)
    in_file = {r.instance.pk for r in result.rows if r.instance}
    holders = {}
    for row in result.rows:
        if row.errors:
            continue
        role = row.changes['role'][1] if 'role' in row.changes else (row.instance.role if row.instance else 'none')
        if role in ('', 'none'):
            continue
        if role in holders:
            row.errors.append(f'role: {labels.get(role, role)} is also set on line {holders[role]}')
            continue
        holders[role] = row.line
        if 'role' in row.changes:
            other = Menu.objects.filter(role=role).exclude(pk=getattr(row.instance, 'pk', None)).first()
            if other and other.pk not in in_file:
                row.notes.append(f'takes {labels.get(role, role)} from "{other.title}" (it becomes No special role)')


def apply(kind_name, csv_text):
    """Re-validate and save every new/changed row in one transaction, or raise ImportRefused."""
    with transaction.atomic():
        result = parse(kind_name, csv_text)
        if not result.ok:
            raise ImportRefused(result)
        for row in result.rows:
            if row.action in ('new', 'update'):
                row.instance = row.form.save()
    return result


# ── Export ────────────────────────────────────────────────────────────────────

def export_rows(kind_name):
    kind = KINDS[kind_name]
    related = [c.field for c in kind.columns if c.type == 'ref']
    qs = kind.model.objects.select_related(*related).order_by(*kind.export_order)
    for obj in qs:
        yield [c.export(obj) for c in kind.columns]


def export_csv(kind_name):
    """CSV text (with a BOM so Excel reads UTF-8) in the import's columns."""
    out = io.StringIO()
    out.write('﻿')
    writer = csv.writer(out)
    writer.writerow([c.name for c in KINDS[kind_name].columns])
    writer.writerows(export_rows(kind_name))
    return out.getvalue()
