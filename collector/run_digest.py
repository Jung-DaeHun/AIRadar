import logging
from datetime import date, datetime, timedelta, timezone

from collector import db
from collector.llm.base import get_provider

log = logging.getLogger("airadar.digest")

KST = timezone(timedelta(hours=9))
REPO_N = 10


def week_start(now: datetime) -> date:
    day = now.astimezone(KST).date()
    return day - timedelta(days=day.weekday())


def build_text(news: list[dict], repos: list[dict]) -> str:
    # summarize가 8000자에서 자르므로 짧은 도구 목록을 앞에 둔다. 잘려도 오래된 뉴스만 빠진다
    lines = ["[급상승 도구]"]
    lines += [f"- {r['full_name']} (+{r['weekly_star_delta']}★/주): {r['summary_ko'] or r['description'] or ''}"
              for r in repos]
    lines.append("\n[뉴스]")
    lines += [f"- ({n['source']}) {n['title']}: {n['summary_ko']}" for n in news]
    return "\n".join(lines)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    try:
        provider = get_provider()
    except ValueError as e:
        log.error("LLM config error: %s", e)
        raise SystemExit(1)
    if provider is None:
        log.info("LLM_API_KEY not set; skipping digest")
        return
    with db.connect() as conn:
        db.apply_schema(conn)
        news = db.week_news(conn)
        if not news:
            log.info("no summarized news this week; skipping digest")
            return
        result = provider.summarize(build_text(news, db.rising_repos(conn, REPO_N)), "digest")
        if result is None:
            log.error("digest generation failed")
            raise SystemExit(1)
        db.upsert_digest(conn, week_start(datetime.now(timezone.utc)), result["title_ko"], result["body_ko"])
        log.info("saved digest: %s", result["title_ko"])


if __name__ == "__main__":
    main()
