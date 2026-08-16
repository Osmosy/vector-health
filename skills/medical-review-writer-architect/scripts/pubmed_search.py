import argparse
import sys
import json
import time
import os
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import re

# Base URLs for NCBI Entrez E-utilities
ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

def search_pubmed(query, max_results=10):
    """
    Search PubMed for a given query and return a list of IDs.
    """
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json",
        "sort": "date" # Get most recent
    }
    
    query_string = urllib.parse.urlencode(params)
    url = f"{ESEARCH_URL}?{query_string}"
    
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            id_list = data.get("esearchresult", {}).get("idlist", [])
            return id_list
    except Exception as e:
        print(f"Error searching PubMed: {e}", file=sys.stderr)
        return []

def fetch_details(id_list):
    """
    Fetch details for a list of PubMed IDs.
    """
    if not id_list:
        return []
    
    # User requested to allow batch retrieval (PMIDs given together)
    ids = ",".join(id_list)
    params = {
        "db": "pubmed",
        "id": ids,
        "retmode": "xml"
    }
    
    query_string = urllib.parse.urlencode(params)
    url = f"{EFETCH_URL}?{query_string}"
    
    papers = []
    try:
        # Rate limit: Sleep slightly to be safe (though user said 1s rate limit, 
        # a single batch request satisfies this easily).
        time.sleep(1.0)
        
        with urllib.request.urlopen(url) as response:
            xml_data = response.read().decode()
            root = ET.fromstring(xml_data)
            
            for article in root.findall(".//PubmedArticle"):
                paper = {}
                medline_citation = article.find("MedlineCitation")
                article_data = medline_citation.find("Article")
                
                # PMCID/PMID for reference
                # Safety check for PMID existence
                pmid_node = medline_citation.find("PMID")
                pmid = pmid_node.text if pmid_node is not None else "Unknown"
                paper["pmid"] = pmid

                # Title
                title_node = article_data.find("ArticleTitle")
                paper["title"] = title_node.text if title_node is not None else "No title available"
                
                # Abstract
                abstract_text = []
                abstract = article_data.find("Abstract")
                if abstract is not None:
                    for abstract_text_elem in abstract.findall("AbstractText"):
                        if abstract_text_elem.text:
                            label = abstract_text_elem.get("Label")
                            if label:
                                abstract_text.append(f"{label}: {abstract_text_elem.text}")
                            else:
                                abstract_text.append(abstract_text_elem.text)
                
                # Auto-skip articles with empty abstracts
    if not abstract_text:
                    continue
                    
                paper["abstract"] = " ".join(abstract_text)
                
                # Year
                journal = article_data.find("Journal")
                
                pub_date = journal.find("JournalIssue").find("PubDate")
                year = pub_date.find("Year")
                if year is not None:
                    paper["year"] = year.text
                else:
                    medline_date = pub_date.find("MedlineDate")
                    if medline_date is not None:
                         # Attempt to extract year
                         paper["year"] = medline_date.text.split(" ")[0] 
                    else:
                        paper["year"] = "Unknown"

                papers.append(paper)
                
    except Exception as e:
         print(f"Error fetching details: {e}", file=sys.stderr)
         
    return papers

def save_to_json(papers, section_name, query, filename="references.json"):
    """
    Appends papers to the JSON file with the section tag and search query.
    """
    # 1. Add section tag and query
    for paper in papers:
        paper["section"] = section_name
        paper["search_query"] = query
        
    # 2. Load existing
    existing_data = []
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: {filename} was corrupted or empty. Overwriting.", file=sys.stderr)
            existing_data = []
            
    # 3. Append (avoiding absolute duplicates if feasible, but simple append is safer for now)
    # We will just append. The read script can filter. 
    # Actually, let's avoid adding the EXACT same PMID for the SAME section.
    
    existing_ids = set((p.get("pmid"), p.get("section")) for p in existing_data)
    
    added_count = 0
    for paper in papers:
        key = (paper.get("pmid"), section_name)
        if key not in existing_ids:
            existing_data.append(paper)
            added_count += 1
            
    # 4. Save
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, indent=2, ensure_ascii=False)
        
    return added_count

def main():
    parser = argparse.ArgumentParser(description="Search PubMed and save to references.json.")
    parser.add_argument("query", help="Search query string")
    parser.add_argument("--section", required=True, help="Section name (e.g., 'Introduction')")
    parser.add_argument("--max", type=int, default=20, help="Max results to return")
    parser.add_argument("--file", default="references.json", help="Output JSON file")
    parser.add_argument("--post-write", action="store_true", help="Flag to indicate this is a supplementary search after writing.")
    
    args = parser.parse_args()

    # Validate section name format
    # Allowed: 'introduction' OR 'section_N' (where N is a number)
    if not re.match(r'^(introduction|section_\d+)$', args.section):
        print(f"Error: Invalid section name '{args.section}'.", file=sys.stderr)
        print("Allowed formats: 'introduction' or 'section_N' (e.g., section_1, section_2).", file=sys.stderr)
        sys.exit(1)
    
    print(f"Searching for: {args.query}...", file=sys.stderr)
    id_list = search_pubmed(args.query, args.max)
    
    if not id_list:
        print("No results found.", file=sys.stderr)
        return

    # Rate limit check
    time.sleep(0.5)
    
    papers = fetch_details(id_list)
    
    # Save to file
    added = save_to_json(papers, args.section, args.query, args.file)
    
    print(f"Successfully fetched {len(papers)} papers.")
    print(f"Added {added} new unique papers to {args.file} under section '{args.section}'.")
    
    # Optionally print a brief summary for the agent to see immediately
    for p in papers[:3]:
        print(f"- {p.get('title')} ({p.get('year')}) [PMID: {p.get('pmid')}]")

    print("\n" + "="*40)
    print("[State Machine]")
    if getattr(args, 'post_write', False):
        print("Current state: Phase 3 (Section Writing) - Post-writing supplementary search complete.")
        print(f"Next steps: ")
        print(f"- Newly retrieved references have been appended to {args.file} under the `{args.section}` tag.")
        print("- Please run `read_references.py` to get the latest references and supplement the section `.md` file to increase reference count.")
    else:
        print(f"Current state: Phase 2 (Data Retrieval) - Search complete. Retrieved references for section `{args.section}`.")
        print("Next steps: ")
        print("- If more sections need retrieval, continue running this script.")
        print("- If all section searches are complete, run `count_references.py` to check total reference count.")
    print("="*40 + "\n")

if __name__ == "__main__":
    main()
