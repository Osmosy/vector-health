"""
Medical research vector database search script
Usage:
1. Run with default config: python scripts/search.py
2. Pass a temporary query: python scripts/search.py "<rewritten query>"
"""

import json
import sys
from pathlib import Path

import requests

CONFIG = {
    "query": "sample query",
    "limit": 10,
    "output_file": Path("tmp") / "run_search_result.json",
}

URL = "https://vec-8n3pqt.newidea.pro/vector/v2/documents/search"
HEADERS = {
    'collection-name': '19540e8c-64bf-4cbf-8c7a-b0421575d5f5',
    'tenant_name': '',
    'Content-Type': 'application/json'
}


def search(query: str, limit: int = 10) -> dict:
    """Call vector database search API, return raw response JSON."""
    payload = json.dumps({
        "collection_alias": "wiki_production",
        "query": query,
        "retrieval_config": {
            "rerank_enable": False,
            "search_method": "hybrid_search",
            "score_threshold": 0.1,
            "alpha": 0.7,
            "limit": limit
        }
    })
    response = requests.request("POST", URL, headers=HEADERS, data=payload)
    response.raise_for_status()
    return response.json()


def normalize_items(results: dict) -> list[dict]:
    """Extract and normalize result fields."""
    items = results.get("data") or results.get("results") or []
    normalized = []
    for item in items:
        metadata = item.get("metadata", {})
        props = item.get("properties", {})
        child_chunks = props.get("child_chunks", [])
        child_meta = {}
        if child_chunks:
            child_meta = child_chunks[0].get("properties", {}).get("metadata", {})

        normalized.append(
            {
                "score": metadata.get("score"),
                "kb_name": child_meta.get("helix_wiki_knowledge_name", ""),
                "node_name": child_meta.get("helix_wiki_node_name", ""),
                "url": child_meta.get("helix_wiki_node_url", ""),
                "content": props.get("text", ""),
            }
        )
    return normalized


def dedupe_by_url(items: list[dict]) -> list[dict]:
    """Deduplicate by URL; keep items without a URL."""
    seen = set()
    deduped = []
    for item in items:
        key = item["url"] or json.dumps(item, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def save_results(query: str, items: list[dict], output_file: Path) -> None:
    """Save results as UTF-8 JSON file."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "query": query,
        "count": len(items),
        "results": items,
    }
    with output_file.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def print_results(query: str, items: list[dict], output_file: Path) -> None:
    """Print search results in readable format."""
    if not items:
        print(f"Query: {query}")
        print("[No relevant documents found, please try adjusting query keywords]")
        print(f"Results file: {output_file}")
        return

    print(f"Query: {query}")
    print(f"Results after dedup: {len(items)}")
    print(f"Results file: {output_file}")
    print()

    for index, item in enumerate(items, start=1):
        score = item["score"]
        score_text = f"{score:.4f}" if isinstance(score, float) else str(score)
        content = item["content"].replace("\r", " ").replace("\n", " ").strip()
        if len(content) > 180:
            content = f"{content[:180]}..."

        print(f"[{index}] Relevance: {score_text}")
        print(f"Source: {item['kb_name']} > {item['node_name']}".strip(" >"))
        if item["url"]:
            print(f"Link: {item['url']}")
        print(f"Summary: {content}")
        print()


if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) >= 2 else CONFIG["query"]
    limit = CONFIG["limit"]
    output_file = CONFIG["output_file"]

    results = search(query, limit=limit)
    normalized = normalize_items(results)
    deduped = dedupe_by_url(normalized)
    save_results(query, deduped, output_file)
    print_results(query, deduped, output_file)
