#!/usr/bin/env python3
"""
Remove numbering prefix from all headings in a DOCX.
Matches '1. Title' '1.1 Subtitle' '2. ' etc.
Modifies the original run text directly, preserving paragraph structure.

Usage:
    python remove_heading_numbers.py <input.docx> [output.docx]
    If no output file is specified, overwrites the input file.
"""
import re
import sys
from docx import Document


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    src = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else src

    doc = Document(src)
    count = 0
    for para in doc.paragraphs:
        if not para.style.name.startswith("Heading"):
            continue
        old = para.text
        new = re.sub(r"^[\d\.]+\s+", "", old)
        if new == old or not para.runs:
            continue
        first = para.runs[0]
        cut = len(old) - len(new)
        if len(first.text) >= cut and first.text[:cut] == old[:cut]:
            first.text = first.text[cut:]
        else:
            first.text = new
        count += 1

    doc.save(output)
    print(f"Removed {count} heading number(s): {output}")


if __name__ == "__main__":
    main()
