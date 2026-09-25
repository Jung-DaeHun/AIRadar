import os
from datetime import date, datetime, timezone

import pytest

from collector import db

URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL not set")


@pytest.fixture
def conn():
    c = db.connect(URL)
    c.execute("DROP TABLE IF EXISTS repo_star_snapshots, repos, news_items")
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
            "stars": 10, "pushed_at": datetime.now(timezone.utc), "topics": ["mcp-server"]}
    return base | kw


def test_upsert_repo_updates_existing(conn):
    rid = db.upsert_repo(conn, repo())
    assert db.upsert_repo(conn, repo(stars=20)) == rid


def test_stars_days_ago(conn):
    rid = db.upsert_repo(conn, repo())
    db.save_snapshot(conn, rid, 10, date(2026, 9, 1))
    assert db.stars_days_ago(conn, rid, date(2026, 9, 5)) is None
    assert db.stars_days_ago(conn, rid, date(2026, 9, 8)) == 10


def test_top_repos_and_set_llm(conn):
    rid = db.upsert_repo(conn, repo())
    db.update_repo_score(conn, rid, 5.0, None)
    db.set_repo_llm(conn, rid, "h", "mcp-server", "요약", ["npx -y x"])
    [row] = db.top_repos(conn, 10)
    assert row["readme_hash"] == "h"
