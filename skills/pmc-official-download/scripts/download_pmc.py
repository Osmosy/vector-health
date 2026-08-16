#!/usr/bin/env python3
"""
PMC official download unified entry point.

This script is the preferred entry:

- Pass `--pmcid` to download official PMC PDFs
- Pass `--identifier` to download PMC BioC

Lets the caller only remember this one script, instead of separate PDF and BioC entry points.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from download_pmc_bioc import download_one as download_bioc_one
from download_selected_pmc_pdfs import download_pdf, fetch_article_metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PMC official download unified entry point")
    parser.add_argument(
        "--pmcid",
        action="append",
        help="PMCID for official PDF download, can be specified multiple times",
    )
    parser.add_argument(
        "--identifier",
        action="append",
        help="PMID or PMCID for BioC download, can be specified multiple times",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory. Defaults to automatic selection by mode: PDF uses pmc-downloads/pdf, BioC uses pmc-downloads/bioc",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite if file already exists",
    )
    parser.add_argument(
        "--bioc-format",
        choices=("xml", "json"),
        default="xml",
        help="BioC output format, default xml",
    )
    parser.add_argument(
        "--bioc-encoding",
        choices=("unicode", "ascii"),
        default="unicode",
        help="BioC output character encoding, default unicode",
    )
    parser.add_argument(
        "--use-default-pdf-list",
        action="store_true",
        help="Ignore --pmcid and use built-in PDF example list",
    )
    parser.add_argument(
        "--use-default-bioc-list",
        action="store_true",
        help="Ignore --identifier and use built-in BioC example list",
    )
    return parser.parse_args()


def run_pdf(pmcids: list[str], output_dir: Path, overwrite: bool) -> int:
    failures = 0
    for pmcid in pmcids:
        try:
            article = fetch_article_metadata(pmcid)
            manifest = download_pdf(article, output_dir=output_dir, overwrite=overwrite)
            print(f"Downloaded: {pmcid} -> {manifest['output_file']}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"Failed: {pmcid} -> {exc}", file=sys.stderr)
    return failures


def run_bioc(
    identifiers: list[str],
    output_dir: Path,
    overwrite: bool,
    bioc_format: str,
    bioc_encoding: str,
) -> int:
    failures = 0
    for identifier in identifiers:
        try:
            saved = download_bioc_one(
                identifier,
                output_dir=output_dir,
                format_name=bioc_format,
                encoding=bioc_encoding,
                overwrite=overwrite,
            )
            print(f"Downloaded: {identifier} -> {saved}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"Failed: {identifier} -> {exc}", file=sys.stderr)
    return failures


def main() -> int:
    args = parse_args()

    pdf_mode = bool(args.pmcid) or args.use_default_pdf_list
    bioc_mode = bool(args.identifier) or args.use_default_bioc_list

    if pdf_mode and bioc_mode:
        print("Please choose only one mode: either --pmcid or --identifier.", file=sys.stderr)
        return 1

    if not pdf_mode and not bioc_mode:
        print("Please provide at least --pmcid or --identifier.", file=sys.stderr)
        return 1

    overwrite = args.overwrite
    if pdf_mode:
        pmcids = args.pmcid or []
        if not pmcids:
            from download_selected_pmc_pdfs import ARTICLES as DEFAULT_PDF_ARTICLES

            pmcids = [article["pmcid"] for article in DEFAULT_PDF_ARTICLES]
        output_dir = Path(args.output_dir or "pmc-downloads/pdf")
        output_dir.mkdir(parents=True, exist_ok=True)
        failures = run_pdf(pmcids, output_dir=output_dir, overwrite=overwrite)
        if failures:
            print(f"Done, but {failures} article(s) failed.", file=sys.stderr)
            return 1
        print(f"All done, output directory: {output_dir}")
        return 0

    identifiers = args.identifier or []
    if not identifiers:
        from download_pmc_bioc import IDENTIFIERS as DEFAULT_IDENTIFIERS

        identifiers = [item for item in DEFAULT_IDENTIFIERS if item]

    output_dir = Path(args.output_dir or "pmc-downloads/bioc")
    output_dir.mkdir(parents=True, exist_ok=True)
    failures = run_bioc(
        identifiers,
        output_dir=output_dir,
        overwrite=overwrite,
        bioc_format=args.bioc_format,
        bioc_encoding=args.bioc_encoding,
    )
    if failures:
        print(f"Done, but {failures} article(s) failed.", file=sys.stderr)
        return 1
    print(f"All done, output directory: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
