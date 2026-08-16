"""
Convert a Markdown file to .docx using pandoc (or pypandoc as fallback).
Auto-installs pandoc via winget if not found (Windows only).
Falls back to pypandoc if winget install fails or no pandoc binary found.

Usage: python convert_to_docx.py input.md [--output out.docx] [--reference-doc template.docx]
"""

import sys
import shutil
import subprocess
import argparse
from pathlib import Path


def find_pandoc() -> str | None:
    return shutil.which("pandoc")


def install_pandoc_winget() -> bool:
    print("pandoc not found. Trying to install via winget...", file=sys.stderr)
    try:
        result = subprocess.run(
            ["winget", "install", "--id", "JohnMacFarlane.Pandoc", "-e", "--silent",
             "--accept-package-agreements", "--accept-source-agreements"],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            print("pandoc installed successfully.", file=sys.stderr)
            return True
        else:
            print(f"winget failed (exit {result.returncode}): {result.stderr.strip()}", file=sys.stderr)
            return False
    except FileNotFoundError:
        print("winget not available on this system.", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Install error: {e}", file=sys.stderr)
        return False


def convert_via_pandoc(input_path: Path, output_path: Path, reference_doc: Path | None, pandoc: str) -> bool:
    cmd = [pandoc, str(input_path), "-o", str(output_path), "--wrap=none"]
    if reference_doc and reference_doc.exists():
        cmd += [f"--reference-doc={reference_doc}"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            return True
        print(f"pandoc error: {result.stderr.strip()}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Conversion error: {e}", file=sys.stderr)
        return False


def convert_via_pypandoc(input_path: Path, output_path: Path, reference_doc: Path | None) -> bool:
    """Fallback: use pypandoc (pip install pypandoc_binary) to convert."""
    try:
        import pypandoc
        extra_args = ["--wrap=none"]
        if reference_doc and reference_doc.exists():
            extra_args += [f"--reference-doc={reference_doc}"]
        pypandoc.convert_file(str(input_path), "docx", outputfile=str(output_path), extra_args=extra_args)
        return True
    except ImportError:
        print("pypandoc not installed. Try: pip install pypandoc_binary", file=sys.stderr)
        return False
    except Exception as e:
        print(f"pypandoc error: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Convert Markdown to docx")
    parser.add_argument("input", help="Input .md file")
    parser.add_argument("--output", help="Output .docx path (default: same name as input)")
    parser.add_argument("--reference-doc", dest="reference_doc", help="Pandoc reference .docx template")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output) if args.output else input_path.with_suffix(".docx")
    reference_doc = Path(args.reference_doc) if args.reference_doc else None

    pandoc = find_pandoc()
    if pandoc:
        if convert_via_pandoc(input_path, output_path, reference_doc, pandoc):
            print(str(output_path))
            return
    else:
        # Try winget install first
        if install_pandoc_winget():
            import os
            os.environ["PATH"] += r";C:\Users\{}\AppData\Local\Microsoft\WinGet\Packages\JohnMacFarlane.Pandoc_Microsoft.Winget.Source_8wekyb3d8bbwe".format(
                os.environ.get("USERNAME", "")
            )
            pandoc = find_pandoc()
            if pandoc and convert_via_pandoc(input_path, output_path, reference_doc, pandoc):
                print(str(output_path))
                return

        # Fallback: try pypandoc
        print("Trying pypandoc as fallback...", file=sys.stderr)
        if convert_via_pypandoc(input_path, output_path, reference_doc):
            print(str(output_path))
            return

        print("Conversion failed. Install pandoc manually: https://pandoc.org/installing.html", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
