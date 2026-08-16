#!/usr/bin/env python3
"""
search_styles.py - Search and install Zotero/CSL citation styles.

Usage:
  python search_styles.py <keyword>            # search
  python search_styles.py --install <style-id> # download & install into Zotero
  python search_styles.py elsevier
  python search_styles.py --install elsevier-harvard
"""

import sys
import re
import os
import json
import ssl
import urllib.request
import urllib.error
import shutil
from pathlib import Path

# Bypass SSL certificate verification (corporate proxy SSL interception)
ssl._create_default_https_context = ssl._create_unverified_context


# ── Style search ──────────────────────────────────────────────────────────────

def search_zotero_styles(query: str) -> list:
    """Search styles via Zotero's official styles.json API."""
    url = 'https://www.zotero.org/styles-files/styles.json'
    req = urllib.request.Request(url, headers={'User-Agent': 'format-references-zotero/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            styles = json.loads(resp.read())
        q = query.lower()
        return [
            (s.get('name', ''), s.get('title', ''))
            for s in styles
            if q in s.get('title', '').lower() or q in s.get('name', '').lower()
        ]
    except Exception as e:
        print(f'  Zotero API failed: {e}, trying GitHub...')
        return search_github_styles(query)


def search_github_styles(query: str) -> list:
    """Fallback: search CSL styles via GitHub git tree API."""
    url = ('https://api.github.com/repos/citation-style-language/styles'
           '/git/trees/master?recursive=0')
    req = urllib.request.Request(url, headers={
        'User-Agent': 'format-references-zotero/1.0',
        'Accept': 'application/vnd.github+json',
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
        q = query.lower()
        return [
            (p[:-4], p[:-4])
            for item in data.get('tree', [])
            if (p := item.get('path', '')).endswith('.csl') and q in p.lower()
        ]
    except Exception as e:
        print(f'  GitHub request failed: {e}')
        return []


# ── Zotero styles directory ───────────────────────────────────────────────────

def find_zotero_styles_dir() -> Path | None:
    """
    Locate Zotero's local styles directory on Windows / macOS / Linux.

    Strategy:
    1. Find the Zotero profile directory (platform-specific)
    2. Read extensions.zotero.dataDir from prefs.js (Zotero 7+ custom path)
    3. Fall back to the platform default data dir (~/Zotero on all platforms)
    """
    import re as _re
    import platform as _platform

    system = _platform.system()

    # Platform-specific profile root
    if system == 'Windows':
        profile_roots = [
            Path(os.environ.get('APPDATA', '')) / 'Zotero' / 'Zotero' / 'Profiles',
        ]
    elif system == 'Darwin':
        profile_roots = [
            Path.home() / 'Library' / 'Application Support' / 'Zotero' / 'Profiles',
        ]
    else:  # Linux
        profile_roots = [
            Path.home() / '.zotero' / 'zotero',
        ]

    # 1. Read dataDir from prefs.js
    for profile_root in profile_roots:
        if not profile_root.exists():
            continue
        for prefs_js in profile_root.glob('*/prefs.js'):
            text = prefs_js.read_text(encoding='utf-8', errors='ignore')
            m = _re.search(r'extensions\.zotero\.dataDir",\s*"([^"]+)"', text)
            if m:
                raw = m.group(1).replace('\\\\', '\\')
                data_dir = Path(raw)
                styles = data_dir / 'styles'
                if styles.exists():
                    return styles
                if data_dir.exists():
                    styles.mkdir(exist_ok=True)
                    return styles

    # 2. Older installs: styles live inside profile directory
    for profile_root in profile_roots:
        if not profile_root.exists():
            continue
        for styles_dir in profile_root.glob('*/zotero/styles'):
            if styles_dir.is_dir():
                return styles_dir

    # 3. Default data dir: ~/Zotero/styles (same on all platforms for Zotero 7)
    default = Path.home() / 'Zotero' / 'styles'
    if default.parent.exists():
        default.mkdir(exist_ok=True)
        return default

    return None


def is_style_installed(style_id: str) -> bool:
    styles_dir = find_zotero_styles_dir()
    if not styles_dir:
        return False
    return (styles_dir / f'{style_id}.csl').exists()


# ── Style install ─────────────────────────────────────────────────────────────

def install_style(style_id: str) -> bool:
    """
    Download style_id.csl from Zotero and place it in Zotero's styles dir.
    Returns True on success.
    """
    styles_dir = find_zotero_styles_dir()
    if not styles_dir:
        print('  Zotero styles directory not found, please install manually:')
        print(f'     Zotero -> Edit -> Preferences -> Cite -> Styles -> Search {style_id}')
        return False

    dest = styles_dir / f'{style_id}.csl'
    if dest.exists():
        print(f'  {style_id} already installed')
        return True

    # Download from Zotero repository
    url = f'https://www.zotero.org/styles/{style_id}'
    req = urllib.request.Request(url, headers={'User-Agent': 'format-references-zotero/1.0'})
    try:
        print(f'  Downloading {style_id}.csl ...', end=' ', flush=True)
        with urllib.request.urlopen(req, timeout=15) as resp:
            csl = resp.read()
        dest.write_bytes(csl)
        print(f'Installed to {dest}')
        return True
    except Exception as e:
        print(f'Download failed: {e}')
        return False


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    if not args:
        print('Usage:')
        print('  python search_styles.py <keyword>')
        print('  python search_styles.py --install <style-id>')
        sys.exit(1)

    if args[0] == '--install':
        if len(args) < 2:
            print('Usage: python search_styles.py --install <style-id>')
            sys.exit(1)
        style_id = args[1]
        print(f'\nInstalling style: {style_id}\n')
        ok = install_style(style_id)
        if ok:
            print('\nInstallation complete. If Zotero is running, restart to take effect.\n')
        sys.exit(0 if ok else 1)

    # Search mode
    query = ' '.join(args)
    print(f'\nSearching styles: "{query}"\n')
    results = search_zotero_styles(query)

    if not results:
        print('No matching styles found.')
        sys.exit(0)

    styles_dir = find_zotero_styles_dir()
    print(f'Found {len(results)} styles:\n')
    print(f'  {"I"} {"Style ID":<45} Name')
    print(f'  {"-"} {"-"*45} {"-"*35}')
    for style_id, title in results:
        installed = '✓' if styles_dir and (styles_dir / f'{style_id}.csl').exists() else ' '
        print(f'  {installed} {style_id:<45} {title}')

    print()
    print('Installed = yes    Install command: python search_styles.py --install <style-id>')
    print(f'\nUsage:')
    print(f'  python process_references.py <file.md> --style {results[0][0]}')
    print()


if __name__ == '__main__':
    main()
