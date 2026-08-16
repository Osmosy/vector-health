import argparse
import sys
import json
import urllib.request
import urllib.parse
import time
from utils import fetch_details

# Force UTF-8 encoding for stdout/stderr to satisfy user request and prevent GBK errors on Windows
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

LITSENSE_URL = "https://www.ncbi.nlm.nih.gov/research/litsense-api/api/"

def search_litsense(query, max_results=100):
    """
    Search LitSense for a given query and return a list of PMIDs.
    """
    params = {
        "query": query,
        "rerank": "true"
    }
    
    query_string = urllib.parse.urlencode(params)
    url = f"{LITSENSE_URL}?{query_string}"
    
    try:
        # LitSense has a rate limit of 1 request per second
        time.sleep(1.0) 
        
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'ReferenceRetrievalSkill/1.0')
        
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            
            pmids = []
            seen = set()
            
            for item in data:
                pmid = str(item.get("pmid"))
                if pmid and pmid not in seen:
                    pmids.append(pmid)
                    seen.add(pmid)
                    if len(pmids) >= max_results:
                        break
            
            return pmids
            
    except Exception as e:
        print(f"Error searching LitSense: {e}", file=sys.stderr)
        return []

def main():
    parser = argparse.ArgumentParser(description="Search PubMed using LitSense (Semantic Search).")
    parser.add_argument("query", nargs="+", help="Natural language query string")
    parser.add_argument("--max", type=int, default=20, help="Max results to return")
    
    args = parser.parse_args()
    
    # Join the query parts
    full_query = " ".join(args.query)
    
    id_list = search_litsense(full_query, args.max)
    
    if not id_list:
        print(json.dumps([]))
        return

    papers = fetch_details(id_list)
    print(json.dumps(papers, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
