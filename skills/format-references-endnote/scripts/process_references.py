#!/usr/bin/env python3
"""
process_references.py - Convert [PMID: xxxx] markers to Word doc with EndNote placeholders.

Usage: python process_references.py <markdown_file>

Pipeline:
  1. Extract & deduplicate PMIDs from the .md file
  2. Fetch metadata (author, year, title, full RIS fields) from PubMed
  3. Replace [PMID: xxxx] with {FirstAuthor, Year, Title} placeholders
  4. Compile .docx via Pandoc (no --citeproc, so placeholders stay literal)
  5. Write <filename>.ris with all fetched references
  6. Open both files with the OS default program
"""

import sys
import re
import os
import json
import time
import ssl
import platform
import subprocess
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path

# Bypass SSL verification for NCBI eutils (corporate proxy cert issue)
ssl._create_default_https_context = ssl._create_unverified_context


# ── PMID extraction ──────────────────────────────────────────────────────────

def extract_pmids(text: str) -> list:
    """Return deduplicated list of PMIDs found in the text, preserving order."""
    found = re.findall(r'\[PMID:\s*(\d+)\]', text, re.IGNORECASE)
    seen = []
    for p in found:
        if p not in seen:
            seen.append(p)
    return seen


# ── PubMed API ───────────────────────────────────────────────────────────────

