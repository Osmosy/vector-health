import sys
import json
import argparse
import urllib.request
import urllib.parse
from utils import fetch_details

# Force UTF-8 encoding for stdout/stderr to satisfy user request and prevent GBK errors on Windows
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

def search_pubmed(query, max_results=10):
    """
    Search PubMed for a given query and return a list of IDs.
    """
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json",
        "sort": "relevance"
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

def main():
    parser = argparse.ArgumentParser(description="Search PubMed using Boolean queries.")
    parser.add_argument("query", nargs="+", help="Boolean search query string (e.g., 'term1 AND term2')")
    parser.add_argument("--max", type=int, default=20, help="Max results to return")
    
    args = parser.parse_args()
    
    # Join the query parts in case they were split by the shell
    full_query = " ".join(args.query)
    
    id_list = search_pubmed(full_query, args.max)
    
    if not id_list:
        print(json.dumps([]))
        return

    papers = fetch_details(id_list)
    print(json.dumps(papers, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
