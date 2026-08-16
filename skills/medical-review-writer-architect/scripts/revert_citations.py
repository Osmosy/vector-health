import re
import sys
import argparse
import os

def revert_citations(file_path: str, inplace: bool = False, output_path: str = None):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.", file=sys.stderr)
        return

    # 1. Replace [[number]](https://pubmed.ncbi.nlm.nih.gov/pmid/) with [PMID: pmid]
    pattern = re.compile(r'\[\[\d+\]\]\(https://pubmed\.ncbi\.nlm\.nih\.gov/(\d+)/\)')
    new_content = pattern.sub(r'[PMID: \1]', content)

    # 2. Remove the ### References section
    if '### References' in new_content:
        new_content = new_content.split('### References')[0].rstrip() + '\n'

    if inplace:
        output_file = file_path
    elif output_path:
        output_file = output_path
    else:
        # Default behavior: print to standard output
        print(new_content)
        return

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Successfully reverted citations and saved to {output_file}")
    
    unique_pmids = set(re.findall(r'\[PMID:\s*\d+\]', new_content, re.IGNORECASE))
    return len(unique_pmids)

def main():
    parser = argparse.ArgumentParser(description="Revert formatted citations back to [PMID: xxx] format.")
    parser.add_argument("file", help="Path to formatted Markdown file")
    parser.add_argument("-i", "--inplace", action="store_true", help="Modify file in-place")
    parser.add_argument("-o", "--output", help="Path to output file")
    
    args = parser.parse_args()
    pmid_count = revert_citations(args.file, args.inplace, args.output)

    if pmid_count is None:
        return

    print("\n" + "="*40)
    print("[State Machine]")
    print(f"Current state: Content modification phase - Citation revert complete, extracted {pmid_count} unique references.")
    print("Next steps: ")
    if pmid_count < 30:
        print("- Note: Current review total references are low (fewer than 30). Recommend supplementing retrieval for weak sections using `--post-write` or directly running `python scripts/pubmed_search.py`.")
    else:
        print("- Current review reference count meets requirements. If during modification/expansion you find specific arguments lack support, you can still use `python scripts/pubmed_search.py` for targeted supplementary retrieval.")
    print("- Please make content modifications or additions based on this reverted version.")
    print("- Remember: When adding new arguments, continue using `[PMID: xxx]` format.")
    print("- After modifications are confirmed, re-run `python scripts/format_citations.py` to format into the final publication version.")
    print("="*40 + "\n")

if __name__ == "__main__":
    main()
