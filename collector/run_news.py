import logging
from datetime import datetime, timedelta, timezone

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


def recent(items: list[dict], now: datetime, days: int = 14) -> list[dict]:
    cutoff = now - timedelta(days=days)
    return [i for i in items if i["published_at"] is None or i["published_at"] >= cutoff]


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    items = recent(collect(), datetime.now(timezone.utc))
    with db.connect() as conn:
        db.apply_schema(conn)
        log.info("inserted %d new items", db.upsert_news(conn, items))
        # LLM 설정 오류가 있어도 뉴스는 이미 저장됐다. 요약만 건너뛰고 실패로 끝내 Actions에서 드러나게 한다
        try:
            provider = get_provider()
        except ValueError as e:
            log.error("LLM config error; skipping summaries: %s", e)
            raise SystemExit(1)
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
