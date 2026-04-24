"""
tools/search.py

GOV.UK search via Tavily AI search API.
Restricted to gov.uk domain for relevant results.
"""

import requests
from config.settings import TAVILY_API_KEY, TAVILY_MAX_RESULTS, VERIFY_SSL, DEBUG


def search_govuk(query: str) -> dict:
    """
    Searches GOV.UK using Tavily.
    Returns a list of results with title, description, and URL.
    """
    if not TAVILY_API_KEY:
        return {"error": "TAVILY_API_KEY not set", "results": []}

    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": query,
                "max_results": TAVILY_MAX_RESULTS,
                "include_domains": ["gov.uk"],
                "search_depth": "basic",
            },
            timeout=10,
            verify=VERIFY_SSL,
        )
        response.raise_for_status()
        data = response.json()

        results = [
            {
                "title": r.get("title", ""),
                "description": r.get("content", "")[:300],
                "url": r.get("url", ""),
            }
            for r in data.get("results", [])
        ]

        if DEBUG:
            print(f"     → {len(results)} results")
            for r in results[:4]:
                print(f"       {r['title'][:65]}")
                print(f"       {r['url']}")

        return {"result_count": len(results), "results": results}

    except requests.RequestException as e:
        if DEBUG:
            print(f"     → ERROR: {e}")
        return {"error": str(e), "result_count": 0, "results": []}
