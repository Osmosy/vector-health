import argparse
import json
import sys
import os

def read_references(section_filter=None, file_path="references.json"):
    """
    Reads the references.json file and prints references matching the section filter.
    """
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found. Please ensure retrieval step is done.", file=sys.stderr)
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            references = json.load(f)
    except json.JSONDecodeError:
        print(f"Error: Failed to decode {file_path}.", file=sys.stderr)
        return

    filtered_refs = []
    
    print(f"--- References for Section: '{section_filter if section_filter else 'ALL'}' ---")
    
    count = 0
    for ref in references:
        # If no filter, show all. If filter, check if section field contains the filter string (case-insensitive)
        current_section = ref.get("section", "").lower()
        if section_filter is None or section_filter.lower() in current_section:
            print(f"\n[Ref {count+1}]")
            print(f"Title: {ref.get('title', 'N/A')}")
            print(f"Year: {ref.get('year', 'N/A')}")
            print(f"PMID: {ref.get('pmid', 'N/A')}") # Assuming PMID might be added in future, or mapped from search
            # Note: The original pubmed_search.py does not strictly output 'pmid' in the JSON body, usually it's used to fetch. 
            # But the agent is instructed to put PMID in json.
            print(f"Abstract: {ref.get('abstract', 'N/A')}")
            filtered_refs.append(ref)
            count += 1
            
    if count == 0:
        print("No references found for this section.")

def main():
    parser = argparse.ArgumentParser(description="Read references from JSON filtered by section.")
    parser.add_argument("section", nargs='?', help="Section name to filter by (fuzzy match)")
    parser.add_argument("--file", default="references.json", help="Path to references.json")
    
    args = parser.parse_args()
    
    # Check if file exists in current or parent directory (standard agent context awareness)
    # The agent might run this from the root or the skill dir
    if os.path.exists(args.file):
        target_file = args.file
    elif os.path.exists(os.path.join("MedicalReviewSkill", args.file)):
        target_file = os.path.join("MedicalReviewSkill", args.file)
    else:
        # Fallback to current, will likely error if missing
        target_file = args.file
        
    read_references(args.section, target_file)

    print("\n" + "="*40)
    print("[State Machine]")
    print(f"Current state: Phase 3 (Section Writing) - References for section `{args.section if args.section else 'ALL'}` have been read.")
    print("Next steps: ")
    print("- Begin writing the current `[section_name].md` file based on the above references, annotating each point with `[PMID: xxx]`.")
    print("- After writing, you may read references for the next section, or proceed to Phase 4 to write conclusion.md and abstract.md.")
    print("="*40 + "\n")

if __name__ == "__main__":
    main()
