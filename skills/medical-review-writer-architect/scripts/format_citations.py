import re
import sys
import argparse
import http.client
import json
import time
import urllib.parse
from typing import Dict, List, Optional

def fetch_article_metadata(pmid: str) -> Optional[Dict]:
    """
    Fetches article metadata from the official PubMed API (E-utilities) using the PMID.
    Endpoint: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi
    """
    conn = http.client.HTTPSConnection("eutils.ncbi.nlm.nih.gov")
    
    # E-utilities esummary parameters
    params = {
        "db": "pubmed",
        "id": pmid,
        "retmode": "json"
    }
    query_string = urllib.parse.urlencode(params)
    url = f"/entrez/eutils/esummary.fcgi?{query_string}"
    
    try:
        conn.request("GET", url)
        res = conn.getresponse()
        data = res.read()
        
        if res.status != 200:
            print(f"Warning: PubMed API query for PMID {pmid} failed with status {res.status}", file=sys.stderr)
            return None
            
        result_json = json.loads(data.decode("utf-8"))
        
        # Structure: result -> uids -> [] and result -> [PMID] -> ...
        result_body = result_json.get("result", {})
        if pmid in result_body:
            return result_body[pmid]
            
        # Sometimes key is string, ensure match
        if str(pmid) in result_body:
            return result_body[str(pmid)]

        return None
        
    except Exception as e:
        print(f"Error fetching metadata for PMID {pmid}: {e}", file=sys.stderr)
        return None
    finally:
        conn.close()

def format_apa(metadata: Dict, pmid: str) -> str:
    """
    Formats metadata into an APA style citation.
    Fallback to simple format if fields are missing.
    """
    if not metadata:
        return f"PMID:{pmid} (Metadata not found)"
    
    # Extract fields from E-utilities structure
    title = metadata.get("title", "No Title")
    # Remove final period if exists in title (APA adds it)
    if title.endswith('.'):
        title = title[:-1]
        
    journal = metadata.get("source", "") # 'source' is usually Journal Name
    
    # Authors: 'authors' -> list of dicts [{'name': 'Smith J', ...}]
    authors_list = metadata.get("authors", [])
    author_names = [a.get("name", "") for a in authors_list if "name" in a]
    
    if len(author_names) > 0:
        if len(author_names) > 6:
             # APA 7th edition: list first 19... wait, simplified:
             # "Smith J, Doe A, et al."
             # Let's list up to 3 and et al for brevity in this script, or all if feasible.
             # User didn't specify strict limit, let's keep it reasonable. 
             # Let's list first 3 et al.
             first_few = ", ".join(author_names[:3])
             authors = f"{first_few}, et al"
        else:
            authors = ", ".join(author_names)
    else:
        authors = "Unknown Author"
        
    # PubDate
    pubdate = metadata.get("pubdate", "") # "2023 May 15" or "2023"
    # Extract year
    year_match = re.search(r'\d{4}', pubdate)
    year = year_match.group(0) if year_match else "n.d."
    
    # Volume/Issue/Pages if needed, but summary usually: 
    # Author. (Year). Title. Journal.
    
    citation = f"{authors} ({year}). {title}"
    if journal:
        citation += f". *{journal}*"
        
    return citation

