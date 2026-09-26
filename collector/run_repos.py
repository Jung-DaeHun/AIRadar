import hashlib
import logging
from datetime import datetime, timezone

from collector import db
from collector.install_cmd import filter_commands
from collector.llm.base import get_provider, max_calls
from collector.scoring import score, weekly_delta
from collector.sources import github

log = logging.getLogger("airadar.repos")

TOP_N = 50


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    repos = github.fetch()
    if not repos:
        log.error("no repos fetched")
        raise SystemExit(1)
    now = datetime.now(timezone.utc)
    today = now.date()
    with db.connect() as conn:
        db.apply_schema(conn)
        for r in repos:
            rid = db.upsert_repo(conn, r)
            db.save_snapshot(conn, rid, r["stars"], today)
            delta = weekly_delta(r["stars"], db.stars_days_ago(conn, rid, today))
            days = (now - r["pushed_at"]).total_seconds() / 86400 if r["pushed_at"] else 90
            db.update_repo_score(conn, rid, score(r["stars"], delta, days), delta)
        log.info("scored %d repos", len(repos))
        db.record_run(conn, "repos")
        # LLM 설정 오류가 있어도 레포·스냅샷은 이미 저장됐다. 요약만 건너뛰고 실패로 끝내 Actions에서 드러나게 한다
        try:
            provider = get_provider()
        except ValueError as e:
            log.error("LLM config error; skipping summaries: %s", e)
            raise SystemExit(1)
        if provider is None:
            log.info("LLM_API_KEY not set; skipping summaries")
            return
        budget = max_calls()
        for row in db.top_repos(conn, TOP_N):
            if budget <= 0:
                break
            readme = github.fetch_readme(row["full_name"])
            if readme is None:
                continue
            digest = hashlib.sha256(readme.encode()).hexdigest()
            if digest == row["readme_hash"]:
                continue
            budget -= 1
            result = provider.summarize(f"{row['full_name']}\n{row['description'] or ''}\n\n{readme}", "repo")
            if result:
                db.set_repo_llm(conn, row["id"], digest, result["category"], result["summary_ko"],
                                filter_commands(result["install_commands"]))


if __name__ == "__main__":
    main()
