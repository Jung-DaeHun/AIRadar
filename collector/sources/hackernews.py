import time
from datetime import datetime, timezone

import httpx

from .keywords import is_ai

ALGOLIA = "https://hn.algolia.com/api/v1/search_by_date"


def parse(data: dict) -> list[dict]:
    items = []
    for h in data.get("hits", []):
        title = h.get("title") or ""
        if not is_ai(title):
            continue
        items.append({
            "source": "hackernews",
            "url": h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}",
            "title": title,
            "published_at": datetime.fromtimestamp(h["created_at_i"], tz=timezone.utc),
            "excerpt": None,
            "lang": "en",
        })
    return items


def fetch() -> list[dict]:
    since = int(time.time()) - 86400
    r = httpx.get(ALGOLIA, timeout=20, params={
        "tags": "story", "numericFilters": f"created_at_i>{since},points>=50", "hitsPerPage": 100,
    })
    r.raise_for_status()
    return parse(r.json())
