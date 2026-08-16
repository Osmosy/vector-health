"""
Convert [PMID:XXXXXXXX] markers in a markdown file to numbered references [1][2]...
and generate a formal bibliography section.

Usage: python remap_refs.py input.md [--output output.md]
"""

import os
import re
import sys
import json
import time
import argparse
import urllib.request
import urllib.parse
import urllib.error
import ssl
from pathlib import Path

try:
    import certifi
    _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CONTEXT = ssl.create_default_context()

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

NCBI_API_KEY = os.environ.get("NCBI_API_KEY", "").strip()

# Matches a bracket containing one or more PMID entries. Tolerates:
#   case:   [pmid:123]  [Pmid:123]  [PMID:123]
#   spaces: [PMID: 123]  [ PMID : 123 ]
#   multi:  [PMID:123, PMID:456]  [PMID:123,PMID:456]  (Chinese comma ，OK too)
PMID_BLOCK = re.compile(
    r'\[\s*pmid\s*:\s*\d+(?:\s*[,，]\s*pmid\s*:\s*\d+)*\s*\]',
    re.IGNORECASE,
)
# Extracts individual numeric IDs from inside a matched block
PMID_EXTRACT = re.compile(r'pmid\s*:\s*(\d+)', re.IGNORECASE)

CANDIDATE_SECTION_PATTERN = re.compile(
    r'\n---\n\n## References \(Candidates\)\b.*$', re.DOTALL
)

ESUMMARY_URL     = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
EMAIL            = "claude-code-skill@example.com"
_PUBMED_INTERVAL = 0.11 if NCBI_API_KEY else 0.36


def collect_pmids_in_order(text: str) -> list[str]:
    """Return unique PMIDs in first-appearance order, handling multi-PMID blocks."""
    seen: list[str] = []
    for block in PMID_BLOCK.finditer(text):
        for pmid in PMID_EXTRACT.findall(block.group()):
            if pmid not in seen:
                seen.append(pmid)
    return seen


def _get(url: str, retries: int = 4, backoff: float = 1.5) -> bytes:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "find-paper-references/2.0"}
            )
            with urllib.request.urlopen(req, timeout=20, context=_SSL_CONTEXT) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = backoff * 2 ** attempt
                print(f"  429 Too Many Requests — backing off {wait:.1f}s", file=sys.stderr)
                time.sleep(wait)
            elif attempt == retries - 1:
                raise
            else:
                time.sleep(backoff * (attempt + 1))
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(backoff * (attempt + 1))
    raise RuntimeError(f"Failed after {retries} retries")


def batch_esummary(pmids: list[str]) -> dict[str, dict]:
    """Fetch metadata for all PMIDs in one API call (up to 200 at a time)."""
    results: dict[str, dict] = {}
    chunk_size = 200
    for i in range(0, len(pmids), chunk_size):
        chunk = pmids[i:i + chunk_size]
        p = {"db": "pubmed", "id": ",".join(chunk), "retmode": "json", "email": EMAIL}
        if NCBI_API_KEY:
            p["api_key"] = NCBI_API_KEY
        params = urllib.parse.urlencode(p)
        try:
            data = json.loads(_get(f"{ESUMMARY_URL}?{params}"))
            result = data.get("result", {})
            for uid in result.get("uids", []):
                doc = result[uid]
                authors_raw = doc.get("authors", [])
                authors = (
                    authors_raw[0].get("name", "") + (" et al." if len(authors_raw) > 1 else "")
                    if authors_raw else "Unknown"
                )
                pubdate = doc.get("pubdate", "")
                doi = next(
                    (a["value"] for a in doc.get("articleids", []) if a.get("idtype") == "doi"),
                    ""
                )
                results[uid] = {
                    "pmid": uid,
                    "title": doc.get("title", "").rstrip("."),
                    "authors": authors,
                    "journal": doc.get("fulljournalname", doc.get("source", "")),
                    "year": pubdate[:4] if pubdate else "",
                    "doi": doi,
                }
        except Exception as e:
            print(f"esummary error (chunk {i}): {e}", file=sys.stderr)
        if i + chunk_size < len(pmids):
            time.sleep(_PUBMED_INTERVAL)
    return results


def format_citation(n: int, info: dict) -> str:
    authors = info.get("authors", "Unknown")
    title   = info.get("title",   "Unknown title")
    journal = info.get("journal", "")
    year    = info.get("year",    "")
    pmid    = info.get("pmid",    "")
    doi     = info.get("doi",     "")

    line = f"{n}. {authors}. {title}."
    if journal:
        line += f" *{journal}*"
    if year:
        line += f" {year}"
    if doi:
        line += f". https://doi.org/{doi}"
    elif pmid:
        line += f". PMID: {pmid}"
    return line


MIN_REFS = {"article": 30}


def get_review_target_range(text_body: str) -> tuple[int, int]:
    """
    For Review type, calculate reference count target from character count:
    ~1 ref per 100 chars, +-20% tolerance.
    Counts all non-whitespace characters as a reasonable character count estimate.
    """
    cleaned = re.sub(r'\s+', '', text_body)
    char_count = len(cleaned)
    target = char_count / 100.0
    low  = max(1, int(target * 0.8))
    high = max(low, int(target * 1.2))
    return low, high


