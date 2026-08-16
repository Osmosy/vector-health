"""
Batch PubMed/LitSense search — parallel queries, single batch esummary.

API key (optional):
  Set env var NCBI_API_KEY to your free NCBI key.
  Without key: 3 req/s limit, 4 workers.
  With key:   10 req/s limit, 8 workers.
  Get a free key at: https://www.ncbi.nlm.nih.gov/account/

Usage:
  python batch_search.py queries.json [--max N] [--workers N]

Input JSON:
  [{"id":1, "description":"...", "query":"English query", "method":"pubmed"}, ...]
  method: "pubmed" | "litsense" | "auto"

Output JSON to stdout:
  [{"id":1, "description":"...", "results":[{pmid,title,authors,journal,year,doi,abstract}]}, ...]
"""

import os
import sys
import json
import time
import argparse
import threading
import urllib.request
import urllib.parse
import urllib.error
import ssl
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import certifi
    _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CONTEXT = ssl.create_default_context()

# Allow disabling SSL verification for corporate proxy environments
_NO_VERIFY_SSL = os.environ.get("NCBI_NO_VERIFY_SSL", "").strip().lower() in ("1", "true", "yes")
if _NO_VERIFY_SSL:
    _SSL_CONTEXT.check_hostname = False
    _SSL_CONTEXT.verify_mode = ssl.CERT_NONE

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ESEARCH_URL  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL   = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
LITSENSE_URL = "https://www.ncbi.nlm.nih.gov/research/litsense-api/api/"
EMAIL        = "claude-code-skill@example.com"
TIMEOUT      = 20

# ── API key & rate limits ────────────────────────────────────────────────────

NCBI_API_KEY = os.environ.get("NCBI_API_KEY", "").strip()

if NCBI_API_KEY:
    # With API key: NCBI allows 10 req/s
    _PUBMED_INTERVAL = 0.11   # ~9/s, leave headroom
    _DEFAULT_WORKERS = 8
    print(f"NCBI API key detected — rate limit: 10 req/s, workers: {_DEFAULT_WORKERS}", file=sys.stderr)
else:
    # Without key: NCBI allows 3 req/s
    _PUBMED_INTERVAL = 0.36   # ~2.8/s, stay safely under 3/s
    _DEFAULT_WORKERS = 4
    print("No NCBI_API_KEY — rate limit: 3 req/s, workers: 4", file=sys.stderr)
    print("  (Set NCBI_API_KEY env var for 10 req/s: https://www.ncbi.nlm.nih.gov/account/)", file=sys.stderr)

_LITSENSE_INTERVAL = 1.05   # LitSense: 1 req/s

# Rate-limiter state
_pubmed_lock   = threading.Lock()
_litsense_lock = threading.Lock()
_pubmed_last   = [0.0]
_litsense_last = [0.0]


def _rate_wait(lock, last_arr, min_interval: float) -> None:
    with lock:
        elapsed = time.time() - last_arr[0]
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        last_arr[0] = time.time()


def _ncbi_params(**kwargs) -> dict:
    """Base params for every NCBI call — always include email and key if present."""
    p = {"email": EMAIL, **kwargs}
    if NCBI_API_KEY:
        p["api_key"] = NCBI_API_KEY
    return p


# ── HTTP helper with 429 back-off ────────────────────────────────────────────

def _get(url: str, retries: int = 4, backoff: float = 1.5) -> bytes:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "find-paper-references/2.0"}
            )
            with urllib.request.urlopen(req, timeout=TIMEOUT, context=_SSL_CONTEXT) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = backoff * 2 ** attempt   # 1.5s, 3s, 6s, 12s
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
    raise RuntimeError(f"Failed after {retries} retries: {url[:80]}")


# ── PubMed esearch ───────────────────────────────────────────────────────────

def pubmed_search(query: str, max_results: int) -> list[str]:
    _rate_wait(_pubmed_lock, _pubmed_last, _PUBMED_INTERVAL)
    params = urllib.parse.urlencode(_ncbi_params(
        db="pubmed", term=query, retmax=max_results, retmode="json"
    ))
    try:
        data = json.loads(_get(f"{ESEARCH_URL}?{params}"))
        return data["esearchresult"].get("idlist", [])
    except Exception as e:
        print(f"  [esearch error] {query[:60]}: {e}", file=sys.stderr)
        return []


# ── LitSense semantic search ─────────────────────────────────────────────────

def litsense_search(query: str, max_results: int) -> list[str]:
    _rate_wait(_litsense_lock, _litsense_last, _LITSENSE_INTERVAL)
    params = urllib.parse.urlencode({"query": query, "rerank": "true"})
    try:
        data = json.loads(_get(f"{LITSENSE_URL}?{params}").decode("utf-8"))
        seen, pmids = set(), []
        for item in data:
            pmid = str(item.get("pmid", "")).strip()
            if pmid and pmid not in seen:
                seen.add(pmid); pmids.append(pmid)
                if len(pmids) >= max_results:
                    break
        return pmids
    except Exception as e:
        print(f"  [litsense error] {query[:60]}: {e}", file=sys.stderr)
        return []


# ── Batch efetch (XML, with abstracts) ───────────────────────────────────────

def _parse_abstract(article_elem) -> str:
    """Extract abstract text from a PubmedArticle XML element."""
    parts = []
    abs_elem = article_elem.find(".//Abstract")
    if abs_elem is None:
        return ""
    for child in abs_elem:
        label = child.get("Label", "")
        text = "".join(child.itertext()).strip()
        if label:
            parts.append(f"{label}: {text}")
        else:
            parts.append(text)
    return " ".join(parts)


