#!/usr/bin/env python3
"""
Download single PMC full text using the official PMC BioC API.

Only depends on Python standard library. Fill the PMID/PMCID to download
in IDENTIFIERS, then run:

    python scripts/download_pmc_bioc.py

Output will be written to OUTPUT_DIR/<identifier>/ with a manifest.json.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


# =========================
# Configuration
# =========================
IDENTIFIERS = [
    # "PMC1234567",
    # "12345678",
]
FORMAT = "xml"  # Options: xml / json
ENCODING = "unicode"  # Options: unicode / ascii
OUTPUT_DIR = Path("pmc-downloads")
TIMEOUT_SECONDS = 60
OVERWRITE = False


def build_url(identifier: str, format_name: str = FORMAT, encoding: str = ENCODING) -> str:
    return (
        "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/"
        f"BioC_{format_name}/{identifier}/{encoding}"
    )


def download_one(
    identifier: str,
    output_dir: Path = OUTPUT_DIR,
    format_name: str = FORMAT,
    encoding: str = ENCODING,
    overwrite: bool = OVERWRITE,
) -> Path:
    url = build_url(identifier, format_name=format_name, encoding=encoding)
    target_dir = output_dir / identifier
    target_dir.mkdir(parents=True, exist_ok=True)

    suffix = ".xml" if format_name.lower() == "xml" else ".json"
    data_path = target_dir / f"BioC_{format_name}_{encoding}{suffix}"
    manifest_path = target_dir / "manifest.json"

    if data_path.exists() and not overwrite:
        raise FileExistsError(f"File already exists and OVERWRITE=False: {data_path}")

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; PMC-Official-Download-Skill/1.0)"
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            payload = response.read()
            status = getattr(response, "status", 200)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"Download failed: {identifier} may not be in the PMC publicly accessible collection, or the service is temporarily unavailable."
        ) from exc

    if not payload:
        raise RuntimeError(
            f"Download failed: {identifier} returned no content, may not be in the PMC Open Access Subset or Author Manuscript Collection."
        )

    data_path.write_bytes(payload)

    manifest = {
        "identifier": identifier,
        "source_service": "PMC BioC API",
        "source_url": url,
        "format": format_name,
        "encoding": encoding,
        "downloaded_at_utc": _dt.datetime.now(tz=_dt.timezone.utc).isoformat(),
        "http_status": status,
        "output_file": str(data_path),
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return data_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download single or multiple publicly accessible articles using the official PMC BioC API."
    )
    parser.add_argument(
        "--identifier",
        action="append",
        dest="identifiers",
        help="PMID or PMCID, can be specified multiple times, e.g. --identifier PMC11787101 --identifier 41875094",
    )
    parser.add_argument(
        "--format",
        choices=("xml", "json"),
        default=FORMAT,
        help="Output format, default xml",
    )
    parser.add_argument(
        "--encoding",
        choices=("unicode", "ascii"),
        default=ENCODING,
        help="Character encoding mode, default unicode",
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
        help="Ignore command-line arguments and use the IDENTIFIERS list at the top of the script",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    identifiers = IDENTIFIERS if args.use_default_list or not args.identifiers else args.identifiers

    if not identifiers:
        print("Please provide --identifier, or fill in PMID/PMCID in IDENTIFIERS at the top of the script.", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    failures = 0

    for identifier in identifiers:
        try:
            saved = download_one(
                identifier,
                output_dir=output_dir,
                format_name=args.format,
                encoding=args.encoding,
                overwrite=args.overwrite or OVERWRITE,
            )
            print(f"Downloaded: {identifier} -> {saved}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"Failed: {identifier} -> {exc}", file=sys.stderr)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
