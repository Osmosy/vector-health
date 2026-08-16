import argparse
import os
import re
import sys

def count_words(text):
    # Process text for typical Chinese/English mixed content
    # Remove markdown tags typically
    text_clean = re.sub(r'[#*`_\[\]()]+', ' ', text)
    # Count chinese characters separately
    hanzi = re.findall(r'[\u4e00-\u9fff]', text_clean)
    # Count english words
    eng_words = re.findall(r'\b[a-zA-Z]+\b', text_clean)
    return len(hanzi) + len(eng_words)

def count_references(text):
    # Matches [PMID:xxx] or [PMID: xxx]
    pmid_pattern = re.compile(r'\[PMID:\s*(\d+)\]', re.IGNORECASE)
    all_matched_pmids = pmid_pattern.findall(text)
    unique_pmids = set(all_matched_pmids)
    return len(unique_pmids)

def check_reference_density(text):
    # Split text into sentences using common punctuation marks.
    sentences = re.split(r'[。！？.!?]+', text)
    violating_sentences = []
    pmid_pattern = re.compile(r'\[PMID:\s*\d+\]', re.IGNORECASE)
    
    for sentence in sentences:
        refs_in_sentence = pmid_pattern.findall(sentence)
        if len(refs_in_sentence) > 2:
            violating_sentences.append((sentence.strip()[:50] + "...", len(refs_in_sentence)))
    return violating_sentences

def main():
    parser = argparse.ArgumentParser(description="Check word count and reference count in a markdown file.")
    parser.add_argument("file", help="Path to the markdown file to check (e.g., section_1.md)")
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"Error: File '{args.file}' not found.", file=sys.stderr)
        sys.exit(1)

    try:
        with open(args.file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {args.file}: {e}", file=sys.stderr)
        sys.exit(1)

    word_count = count_words(content)
    ref_count = count_references(content)
    violating_sentences = check_reference_density(content)

    print(f"--- Document Check: {args.file} ---")
    print(f"Estimated Word/Char Count: {word_count}")
    print(f"Unique References (PMIDs): {ref_count}")
    
    if violating_sentences:
        print("\n[Warning] The following sentences have more than 2 citations:")
        for sentence, count in violating_sentences:
            print(f"  - ({count} refs) {sentence}")

    print(“\n” + “=”*40)
    print(“[State Machine]”)
    print(f”Current state: Section `{os.path.basename(args.file)}` quality check complete. Word count: {word_count}, References: {ref_count}.”)
    print(“Next steps: “)

    if ref_count < 10:
        print(“- References too few (< 10), recommend running `pubmed_search.py` with `--post-write` to supplement retrieval for this section.”)
    elif word_count < 7000:
        print(f”- Note: Current section word count is insufficient ({word_count} < 7000). If this review needs to reach the target length, consider expanding content and adding more detail paragraphs.”)
        print(“- When supplementing content, continue searching for supporting references as needed.”)
    elif violating_sentences:
        print(f”- Note: Found {len(violating_sentences)} sentences citing more than 2 references!”)
        print(“- Required: Please modify the above over-cited sentences. Distribute dense citations across different clauses, or expand the specific analysis of citations, ensuring no more than 2 citations per sentence.”)
        print(“- After modification, please run `check_section.py` again to verify.”)
    else:
        print(“- Reference count, distribution density, and word count all meet requirements.”)
        print(“- Required: Please PAUSE now and report to the user (in the user's language) the completion status, word count, and reference count of this section.”)
        print(“- Ask the user: 'Shall I continue writing the next section?' Wait for user confirmation before proceeding.”)
        print(“- If all sections are complete, proceed to Phase 5 and run `merge_review.py`.”)
        
    print("="*40 + "\n")

if __name__ == "__main__":
    main()