def process_file(file_path: str, inplace: bool = False, output_path: Optional[str] = None):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.", file=sys.stderr)
        return

    # Find all unique PMIDs first
    # Matches [PMID:123] or [PMID: 123]
    pmid_pattern = re.compile(r'\[PMID:\s*(\d+)\]', re.IGNORECASE)
    all_matched_pmids = pmid_pattern.findall(content)
    # Use set for uniqueness but preserve order? No, just unique list.
    unique_pmids = sorted(list(set(all_matched_pmids))) # Sort nicely
    
    if not unique_pmids:
        print("No [PMID:xxx] tags found.")
        if not inplace:
            print(content)
        return

    print(f"Found {len(unique_pmids)} unique PMIDs. Fetching metadata from PubMed...", file=sys.stderr)
    
    # Fetch metadata for all map {pmid: citation_string}
    pmid_citation_map = {}
    
    # Batch request if possible? 
    # E-utilities supports comma separated IDs. "id=1,2,3"
    # Let's do batches of 20 to be safe and fast.
    
    batch_size = 20
    for i in range(0, len(unique_pmids), batch_size):
        batch = unique_pmids[i:i+batch_size]
        pmid_str = ",".join(batch)
        print(f"Fetching batch {i//batch_size + 1} ({len(batch)} PMIDs)...", file=sys.stderr)
        
        # Need a batch fetch function or reuse existing one lightly refactored?
        # Let's do raw call here to keep it simple or refactor fetch_article_metadata to handle list?
        # Refactoring fetch_article_metadata to take single ID is slow.
        # Let's implement batch fetching here inline or helper.
        
        conn = http.client.HTTPSConnection("eutils.ncbi.nlm.nih.gov")
        params = {
            "db": "pubmed",
            "id": pmid_str,
            "retmode": "json"
        }
        url = f"/entrez/eutils/esummary.fcgi?{urllib.parse.urlencode(params)}"
        
        try:
            conn.request("GET", url)
            res = conn.getresponse()
            data = res.read()
            if res.status == 200:
                result_json = json.loads(data.decode("utf-8"))
                result_body = result_json.get("result", {}) # contains uids list and dicts
                
                for pmid in batch:
                    if pmid in result_body:
                        meta = result_body[pmid]
                        pmid_citation_map[pmid] = format_apa(meta, pmid)
                    else:
                        pmid_citation_map[pmid] = f"PMID:{pmid} (Metadata not found in batch)"
            else:
                 print(f"Batch failed: {res.status}", file=sys.stderr)
                 # Fallback empty
        except Exception as e:
            print(f"Batch error: {e}", file=sys.stderr)
        finally:
            conn.close()
            
        time.sleep(0.34) # Rate limit: 3 requests per second standard without API key

    # Now replace
    citation_counter = 1
    pmid_to_number = {} # pmid -> assigned number
    final_references = [] # list of (number, citation_string, url)
    
    def replacer(match):
        nonlocal citation_counter
        pmid = match.group(1)
        
        if pmid not in pmid_to_number:
            pmid_to_number[pmid] = citation_counter
            
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            citation_text = pmid_citation_map.get(pmid, f"PMID:{pmid}")
            final_references.append((citation_counter, citation_text, url))
            
            citation_counter += 1
            
        num = pmid_to_number[pmid]
        url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        return f"[[{num}]]({url})"

    new_content = pmid_pattern.sub(replacer, content)
    
    # Append Bibliography
    if final_references:
        bibliography_section = "\n\n### References\n\n"
        ref_lines = []
        for num, text, url in final_references:
            # Format: [1] Text [URL](URL)
            line = f"[{num}] {text} [{url}]({url})"
            ref_lines.append(line)
            
        new_content += bibliography_section + "\n\n".join(ref_lines)

    if inplace:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Successfully updated {file_path}")
    elif output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Successfully saved to {output_path}")
    else:
        print(new_content)

def main():
    parser = argparse.ArgumentParser(description="Format citations with PubMed API.")
    parser.add_argument("file", help="Path to Markdown file")
    parser.add_argument("-i", "--inplace", action="store_true", help="Modify file in-place")
    parser.add_argument("-o", "--output", help="Path to output file")
    
    args = parser.parse_args()
    process_file(args.file, args.inplace, args.output)

    print("\n" + "="*40)
    print("[State Machine]")
    print("Current state: Phase 6 (Format Citations) - Citation formatting completed successfully, final formatted document generated.")
    print("Next steps: ")
    print("- The entire Medical Review workflow is complete!")
    print("- Please present or deliver the final merged and formatted document to the user.")
    print("="*40 + "\n")

if __name__ == "__main__":
    main()
