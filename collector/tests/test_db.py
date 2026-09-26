import os
from datetime import date, datetime, timezone

import pytest

from collector import db

URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL not set")


@pytest.fixture
def conn():
    c = db.connect(URL)
    c.execute("DROP TABLE IF EXISTS repo_star_snapshots, repos, news_items, collector_runs, digests")
    db.apply_schema(c)
    yield c
    c.close()


def news(**kw):
    base = {"source": "hackernews", "url": "https://example.com/a", "title": "A",
            "published_at": None, "excerpt": None, "lang": "en"}
    return base | kw


def test_upsert_news_stores_same_url_once(conn):
    assert db.upsert_news(conn, [news(), news(source="openai")]) == 1


def test_news_without_summary_then_set(conn):
    db.upsert_news(conn, [news()])
    [row] = db.news_without_summary(conn, 10)
    db.set_news_summary(conn, row["id"], "요약")
    assert db.news_without_summary(conn, 10) == []


def repo(**kw):
    base = {"full_name": "o/r", "description": None, "url": "https://github.com/o/r",
            "stars": 10, "pushed_at": datetime.now(timezone.utc), "topics": ["mcp-server"],
            "created_at": datetime(2026, 9, 1, tzinfo=timezone.utc)}
    return base | kw


def test_upsert_repo_updates_existing(conn):
    rid = db.upsert_repo(conn, repo())
    assert db.upsert_repo(conn, repo(stars=20)) == rid


def test_upsert_repo_stores_and_updates_created_at(conn):
    rid = db.upsert_repo(conn, repo(created_at=None))
    db.upsert_repo(conn, repo())
    row = conn.execute("SELECT created_at FROM repos WHERE id = %s", (rid,)).fetchone()
    assert row["created_at"] == datetime(2026, 9, 1, tzinfo=timezone.utc)


def test_stars_days_ago(conn):
    rid = db.upsert_repo(conn, repo())
    db.save_snapshot(conn, rid, 10, date(2026, 9, 1))
    assert db.stars_days_ago(conn, rid, date(2026, 9, 5)) is None
    assert db.stars_days_ago(conn, rid, date(2026, 9, 8)) == 10


def test_stars_days_ago_ignores_snapshots_older_than_14_days(conn):
    rid = db.upsert_repo(conn, repo())
    db.save_snapshot(conn, rid, 10, date(2026, 8, 1))
    assert db.stars_days_ago(conn, rid, date(2026, 9, 8)) is None
    db.save_snapshot(conn, rid, 20, date(2026, 8, 25))
    db.save_snapshot(conn, rid, 30, date(2026, 8, 30))
    assert db.stars_days_ago(conn, rid, date(2026, 9, 8)) == 30


def test_top_repos_and_set_llm(conn):
    rid = db.upsert_repo(conn, repo())
    db.update_repo_score(conn, rid, 5.0, None)
    db.set_repo_llm(conn, rid, "h", "mcp-server", "요약", ["npx -y x"])
    [row] = db.top_repos(conn, 10)
    assert row["readme_hash"] == "h"


def test_top_repos_skips_repos_not_updated_recently(conn):
    rid = db.upsert_repo(conn, repo())
    conn.execute("UPDATE repos SET updated_at = now() - interval '3 days' WHERE id = %s", (rid,))
    assert db.top_repos(conn, 10) == []


def test_record_run_upserts_by_name(conn):
    db.record_run(conn, "news")
    conn.execute("UPDATE collector_runs SET finished_at = now() - interval '1 day'")
    db.record_run(conn, "news")
    rows = conn.execute(
        "SELECT name, finished_at > now() - interval '1 hour' AS fresh FROM collector_runs").fetchall()
    assert rows == [{"name": "news", "fresh": True}]


def test_week_news_returns_recent_summarized_only(conn):
    now = datetime.now(timezone.utc)
    db.upsert_news(conn, [news(url="u1", published_at=now), news(url="u2", published_at=now),
                          news(url="u3", published_at=datetime(2020, 1, 1, tzinfo=timezone.utc))])
    conn.execute("UPDATE news_items SET summary_ko = '요약' WHERE url IN ('u1', 'u3')")
    assert db.week_news(conn) == [{"title": "A", "summary_ko": "요약", "source": "hackernews"}]


def test_rising_repos_orders_by_weekly_star_delta(conn):
    a = db.upsert_repo(conn, repo(full_name="o/a"))
    b = db.upsert_repo(conn, repo(full_name="o/b"))
    c = db.upsert_repo(conn, repo(full_name="o/c"))
    db.update_repo_score(conn, a, 1.0, 5)
    db.update_repo_score(conn, b, 1.0, 50)
    db.update_repo_score(conn, c, 1.0, None)
    assert [r["full_name"] for r in db.rising_repos(conn, 10)] == ["o/b", "o/a"]


def test_upsert_digest_replaces_same_week(conn):
    db.upsert_digest(conn, date(2026, 9, 21), "제목1", "본문1")
    db.upsert_digest(conn, date(2026, 9, 21), "제목2", "본문2")
    rows = conn.execute("SELECT week_start, title_ko, body_ko FROM digests").fetchall()
    assert rows == [{"week_start": date(2026, 9, 21), "title_ko": "제목2", "body_ko": "본문2"}]
