#!/usr/bin/env python3
"""
PDF Text Extraction Tool

Usage:
  python3 extract_pdf.py <pdf_path> [output_path]

Extracts text from all pages of a PDF into a specified text file.
If output_path is not specified, generates a .txt file with the same name in the PDF's directory.

Dependency: PyMuPDF (fitz)
"""

import sys
import os
from pathlib import Path


def extract_text_from_pdf(pdf_path: str, output_path: str = None) -> str:
    """
    Extract all text from a PDF file and save as a txt file.

    Args:
        pdf_path: Path to the PDF file
        output_path: Output txt file path. Auto-generated if None.

    Returns:
        Path of the output file
    """
    pdf_path = os.path.abspath(pdf_path)

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file does not exist: {pdf_path}")

    # Auto-generate output path
    if output_path is None:
        pdf_stem = Path(pdf_path).stem
        pdf_dir = os.path.dirname(pdf_path)
        output_path = os.path.join(pdf_dir, f"{pdf_stem}_extracted.txt")

    try:
        import fitz
    except ImportError:
        raise ImportError(
            "PyMuPDF library is required. Please install first: pip install PyMuPDF"
        )

    doc = fitz.open(pdf_path)
    total_pages = doc.page_count

    all_text = []
    all_text.append(f"File: {os.path.basename(pdf_path)}")
    all_text.append(f"Total pages: {total_pages}")
    all_text.append("=" * 60)

    for i in range(total_pages):
        page = doc[i]
        page_text = page.get_text()

        all_text.append(f"\n{'=' * 60}")
        all_text.append(f"Page {i+1} (of {total_pages})")
        all_text.append(f"{'=' * 60}\n")

        if page_text.strip():
            all_text.append(page_text)
        else:
            all_text.append("[No extractable text on this page — may be an image-only page]")

    doc.close()

    result = "\n".join(all_text)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)

    return output_path


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 extract_pdf.py <pdf_path> [output_path]")
        print("Example: python3 extract_pdf.py paper.pdf")
        print("         python3 extract_pdf.py paper.pdf output/paper_text.txt")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        out = extract_text_from_pdf(pdf_path, output_path)
        print(f"Text extracted to: {out}")
    except Exception as e:
        print(f"Extraction failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