def batch_efetch(all_pmids: list[str]) -> dict[str, dict]:
    """Fetch metadata + abstracts via EFetch XML. Returns {pmid: {pmid, title, authors, first_author, journal, year, doi, abstract}}."""
    if not all_pmids:
        return {}
    results: dict[str, dict] = {}
    chunk_size = 100  # EFetch chunks smaller than ESummary
    for i in range(0, len(all_pmids), chunk_size):
        chunk = all_pmids[i:i + chunk_size]
        _rate_wait(_pubmed_lock, _pubmed_last, _PUBMED_INTERVAL)
        params = urllib.parse.urlencode(_ncbi_params(
            db="pubmed", id=",".join(chunk), rettype="abstract", retmode="xml"
        ))
        try:
            xml_bytes = _get(f"{EFETCH_URL}?{params}")
            root = ET.fromstring(xml_bytes)
            for article in root.findall(".//PubmedArticle"):
                medline = article.find(".//MedlineCitation")
                if medline is None:
                    continue
                pmid_elem = medline.find("PMID")
                if pmid_elem is None:
                    continue
                pmid = pmid_elem.text

                article_elem = medline.find("Article")
                if article_elem is None:
                    continue

                title_elem = article_elem.find("ArticleTitle")
                title = "".join(title_elem.itertext()).strip().rstrip(".") if title_elem is not None else ""

                # Authors
                author_list = article_elem.find("AuthorList")
                authors = []
                first_author = "Unknown"
                if author_list is not None:
                    for au in author_list.findall("Author"):
                        ln = au.findtext("LastName", "")
                        fn = au.findtext("ForeName", "")
                        if ln:
                            authors.append(f"{ln} {fn}".strip())
                    if authors:
                        first_author = authors[0] + (" et al." if len(authors) > 1 else "")

                # Journal
                journal_elem = article_elem.find("Journal")
                journal = ""
                if journal_elem is not None:
                    jn = journal_elem.findtext("ISOAbbreviation", "")
                    jf = journal_elem.findtext("Title", "")
                    journal = jn or jf or ""

                # Year
                pubdate = ""
                if journal_elem is not None:
                    jd = journal_elem.find("JournalIssue")
                    if jd is not None:
                        pd = jd.find("PubDate")
                        if pd is not None:
                            y = pd.findtext("Year", "")
                            m = pd.findtext("MedlineDate", "")
                            pubdate = y or (m[:4] if m else "")

                # DOI
                doi = ""
                for aid in article_elem.findall(".//ArticleIdList/ArticleId"):
                    if aid.get("IdType") == "doi":
                        doi = aid.text or ""
                        break

                # Abstract
                abstract = _parse_abstract(article_elem)

                results[pmid] = {
                    "pmid": pmid,
                    "title": title,
                    "authors": first_author,
                    "first_author": first_author,
                    "journal": journal,
                    "year": pubdate,
                    "doi": doi,
                    "abstract": abstract,
                }
        except Exception as e:
            print(f"  [efetch error] chunk {i}: {e}", file=sys.stderr)
    return results


# ── Per-query worker ─────────────────────────────────────────────────────────

def search_one(item: dict, max_results: int) -> tuple[int, list[str]]:
    qid    = item["id"]
    query  = item["query"]
    method = item.get("method", "pubmed").lower()

    pmids: list[str] = []
    if method in ("litsense", "auto"):
        pmids = litsense_search(query, max_results)
        print(f"  [{qid}] litsense '{query[:50]}' → {len(pmids)} hits", file=sys.stderr)

    if method == "pubmed" or (method == "auto" and len(pmids) < 2):
        pub_pmids = pubmed_search(query, max_results)
        print(f"  [{qid}] pubmed   '{query[:50]}' → {len(pub_pmids)} hits", file=sys.stderr)
        seen = set(pmids)
        for p in pub_pmids:
            if p not in seen:
                pmids.append(p); seen.add(p)

    return qid, pmids[:max_results]


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("queries_file", help="JSON file with query list")
    parser.add_argument("--max",     type=int, default=5,               help="Max results per query")
    parser.add_argument("--workers", type=int, default=_DEFAULT_WORKERS, help="Parallel workers")
    args = parser.parse_args()

    with open(args.queries_file, encoding="utf-8") as f:
        queries = json.load(f)

    print(
        f"Batch search: {len(queries)} queries, max {args.max}, {args.workers} workers",
        file=sys.stderr,
    )
    t0 = time.time()

    id_to_pmids: dict[int, list[str]] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(search_one, item, args.max): item["id"] for item in queries}
        for fut in as_completed(futures):
            qid, pmids = fut.result()
            id_to_pmids[qid] = pmids

    all_pmids = list({p for pmids in id_to_pmids.values() for p in pmids})
    print(f"Phase 2: fetching metadata + abstracts for {len(all_pmids)} unique PMIDs...", file=sys.stderr)
    meta = batch_efetch(all_pmids)

    id_to_item = {item["id"]: item for item in queries}
    output = []
    for qid in sorted(id_to_pmids):
        pmids  = id_to_pmids[qid]
        output.append({
            "id":          qid,
            "description": id_to_item[qid].get("description", ""),
            "query":       id_to_item[qid]["query"],
            "results":     [meta[p] for p in pmids if p in meta],
        })

    print(f"Done in {time.time() - t0:.1f}s", file=sys.stderr)
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
