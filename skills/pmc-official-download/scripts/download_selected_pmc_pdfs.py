#!/usr/bin/env python3
"""
Download specified PMC official PDFs.

This script only accesses the official PDF address on pmc.ncbi.nlm.nih.gov,
for saving user-specified publicly accessible articles.

Usage:
    python scripts/download_selected_pmc_pdfs.py
"""

from __future__ import annotations

import datetime as _dt
import argparse
import json
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


# =========================
# Configuration
# =========================
OUTPUT_DIR = Path("pmc-downloads") / "nsclc-immunotherapy"
TIMEOUT_SECONDS = 90
OVERWRITE = True

ARTICLES = [
    {
        "year": 2026,
        "title": "Optimal sequencing of brain radiotherapy and immunotherapy for patients with non-small cell lung cancer and driver gene-negative, asymptomatic brain metastases",
        "pmcid": "PMC13011518",
        "pdf_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC13011518/",
        "article_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC13011518/",
    },
    {
        "year": 2024,
        "title": "Immune-related adverse events correlate with the clinical efficacy in advanced Non-Small-Cell Lung Cancer patients treated with PD-1 inhibitors combination therapy",
        "pmcid": "PMC11656652",
        "pdf_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11656652/pdf/12885_2024_Article_13220.pdf",
        "article_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11656652/",
    },
    {
        "year": 2025,
        "title": "Pre-immunotherapy alters stereotactic ablative radiotherapy-induced systemic T cell responses in early-stage NSCLC",
        "pmcid": "PMC11787101",
        "pdf_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11787101/pdf/262_2024_Article_3935.pdf",
        "article_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11787101/",
    },
]


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:120]


def fetch_article_metadata(pmcid: str) -> dict:
    """
    Read title and year from PMC E-utilities for auto-naming in command-line mode.
    """
    url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?"
        f"db=pmc&id={pmcid}&retmode=xml"
    )
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; PMC-Official-Download-Skill/1.0)"},
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        xml_text = response.read().decode("utf-8", "ignore")

    root = ET.fromstring(xml_text)
    article = root.find(".//article")
    if article is None:
        raise RuntimeError(f"Cannot retrieve article metadata from PMC: {pmcid}")

    title = article.findtext(".//article-title") or pmcid
    year = article.findtext(".//pub-date/year")
    if not year:
        year = article.findtext(".//history/date[@date-type='accepted']/year") or "0000"
    return {
        "title": title,
        "year": int(year),
        "pmcid": pmcid,
        "article_url": f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/",
    }


def resolve_official_pdf_url(pmcid: str) -> tuple[str, str]:
    """
    Resolve official PDF FTP address via PMC OA Web Service.

    Returns (pdf_url, record_xml_url).
    """
    oa_url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id={pmcid}"
    request = urllib.request.Request(
        oa_url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; PMC-Official-Download-Skill/1.0)"},
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        xml_text = response.read().decode("utf-8", "ignore")

    root = ET.fromstring(xml_text)
    pdf_link = root.find(".//link[@format='pdf']")
    if pdf_link is None or not pdf_link.get("href"):
        raise RuntimeError(f"{pmcid} did not return an official PDF link, may not be a publicly accessible PMC article.")
    return pdf_link.get("href"), oa_url


def normalize_download_url(url: str) -> str:
    """
    Convert ftp:// links returned by OA Web Service to more stable https:// links.
    """
    if url.startswith("ftp://ftp.ncbi.nlm.nih.gov/"):
        return "https://ftp.ncbi.nlm.nih.gov/" + url.removeprefix("ftp://ftp.ncbi.nlm.nih.gov/")
    return url


def download_pdf(article: dict, output_dir: Path, overwrite: bool) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_name = f"{article['year']}_{article['pmcid']}_{slugify(article['title'])}.pdf"
    pdf_path = output_dir / safe_name
    manifest_path = output_dir / f"{article['pmcid']}_manifest.json"

    if pdf_path.exists() and not overwrite:
        raise FileExistsError(f"File already exists: {pdf_path}")

    pdf_url, oa_url = resolve_official_pdf_url(article["pmcid"])
    download_url = normalize_download_url(pdf_url)
    request = urllib.request.Request(
        download_url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; PMC-Official-Download-Skill/1.0)",
            "Accept": "application/pdf,*/*",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            payload = response.read()
            status = getattr(response, "status", 200)
            content_type = response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Download failed: {article['pmcid']}, HTTP {exc.code}") from exc

    if not payload:
        raise RuntimeError(f"Download failed: {article['pmcid']} returned no content")
    if not payload.startswith(b"%PDF"):
        raise RuntimeError(f"Download failed: {article['pmcid']} returned content is not a PDF file")

    pdf_path.write_bytes(payload)

    manifest = {
        "title": article["title"],
        "year": article["year"],
        "pmcid": article["pmcid"],
        "article_url": article["article_url"],
        "pdf_url": download_url,
        "oa_service_url": oa_url,
        "source_service": "PMC official PDF",
        "downloaded_at_utc": _dt.datetime.now(tz=_dt.timezone.utc).isoformat(),
        "http_status": status,
        "content_type": content_type,
        "output_file": str(pdf_path),
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download publicly accessible PMC articles using the official PMC OA Web Service + PDF resources."
    )
    parser.add_argument(
        "--pmcid",
        action="append",
        help="PMCID to download, can be specified multiple times, e.g. --pmcid PMC13011518 --pmcid PMC11656652",
    )
    parser.add_argument(
        "--output-dir",
        default=str(OUTPUT_DIR),
        help=f"Output directory, default: {OUTPUT_DIR}",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite if file already exists",
    )
    parser.add_argument(
        "--use-default-list",
        action="store_true",
        help="Ignore command-line PMCIDs and use built-in example list",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    overwrite = args.overwrite or OVERWRITE

    if args.use_default_list or not args.pmcid:
        articles = ARTICLES
    else:
        articles = [fetch_article_metadata(pmcid) for pmcid in args.pmcid]

    results = []
    failures = 0

    for article in articles:
        try:
            manifest = download_pdf(article, output_dir=output_dir, overwrite=overwrite)
            results.append(manifest)
            print(f"Downloaded: {article['pmcid']} -> {manifest['output_file']}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"Failed: {article['pmcid']} -> {exc}", file=sys.stderr)

    summary_path = output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if failures:
        print(f"Done, but {failures} article(s) failed.", file=sys.stderr)
        return 1
        print(f"All done, output directory: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
