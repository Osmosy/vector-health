import http.client
import json
import argparse
import sys
from typing import List, Optional

def search_literature(
    query: str,
    limit: int = 10,
    page: int = 1,
    year_range: Optional[List[int]] = None,
    article_types: Optional[List[str]] = None,
    fields: Optional[List[str]] = None
):
    """
    Search for literature using the internal database API.
    """
    conn = http.client.HTTPSConnection("search-db.xiantaozi.com")
    
    payload_dict = {
        "q": query,
        "n": limit,
        "page": page,
        "params": {} # Wrapper for extra params if needed, but based on user example it is flat
    }
    
    # Based on user example, the structure is flat:
    payload_dict = {
        "q": query,
        "n": limit,
        "page": page,
        "jif": ["", ""],          # Default empty range
        "jcr": ["", ""],          # Default
        "cas": ["", ""],          # Default
        "mg": ["", ""],           # Default
        "dm_type": article_types if article_types else ["", ""],
        "dm_type_exclude": [""],
        "dm_time": [str(y) for y in year_range] if year_range else ["", ""],
        "fields": fields if fields else ["", "", ""],
        "nonull_fields": "",
        "min_s": "",
    }

    # Clean up empty lists to match the exact requirement if strictly needed, 
    # but the user example shows explicit empty strings in lists.
    # Let's trust the user's example payload structure.
    
    payload = json.dumps(payload_dict)
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    try:
        conn.request("POST", "/api/v1/literature/search/query", payload, headers)
        res = conn.getresponse()
        data = res.read()
        
        if res.status != 200:
            print(f"Error: API returned status code {res.status}", file=sys.stderr)
            print(data.decode("utf-8"), file=sys.stderr)
            return None
            
        return json.loads(data.decode("utf-8"))
        
    except Exception as e:
        print(f"Error connecting to API: {e}", file=sys.stderr)
        return None
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(description="Search internal literature database.")
    parser.add_argument("query", type=str, help="The search query string (q)")
    parser.add_argument("-n", "--limit", type=int, default=10, help="Number of results to return (default: 10)")
    parser.add_argument("-p", "--page", type=int, default=1, help="Page number (default: 1)")
    parser.add_argument("--years", type=str, help="Year range, e.g., '2020,2024'")
    parser.add_argument("--types", type=str, help="Article types, comma separated")
    parser.add_argument("--fields", type=str, help="Fields to return, comma separated")
    
    args = parser.parse_args()
    
    year_range = None
    if args.years:
        try:
            parts = args.years.split(',')
            if len(parts) == 2:
                year_range = [int(p.strip()) for p in parts]
            else:
                 # If single year provided, use it for both start and end? or just one?
                 # API expects 2 values for range.
                 val = int(parts[0].strip())
                 year_range = [val, val]
        except ValueError:
            print("Error: Years must be integers separated by comma, e.g., '2020,2024'", file=sys.stderr)
            sys.exit(1)

    article_types = None
    if args.types:
        article_types = [t.strip() for t in args.types.split(',')]
        # Pad with empty string if less than 2? User example had ["", ""].
        # Let's ensure it's a list. The API might handle variable length.
        # But looking at user example: "dm_type": ["", ""], it seems it expects a list of strings.

    fields = None
    if args.fields:
        fields = [f.strip() for f in args.fields.split(',')]

    result = search_literature(
        query=args.query,
        limit=args.limit,
        page=args.page,
        year_range=year_range,
        article_types=article_types,
        fields=fields
    )
    
    if result:
        # Output formatted JSON to stdout so it can be piped or read by other tools
        print(json.dumps(result, indent=2, ensure_ascii=False))

    print("\n" + "="*40, file=sys.stderr)
    print("[State Machine]", file=sys.stderr)
    print("Current state: Internal literature search complete.", file=sys.stderr)
    print("Next steps: ", file=sys.stderr)
    print("- Analyze the retrieved JSON results to assist with current section writing.", file=sys.stderr)
    print("- You may also adjust search criteria and re-search as needed.", file=sys.stderr)
    print("="*40 + "\n", file=sys.stderr)

if __name__ == "__main__":
    main()
