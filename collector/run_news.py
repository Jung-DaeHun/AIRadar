import logging

from collector import db
from collector.llm.base import get_provider, max_calls
from collector.sources import geeknews, hackernews, rss

log = logging.getLogger("airadar.news")

SOURCES = {"rss": rss.fetch, "hackernews": hackernews.fetch, "geeknews": geeknews.fetch}


def collect() -> list[dict]:
    items, failed = [], 0
    for name, fetch in SOURCES.items():
        try:
            got = fetch()
            items += got
            log.info("%s: %d items", name, len(got))
        except Exception:
            failed += 1
            log.exception("%s failed", name)
    if failed == len(SOURCES):
        raise SystemExit(1)
    return items


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    items = collect()
    provider = get_provider()
    with db.connect() as conn:
        db.apply_schema(conn)
        log.info("inserted %d new items", db.upsert_news(conn, items))
        if provider is None:
            log.info("LLM_API_KEY not set; skipping summaries")
            return
        done = 0
        for row in db.news_without_summary(conn, max_calls()):
            result = provider.summarize(f"{row['title']}\n\n{row['excerpt'] or ''}", "news")
            if result:
                db.set_news_summary(conn, row["id"], result["summary_ko"])
                done += 1
        log.info("summarized %d items", done)


if __name__ == "__main__":
    main()