def _fetch_xml(pmids: list) -> str:
    """Fetch PubMed XML for a list of PMIDs."""
    ids = ','.join(pmids)
    url = (
        'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi'
        f'?db=pubmed&id={ids}&retmode=xml'
    )
    req = urllib.request.Request(url, headers={'User-Agent': 'format-references-skill/1.0'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode('utf-8')


def _text(el):
    """Recursively concatenate all text within an XML element."""
    if el is None:
        return ''
    parts = [el.text or '']
    for child in el:
        parts.append(_text(child))
        parts.append(child.tail or '')
    return ''.join(parts).strip()


def _transliterate_greek(text: str) -> str:
    """Replace Greek Unicode letters with Latin equivalents.

    EndNote may normalize Unicode Greek letters during RIS import, causing
    title mismatches with the citation placeholder. Transliterating both
    the RIS title and the placeholder ensures consistent matching.
    """
    _GREEK_MAP = {
        # Lowercase
        '\u03b1': 'alpha', '\u03b2': 'beta', '\u03b3': 'gamma',
        '\u03b4': 'delta', '\u03b5': 'epsilon', '\u03b6': 'zeta',
        '\u03b7': 'eta', '\u03b8': 'theta', '\u03b9': 'iota',
        '\u03ba': 'kappa', '\u03bb': 'lambda', '\u03bc': 'mu',
        '\u03bd': 'nu', '\u03be': 'xi', '\u03bf': 'omicron',
        '\u03c0': 'pi', '\u03c1': 'rho', '\u03c3': 'sigma',
        '\u03c2': 'sigma',  # final sigma
        '\u03c4': 'tau', '\u03c5': 'upsilon', '\u03c6': 'phi',
        '\u03c7': 'chi', '\u03c8': 'psi', '\u03c9': 'omega',
        # Uppercase
        '\u0391': 'Alpha', '\u0392': 'Beta', '\u0393': 'Gamma',
        '\u0394': 'Delta', '\u0395': 'Epsilon', '\u0396': 'Zeta',
        '\u0397': 'Eta', '\u0398': 'Theta', '\u0399': 'Iota',
        '\u039a': 'Kappa', '\u039b': 'Lambda', '\u039c': 'Mu',
        '\u039d': 'Nu', '\u039e': 'Xi', '\u039f': 'Omicron',
        '\u03a0': 'Pi', '\u03a1': 'Rho', '\u03a3': 'Sigma',
        '\u03a4': 'Tau', '\u03a5': 'Upsilon', '\u03a6': 'Phi',
        '\u03a7': 'Chi', '\u03a8': 'Psi', '\u03a9': 'Omega',
    }
    result = []
    for ch in text:
        result.append(_GREEK_MAP.get(ch, ch))
    return ''.join(result)


def _parse_articles(xml_data: str) -> dict:
    """Parse PubMed XML into a dict keyed by PMID string."""
    root = ET.fromstring(xml_data)
    result = {}
    for article in root.findall('.//PubmedArticle'):
        pmid_el = article.find('.//PMID')
        if pmid_el is None:
            continue
        pmid = pmid_el.text.strip()

        # Authors
        author_els = article.findall('.//Author')
        first_author = 'Unknown'
        all_authors = []
        for auth in author_els:
            ln = auth.findtext('LastName', '').strip()
            fn = auth.findtext('ForeName', '').strip()
            initials = auth.findtext('Initials', '').strip()
            if ln:
                display = f'{ln}, {fn}' if fn else (f'{ln} {initials}' if initials else ln)
                all_authors.append(display)
                if first_author == 'Unknown':
                    first_author = ln

        # Year — try PubDate > Year, then MedlineDate prefix, then ArticleDate
        year = 'n.d.'
        pub_date = article.find('.//PubDate')
        if pub_date is not None:
            year_el = pub_date.find('Year')
            if year_el is not None and year_el.text:
                year = year_el.text.strip()
            else:
                med = pub_date.findtext('MedlineDate', '')
                if med:
                    year = med[:4]
        if year == 'n.d.':
            ad = article.find('.//ArticleDate')
            if ad is not None:
                y = ad.findtext('Year', '')
                if y:
                    year = y.strip()

        # Title (may contain XML markup like <i>, <b> — strip tags)
        title_el = article.find('.//ArticleTitle')
        full_title = _text(title_el) if title_el is not None else ''
        # Normalize once — same string used in both RIS (TI field) and Word placeholder,
        # so EndNote CWYW always matches exactly:
        #   - normalize Unicode smart quotes/apostrophes → ASCII
        #   - transliterate Greek letters → Latin (α→alpha) so EndNote can match
        #   - strip XML markup chars that break placeholder syntax: {} []
        #   - strip trailing period (some libraries omit it)
        #   - strip commas (comma is the placeholder field delimiter)
        _normalized = full_title
        for _smart, _straight in [('\u2018', "'"), ('\u2019', "'"), ('\u201c', '"'), ('\u201d', '"'),
                                   ('\u2013', '-'), ('\u2014', '--'), ('\u00a0', ' ')]:
            _normalized = _normalized.replace(_smart, _straight)
        _normalized = _transliterate_greek(_normalized)
        full_title_clean = re.sub(r'[{}\[\]]', '', _normalized).rstrip('.').replace(',', '')
        short_title = full_title_clean

        # Journal
        journal = article.findtext('.//Journal/Title', '').strip()

        # Volume, issue, pages
        volume = article.findtext('.//Volume', '').strip()
        issue = article.findtext('.//Issue', '').strip()
        pages = article.findtext('.//MedlinePgn', '').strip()

        # DOI
        doi = ''
        for loc in article.findall('.//ELocationID'):
            if loc.get('EIdType') == 'doi':
                doi = (loc.text or '').strip()
                break

        # Abstract
        abstract_parts = []
        for ab in article.findall('.//AbstractText'):
            label = ab.get('Label', '')
            txt = _text(ab)
            if label:
                abstract_parts.append(f'{label}: {txt}')
            else:
                abstract_parts.append(txt)
        abstract = ' '.join(abstract_parts)[:500]  # cap at 500 chars for RIS

        result[pmid] = {
            'first_author': first_author,
            'year': year,
            'short_title': short_title,
            'full_title': full_title_clean,
            'all_authors': all_authors,
            'journal': journal,
            'volume': volume,
            'issue': issue,
            'pages': pages,
            'doi': doi,
            'abstract': abstract,
        }
    return result


def _load_cache(cache_path: Path) -> dict | None:
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text(encoding='utf-8'))
        except Exception:
            return None
    return None


def _save_cache(cache_path: Path, metadata: dict):
    cache_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')


def fetch_pubmed_metadata(pmids: list, cache_path: Path = None) -> dict:
    """
    Fetch metadata for all PMIDs. Batches requests (20 per call).
    Uses local JSON cache if available; only fetches new/missing PMIDs.
    """
    metadata = {}

    # Try cache first
    if cache_path:
        cached = _load_cache(cache_path)
        if cached:
            hit = 0
            for pmid in pmids:
                if pmid in cached and not cached[pmid].get('short_title', '').startswith('[fetch failed'):
                    metadata[pmid] = cached[pmid]
                    hit += 1
            pmids = [p for p in pmids if p not in metadata]
            if hit:
            print(f'  Cache hit: {hit} articles, {len(pmids)} remaining to fetch')

    if not pmids:
        return metadata

    batch_size = 20
    for i in range(0, len(pmids), batch_size):
        batch = pmids[i:i + batch_size]
        try:
            xml_data = _fetch_xml(batch)
            metadata.update(_parse_articles(xml_data))
        except (urllib.error.URLError, ET.ParseError, Exception) as exc:
            print(f'  ⚠  PubMed fetch failed for {batch}: {exc}', file=sys.stderr)
        for pmid in batch:
            if pmid not in metadata:
                metadata[pmid] = {
                    'first_author': f'PMID{pmid}',
                    'year': 'n.d.',
                    'short_title': f'[fetch failed — PMID:{pmid}]',
                    'full_title': '',
                    'all_authors': [],
                    'journal': '',
                    'volume': '',
                    'issue': '',
                    'pages': '',
                    'doi': '',
                    'abstract': '',
                }
        if i + batch_size < len(pmids):
            time.sleep(0.34)

    if cache_path:
        _save_cache(cache_path, metadata)
    return metadata


# ── Text transformation ───────────────────────────────────────────────────────

def replace_pmid_markers(text: str, metadata: dict) -> str:
    """Swap every [PMID: xxxx] with an EndNote unformatted citation placeholder.

    Uses {Author, Year, Title} format. Titles are normalized (Greek→Latin, smart
    quotes→ASCII) so they match exactly what EndNote stores after RIS import.
    """
    def _sub(m):
        pmid = m.group(1)
        meta = metadata.get(pmid, {})
        author = meta.get('first_author', f'PMID{pmid}')
        year = meta.get('year', 'n.d.')
        title = meta.get('short_title', '')
        return f'{{{author}, {year}, {title}}}'
    return re.sub(r'\[PMID:\s*(\d+)\]', _sub, text, flags=re.IGNORECASE)


# ── RIS generation ────────────────────────────────────────────────────────────

def generate_ris(metadata: dict, output_path: Path):
    """Write a RIS file containing all fetched references."""
    with output_path.open('w', encoding='utf-8') as f:
        for pmid, meta in metadata.items():
            f.write('TY  - JOUR\n')
            for author in meta.get('all_authors', []):
                f.write(f'AU  - {author}\n')
            f.write(f'PY  - {meta["year"]}\n')
            title = meta.get('full_title') or meta.get('short_title', '')
            f.write(f'TI  - {title}\n')
            if meta.get('journal'):
                f.write(f'JO  - {meta["journal"]}\n')
            if meta.get('volume'):
                f.write(f'VL  - {meta["volume"]}\n')
            if meta.get('issue'):
                f.write(f'IS  - {meta["issue"]}\n')
            if meta.get('pages'):
                f.write(f'SP  - {meta["pages"]}\n')
            if meta.get('doi'):
                f.write(f'DO  - {meta["doi"]}\n')
            if meta.get('abstract'):
                f.write(f'AB  - {meta["abstract"]}\n')
            f.write(f'AN  - {pmid}\n')
            f.write('ER  - \n\n')


# ── Pandoc compile ────────────────────────────────────────────────────────────

def compile_docx(md_path: Path, docx_path: Path) -> bool:
    """Convert the modified markdown to .docx via Pandoc (no --citeproc)."""
    try:
        result = subprocess.run(
            ['pandoc', str(md_path), '-o', str(docx_path), '--from', 'markdown-smart'],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            print(f'  Pandoc stderr: {result.stderr}', file=sys.stderr)
            return False
        return True
    except FileNotFoundError:
        print(
            '\n  Pandoc not found. Please install: https://pandoc.org/installing.html\n',
            file=sys.stderr,
        )
        return False
    except subprocess.TimeoutExpired:
        print('  Pandoc conversion timed out', file=sys.stderr)
        return False


# ── File opening ──────────────────────────────────────────────────────────────

def open_file(path: Path):
    """Open a file with the OS default application."""
    system = platform.system()
    try:
        if system == 'Windows':
            os.startfile(str(path))
        elif system == 'Darwin':
            subprocess.run(['open', str(path)], check=True)
        else:
            subprocess.run(['xdg-open', str(path)], check=True)
    except Exception as exc:
        print(f'  Cannot auto-open {path.name}: {exc}', file=sys.stderr)
        print(f'     Please open manually: {path}', file=sys.stderr)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    md_args = []
    force_refresh = False
    for a in sys.argv[1:]:
        if a == '--force-refresh':
            force_refresh = True
        else:
            md_args.append(a)

    if not md_args:
        print('Usage: python process_references.py <markdown_file> [--force-refresh]')
        sys.exit(1)

    md_file = Path(sys.argv[1]).resolve()
    if not md_file.exists():
        print(f'File does not exist: {md_file}')
        sys.exit(1)

    out_dir = md_file.parent
    stem = md_file.stem

    # ── Step 1: read & extract PMIDs ──
    print(f'\nReading file: {md_file}')
    text = md_file.read_text(encoding='utf-8')
    pmids = extract_pmids(text)
    if not pmids:
        print('No [PMID: xxxx] markers found, nothing to process.')
        sys.exit(0)
    print(f'Found {len(pmids)} unique PMIDs')

    # Cache path
    cache_path = out_dir / f'{stem}_pubmed_cache.json'
    if force_refresh and cache_path.exists():
        cache_path.unlink()
        print('  Cache cleared, will re-fetch')

    # ── Step 2: fetch PubMed metadata ──
    print('Fetching metadata from PubMed...')
    metadata = fetch_pubmed_metadata(pmids, cache_path=cache_path)

    # Integrity check
    failed_pmids = [p for p in pmids
                    if metadata.get(p, {}).get('short_title', '').startswith('[fetch failed')]
    if failed_pmids:
        print(f'  {len(failed_pmids)} PMIDs failed to fetch: {", ".join(failed_pmids)}')
        print(f'     Check network and retry: python process_references.py "<file>" --force-refresh')
    else:
        fetched = len(pmids)
        print(f'Fetch complete ({fetched}/{len(pmids)} successful)')

    # ── Step 3a: replace markers ──
    modified_text = replace_pmid_markers(text, metadata)

    # ── Step 3b: write temp .md for pandoc ──
    temp_md = out_dir / f'{stem}_pandoc_temp.md'
    temp_md.write_text(modified_text, encoding='utf-8')

    # ── Step 3c: compile .docx ──
    docx_path = out_dir / f'{stem}-endnote.docx'
    print('Generating Word document with Pandoc...')
    pandoc_ok = compile_docx(temp_md, docx_path)
    if temp_md.exists():
        temp_md.unlink()
    if pandoc_ok:
        print(f'Word document: {docx_path}')
    else:
        print('  (Skipping Word document generation, RIS file will still be written)')

    # ── Step 3d: write RIS ──
    ris_path = out_dir / f'{stem}.ris'
    generate_ris(metadata, ris_path)
    print(f'RIS file: {ris_path}')

    # ── Step 4: open files ──
    print('\nOpening files...')
    open_file(ris_path)          # triggers EndNote import
    time.sleep(2)                # give EndNote a moment to start
    if pandoc_ok and docx_path.exists():
        open_file(docx_path)

    # ── Summary ──
    print('\n' + '─' * 50)
    print('Done!')
    print()
    print('  References imported to EndNote, document opened.')
    print('  In Word, switch to the EndNote tab,')
    print('  click "Update Citations and Bibliography" to format.')
    print()
    print(f'  Processed {len(pmids)} references')
    if pandoc_ok:
        print(f'  Word document: {docx_path}')
    print(f'  RIS file:  {ris_path}')
    print('─' * 50)


if __name__ == '__main__':
    main()
