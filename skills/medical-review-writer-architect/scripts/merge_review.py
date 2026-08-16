import os
import glob
import re
import argparse
import sys

def natural_sort_key(s):
    """
    Sort strings containing numbers naturally, e.g. section_2.md comes before section_10.md
    """
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(r'(\d+)', s)]

def merge_files(output_file, input_patterns):
    """
    Merges files matching the input patterns into a single Markdown file.
    """
    files_to_merge = []
    
    # Expand patterns preserving order
    for pattern in input_patterns:
        # Check if pattern contains wildcards
        if any(char in pattern for char in ['*', '?', '[']):
            matched = glob.glob(pattern)
            # Sort matched files naturally
            matched.sort(key=natural_sort_key)
            if not matched:
                print(f"Warning: No files found for pattern '{pattern}'", file=sys.stderr)
            files_to_merge.extend(matched)
        else:
            # Exact filename
            if os.path.exists(pattern):
                files_to_merge.append(pattern)
            else:
                 print(f"Error: File '{pattern}' not found.", file=sys.stderr)
                 sys.exit(1)

    # Remove duplicates while preserving order? 
    # Usually patterns might overlap? Let's assume user knows what they are doing or just unique them.
    # Uniquify:
    seen = set()
    unique_files = []
    for f in files_to_merge:
        if f not in seen:
            if os.path.basename(f).lower() == 'outline.md':
                print(f"Skipping {f} (outline file)", file=sys.stderr)
                continue
            unique_files.append(f)
            seen.add(f)
            
    if not unique_files:
        print("No files to merge. Please check your patterns.", file=sys.stderr)
        return

    print(f"Merging {len(unique_files)} files: {', '.join(unique_files)}", file=sys.stderr)

    content_parts = []
    for filepath in unique_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content_parts.append(f.read().strip())
        except Exception as e:
            print(f"Error reading {filepath}: {e}", file=sys.stderr)

    # Join with double newlines
    full_content = "\n\n".join(content_parts)
    
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(full_content)
        print(f"Successfully merged files into '{output_file}'")
    except Exception as e:
        print(f"Error writing to {output_file}: {e}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description="Merge markdown files into a single document.")
    parser.add_argument("inputs", nargs="*", 
                        help="Input files or patterns (e.g. 'abstract.md' 'section_*.md'). If empty, uses default preset.")
    parser.add_argument("-o", "--output", default="Review_Final.md", 
                        help="Output filename (default: Review_Final.md)")
    
    args = parser.parse_args()
    
    inputs = args.inputs
    if not inputs:
        # Default behavior if no args provided: Smart Default
        inputs = ["abstract.md", "introduction.md", "section_*.md", "conclusion.md"]
        print("No input files specified. Using default pattern: " + " ".join(inputs), file=sys.stderr)
    
    merge_files(args.output, inputs)

    print("\n" + "="*40)
    print("[State Machine]")
    print("Current state: Phase 5 (Abstract & Finalization) - Section files merged into final draft.")
    print("Next steps: ")
    print("- Review the merged document layout and content.")
    print("- If correct, proceed to Phase 6, run `format_citations.py` to format `[PMID: xxx]` into APA-style citations.")
    print("="*40 + "\n")

if __name__ == "__main__":
    main()
