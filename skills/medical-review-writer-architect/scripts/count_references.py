import json
import argparse
import os

def count_references(filename="references.json"):
    if not os.path.exists(filename):
        print(f"Error: {filename} not found.")
        return

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print(f"Error: Failed to decode {filename}.")
        return

    unique_pmids = set()
    section_counts = {}

    for entry in data:
        pmid = entry.get('pmid')
        section = entry.get('section', 'Unknown')
        
        if pmid:
            unique_pmids.add(pmid)
        
        section_counts[section] = section_counts.get(section, 0) + 1

    total_unique = len(unique_pmids)
    
    print(f"\n--- Reference Statistics ---")
    print(f"Total Unique PMIDs: {total_unique}")
    print(f"Total Entries: {len(data)}")
    print(f"\n--- By Section ---")
    for section, count in section_counts.items():
        print(f"{section}: {count}")
    
    if total_unique < 200:
        print(f"\n⚠️  Warning: Unique references ({total_unique}) are fewer than the recommended target of 200.")
    else:
        print(f"\n✅ Target reached: >200 unique references available.")

    print("\n" + "="*40)
    print("[State Machine]")
    print("Current state: Phase 2 (Data Retrieval) - Reference count check complete.")
    print("Next steps: ")
    print("- If PMIDs >= 150, proceed to Phase 3, run `read_references.py` to read references and begin writing sections.")
    print("- If references are insufficient, use `pubmed_search.py` to supplement retrieval.")
    print("="*40 + "\n")

def main():
    parser = argparse.ArgumentParser(description="Count unique references in references.json")
    parser.add_argument("--file", default="references.json", help="Path to references.json file")
    args = parser.parse_args()
    
    count_references(args.file)

if __name__ == "__main__":
    main()
