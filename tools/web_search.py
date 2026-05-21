from __future__ import annotations

try:
    from ddgs import DDGS
    _DDGS = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        _DDGS = True
    except ImportError:
        _DDGS = False

TOOL_DEFINITIONS = [
    {
        "name": "web_search",
        "description": (
            "Search the web via DuckDuckGo and return a summary of the top results. "
            "Use for current events, factual lookups, prices, news, or anything that "
            "may have changed since the model's training cutoff."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of results to return (default: 5, max: 10)"
                },
                "timelimit": {
                    "type": "string",
                    "description": "Restrict results by age: 'd' (day), 'w' (week), 'm' (month), 'y' (year)"
                }
            },
            "required": ["query"]
        }
    }
]


def web_search(query: str, max_results: int = 5, timelimit: str = None) -> dict:
    if not _DDGS:
        return {"error": "ddgs not installed. Run: pip install ddgs"}

    max_results = min(max_results or 5, 10)

    try:
        with DDGS() as ddgs:
            raw = ddgs.text(
                query,
                max_results=max_results,
                timelimit=timelimit,
            )
    except Exception as e:
        return {"error": f"Search failed: {e}"}

    if not raw:
        return {"query": query, "results": [], "count": 0}

    results = [
        {
            "title": r.get("title", ""),
            "url":   r.get("href", ""),
            "snippet": r.get("body", ""),
        }
        for r in raw
    ]

    return {
        "query":   query,
        "count":   len(results),
        "results": results,
    }


TOOL_HANDLERS = {
    "web_search": lambda args: web_search(**args),
}
