"""
Legacy field audit script for SoHo Pittsburgh.

Run from the project root on web-dev:
    python audit_legacy.py

Scans templates and views to map which legacy Banner/PanelSide fields
are referenced, and on which pages/views they appear.
"""

import os
import re
from pathlib import Path
from collections import defaultdict

BANNER_LEGACY = {
    r'banner\.title':       'Banner.title (legacy text field)',
    r'banner\.content':     'Banner.content (legacy text field)',
    r'banner\.buttons':     'Banner.buttons (BannerButton through model)',
    r'as_context':          'Banner.as_context() method',
    r'BannerButton':        'BannerButton model reference',
    r'render_button':       'render_button tag (legacy button rendering)',
}

PANEL_LEGACY = {
    r'panel\.title':        'PanelSide.title (legacy text field)',
    r'\.mode\b':            'PanelSide.mode (old text/image/map field)',
    r'panel\.button_label': 'PanelSide.button_label (legacy)',
    r'panel\.button_href':  'PanelSide.button_href (legacy)',
    r'panel\.content_slot': 'PanelSide.content_slot (old single-slot FK)',
    r'full_img':            'full_img dict key (old image mode pattern)',
    r'PANEL_MODE_CHOICES':  'PANEL_MODE_CHOICES (old mode choices list)',
    r'as_dict\(\)':         'PanelSide.as_dict() method',
    r'left\.title':         'left.title (panel as left var)',
    r'left\.mode':          'left.mode (panel as left var)',
    r'right\.title':        'right.title (panel as right var)',
    r'right\.mode':         'right.mode (panel as right var)',
}

ALL_PATTERNS = {**BANNER_LEGACY, **PANEL_LEGACY}

def find_files(root='.'):
    skip = {'migrations', '.venv', 'venv', '__pycache__', 'node_modules', '.git'}
    for path in Path(root).rglob('*'):
        if any(s in path.parts for s in skip):
            continue
        if path.suffix in ('.py', '.html'):
            yield path

def categorize_file(filepath):
    fp = filepath.replace('\\', '/')
    name = Path(fp).name
    parent = Path(fp).parent.name

    if 'templates' in fp:
        if 'about' in name:          return '📄 PAGE: about.html'
        if 'home' in name:           return '📄 PAGE: home.html'
        if 'db_banner' in name:      return '🧩 COMPONENT: db_banner_full.html'
        if 'banner_full' in name:    return '🧩 COMPONENT: banner_full.html'
        if '50_50' in name:          return '🧩 COMPONENT: 50_50.html'
        if '_panel_side' in name:    return '🧩 COMPONENT: _panel_side.html'
        if 'hero_with' in name:      return '🧩 COMPONENT: hero_with_promos.html'
        if 'staff' in fp:            return f'🔧 STAFF PORTAL: {name}'
        return f'🧩 TEMPLATE: {name}'

    if 'views.py' in name:
        return f'⚙️  VIEW: {parent}/views.py'
    if 'models.py' in name:
        return f'🗄️  MODEL: {parent}/models.py'
    if 'admin.py' in name:
        return f'🔑 ADMIN: {parent}/admin.py'
    if 'templatetags' in fp:
        return f'🏷️  TAG: {name}'
    if 'utils.py' in name:
        return f'🔧 UTILS: {parent}/utils.py'

    return f'📁 {parent}/{name}'

def audit(root='.'):
    hits = defaultdict(list)
    for filepath in find_files(root):
        try:
            lines = filepath.read_text(errors='replace').splitlines()
        except Exception:
            continue
        ftype = 'template' if filepath.suffix == '.html' else 'python'
        for i, line in enumerate(lines, 1):
            for pattern, label in ALL_PATTERNS.items():
                if re.search(pattern, line):
                    hits[pattern].append((str(filepath), i, line.strip()[:120], ftype))
    return hits

def print_report(hits):
    if not hits:
        print("✅ No legacy field references found — safe to drop all legacy fields.")
        return

    banner_patterns = set(BANNER_LEGACY.keys())
    panel_patterns  = set(PANEL_LEGACY.keys())

    def section(title, patterns):
        relevant = {p: hits[p] for p in patterns if p in hits}
        if not relevant:
            print(f"\n✅  {title} — no legacy references found")
            return
        print(f"\n{'═'*72}")
        print(f"  {title}")
        print(f"{'═'*72}")
        for pattern, occurrences in relevant.items():
            label = ALL_PATTERNS[pattern]
            print(f"\n  ⚠️  {label}")
            by_file = defaultdict(list)
            for fp, lineno, content, ftype in occurrences:
                by_file[categorize_file(fp)].append((lineno, content))
            for cat, refs in sorted(by_file.items()):
                print(f"\n     {cat}")
                for lineno, content in refs[:4]:
                    print(f"       {lineno:4d}: {content}")
                if len(refs) > 4:
                    print(f"       ... +{len(refs)-4} more lines")

    section("BANNER LEGACY FIELDS", banner_patterns)
    section("PANELSIDE LEGACY FIELDS", panel_patterns)

    # Summary — one line per file showing what it uses
    print(f"\n{'═'*72}")
    print("  SUMMARY — what needs updating before fields can be dropped")
    print(f"{'═'*72}\n")

    all_files = defaultdict(set)
    for pattern, occurrences in hits.items():
        for fp, lineno, content, ftype in occurrences:
            cat = categorize_file(fp)
            all_files[cat].add(ALL_PATTERNS[pattern])

    pages      = {k: v for k, v in all_files.items() if 'PAGE' in k}
    components = {k: v for k, v in all_files.items() if 'COMPONENT' in k}
    views      = {k: v for k, v in all_files.items() if 'VIEW' in k}
    others     = {k: v for k, v in all_files.items() if k not in {**pages, **components, **views}}

    for group_label, group in [
        ('Page templates (visitor-facing)', pages),
        ('Component templates (partials)', components),
        ('Views', views),
        ('Other files', others),
    ]:
        if not group:
            continue
        print(f"  {group_label}:")
        for cat, fields in sorted(group.items()):
            print(f"    {cat}")
            for field in sorted(fields):
                print(f"      • {field}")
        print()

    total_refs  = sum(len(v) for v in hits.values())
    total_files = len(all_files)
    print(f"  Total: {total_refs} references across {total_files} files\n")
    print("  ─── Recommended action ───────────────────────────────────────────")
    print("  Fix COMPONENT templates first (they affect all pages that use them).")
    print("  Then fix PAGE templates. Then drop the model fields.\n")

if __name__ == '__main__':
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    print(f"\nScanning: {os.path.abspath(root)}\n")
    hits = audit(root)
    print_report(hits)