def main():
    parser = argparse.ArgumentParser(description="Remap PMID markers to numbered references")
    parser.add_argument("input",    help="Input markdown file path")
    parser.add_argument("--output", help="Output file path (default: overwrite input)")
    parser.add_argument(
        "--type",
        choices=["article", "review"],
        default=None,
        help="Article type for reference count validation (article: >=30, review: char-count-based ~1/100chars +-20%)",
    )
    args = parser.parse_args()

    input_path  = Path(args.input)
    output_path = Path(args.output) if args.output else input_path

    if not input_path.exists():
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    text      = input_path.read_text(encoding="utf-8")
    text_body = CANDIDATE_SECTION_PATTERN.sub("", text)
    pmids     = collect_pmids_in_order(text_body)

    if not pmids:
        print("No [PMID:XXXXXXXX] markers found.", file=sys.stderr)
        sys.exit(0)

    print(f"Found {len(pmids)} unique PMIDs — fetching all in one batch...", file=sys.stderr)
    meta = batch_esummary(pmids)

    pmid_to_num: dict[str, int] = {}
    citations:   dict[str, dict] = {}
    for i, pmid in enumerate(pmids, start=1):
        pmid_to_num[pmid] = i
        info = meta.get(pmid, {"pmid": pmid, "title": f"[Could not fetch PMID {pmid}]"})
        citations[pmid] = info
        print(f"  [{i}/{len(pmids)}] PMID {pmid} — {info.get('title','')[:60]}", file=sys.stderr)

    def replace_block(m: re.Match) -> str:
        # [PMID:123, PMID:456] → [1][2]
        return "".join(
            f"[{pmid_to_num[p]}]"
            for p in PMID_EXTRACT.findall(m.group())
            if p in pmid_to_num
        )

    updated_body = PMID_BLOCK.sub(replace_block, text_body)

    bib_lines = ["\n---\n\n## References\n"]
    for pmid in pmids:
        bib_lines.append(format_citation(pmid_to_num[pmid], citations[pmid]))

    final_text = updated_body.rstrip() + "\n" + "\n".join(bib_lines) + "\n"
    output_path.write_text(final_text, encoding="utf-8")
    print(f"Done → {output_path}  ({len(pmids)} references)", file=sys.stderr)

    # ── Validation ───────────────────────────────────────────────────────────
    exit_code = 0

    # 1. Leftover marker check
    issues = validate_output(final_text)
    if issues:
        print("\n⚠  VALIDATION — leftover markers found:", file=sys.stderr)
        for line_no, snippet in issues:
            print(f"  line {line_no}: {snippet}", file=sys.stderr)
        print("  Fix these before submitting.", file=sys.stderr)
        exit_code = 2
    else:
        print("✓  No leftover markers.", file=sys.stderr)

    # 2. Reference count check
    if args.type:
        actual  = len(pmids)
        if args.type == "review":
            low, high = get_review_target_range(text_body)
            if actual < low or actual > high:
                print(
                    f"\n⚠  Reference count: {actual} unique refs"
                    f" — review (chars ~ {low * 125}) requires {low}–{high} refs."
                    f" Need {'more' if actual < low else 'fewer'}.",
                    file=sys.stderr,
                )
                exit_code = max(exit_code, 3)
            else:
                print(
                    f"✓  Reference count: {actual} in [{low}, {high}]"
                    f" (char-count-based, review requirement met).",
                    file=sys.stderr,
                )
        else:
            min_req = MIN_REFS[args.type]
            if actual < min_req:
                print(
                    f"\n⚠  Reference count: {actual} unique refs"
                    f" — {args.type} requires ≥ {min_req}."
                    f" Need {min_req - actual} more.",
                    file=sys.stderr,
                )
                exit_code = max(exit_code, 3)
            else:
                print(
                    f"✓  Reference count: {actual} ≥ {min_req} ({args.type} requirement met).",
                    file=sys.stderr,
                )

    if exit_code == 0:
        print("✓  All checks passed.", file=sys.stderr)
    sys.exit(exit_code)


def validate_output(text: str) -> list[tuple[int, str]]:
    """
    Scan the manuscript body (everything before the bibliography separator) for
    residual PMID-style markers that were NOT replaced. Returns (line_no, snippet).

    Flags:
      - Full brackets still present:   [PMID:123]  [pmid: 123]
      - Partial / malformed fragments:  [PMID:  or  PMID:123  without brackets
    Skips the ## References section, which legitimately contains "PMID: NNN" text.
    """
    # Only validate body text above the bibliography line
    bib_sep = re.search(r'\n---\n+## References', text)
    body = text[:bib_sep.start()] if bib_sep else text

    # Matches any pmid: token (bracketed or bare, full or partial)
    leftover = re.compile(r'\[?\s*pmid\s*:\s*\d*', re.IGNORECASE)

    issues: list[tuple[int, str]] = []
    for line_no, line in enumerate(body.splitlines(), start=1):
        for m in leftover.finditer(line):
            snippet = line[max(0, m.start() - 5): m.end() + 15].strip()
            issues.append((line_no, f"…{snippet}…"))
    return issues


if __name__ == "__main__":
    main()
