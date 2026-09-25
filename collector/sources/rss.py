import html
import logging
import re
from datetime import datetime, timezone

import feedparser
import httpx

log = logging.getLogger("airadar.rss")

FEEDS = {
    "openai": "https://openai.com/news/rss.xml",
    "deepmind": "https://deepmind.google/blog/rss.xml",
    "huggingface": "https://huggingface.co/blog/feed.xml",
    "google-ai": "https://blog.google/technology/ai/rss/",
}
_TAG = re.compile(r"<[^>]+>")


def _clean(s: str | None) -> str:
    return html.unescape(_TAG.sub("", s or "")).strip()


def _date(entry) -> datetime | None:
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    return datetime(*t[:6], tzinfo=timezone.utc) if t else None


def parse(xml: bytes | str, source: str, lang: str = "en") -> list[dict]:
    items = []
    for e in feedparser.parse(xml).entries:
        url, title = e.get("link"), _clean(e.get("title"))
        if not url or not title:
            continue
        items.append({"source": source, "url": url, "title": title, "published_at": _date(e),
                      "excerpt": _clean(e.get("summary"))[:500] or None, "lang": lang})
    return items


def get(url: str) -> bytes:
    r = httpx.get(url, timeout=20, follow_redirects=True, headers={"User-Agent": "airadar/0.1"})
    r.raise_for_status()
    return r.content


def fetch() -> list[dict]:
    items = []
    for source, url in FEEDS.items():
        try:
            items += parse(get(url), source)
        except httpx.HTTPError as e:
            log.warning("feed %s failed: %s", source, e)
    return items
