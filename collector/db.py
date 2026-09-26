import os
from datetime import date, timedelta
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

SCHEMA = Path(__file__).resolve().parent.parent / "db" / "schema.sql"


def connect(url: str | None = None) -> psycopg.Connection:
    return psycopg.connect(url or os.environ["DATABASE_URL"], row_factory=dict_row, autocommit=True)


def apply_schema(conn) -> None:
    conn.execute(SCHEMA.read_text(encoding="utf-8"))


def upsert_news(conn, items: list[dict]) -> int:
    inserted = 0
    for item in items:
        cur = conn.execute(
            """INSERT INTO news_items (source, url, title, published_at, excerpt, lang)
               VALUES (%(source)s, %(url)s, %(title)s, %(published_at)s, %(excerpt)s, %(lang)s)
               ON CONFLICT (url) DO NOTHING""",
            item,
        )
        inserted += cur.rowcount
    return inserted


def news_without_summary(conn, limit: int) -> list[dict]:
    return conn.execute(
        """SELECT id, title, excerpt FROM news_items WHERE summary_ko IS NULL
           ORDER BY published_at DESC NULLS LAST LIMIT %s""",
        (limit,),
    ).fetchall()


def set_news_summary(conn, news_id: int, summary: str) -> None:
    conn.execute("UPDATE news_items SET summary_ko = %s WHERE id = %s", (summary, news_id))


def upsert_repo(conn, r: dict) -> int:
    row = conn.execute(
        """INSERT INTO repos (full_name, description, url, stars, pushed_at, topics, created_at)
           VALUES (%(full_name)s, %(description)s, %(url)s, %(stars)s, %(pushed_at)s, %(topics)s,
                   %(created_at)s)
           ON CONFLICT (full_name) DO UPDATE SET
             description = EXCLUDED.description, url = EXCLUDED.url, stars = EXCLUDED.stars,
             pushed_at = EXCLUDED.pushed_at, topics = EXCLUDED.topics,
             created_at = EXCLUDED.created_at, updated_at = now()
           RETURNING id""",
        r,
    ).fetchone()
    return row["id"]


def save_snapshot(conn, repo_id: int, stars: int, day: date) -> None:
    conn.execute(
        """INSERT INTO repo_star_snapshots (repo_id, date, stars) VALUES (%s, %s, %s)
           ON CONFLICT (repo_id, date) DO UPDATE SET stars = EXCLUDED.stars""",
        (repo_id, day, stars),
    )


def stars_days_ago(conn, repo_id: int, today: date, days: int = 7) -> int | None:
    row = conn.execute(
        """SELECT stars FROM repo_star_snapshots WHERE repo_id = %s AND date BETWEEN %s AND %s
           ORDER BY date DESC LIMIT 1""",
        (repo_id, today - timedelta(days=days + 7), today - timedelta(days=days)),
    ).fetchone()
    return row["stars"] if row else None


def update_repo_score(conn, repo_id: int, score: float, weekly_delta: int | None) -> None:
    conn.execute(
        "UPDATE repos SET score = %s, weekly_star_delta = %s WHERE id = %s",
        (score, weekly_delta, repo_id),
    )


def top_repos(conn, limit: int) -> list[dict]:
    return conn.execute(
        """SELECT id, full_name, description, readme_hash FROM repos
           WHERE pushed_at >= now() - interval '90 days' AND updated_at >= now() - interval '2 days'
           ORDER BY score DESC LIMIT %s""",
        (limit,),
    ).fetchall()


def set_repo_llm(conn, repo_id: int, readme_hash: str, category: str,
                 summary_ko: str, install_commands: list[str]) -> None:
    conn.execute(
        """UPDATE repos SET readme_hash = %s, category = %s, summary_ko = %s, install_commands = %s
           WHERE id = %s""",
        (readme_hash, category, summary_ko, Jsonb(install_commands), repo_id),
    )


def record_run(conn, name: str) -> None:
    conn.execute(
        """INSERT INTO collector_runs (name, finished_at) VALUES (%s, now())
           ON CONFLICT (name) DO UPDATE SET finished_at = now()""",
        (name,),
    )


def week_news(conn, limit: int = 40) -> list[dict]:
    return conn.execute(
        """SELECT title, summary_ko, source FROM news_items
           WHERE summary_ko IS NOT NULL AND COALESCE(published_at, created_at) >= now() - interval '7 days'
           ORDER BY COALESCE(published_at, created_at) DESC LIMIT %s""",
        (limit,),
    ).fetchall()


def rising_repos(conn, limit: int) -> list[dict]:
    return conn.execute(
        """SELECT full_name, description, summary_ko, weekly_star_delta FROM repos
           WHERE weekly_star_delta IS NOT NULL AND updated_at >= now() - interval '2 days'
           ORDER BY weekly_star_delta DESC LIMIT %s""",
        (limit,),
    ).fetchall()


def upsert_digest(conn, week_start: date, title_ko: str, body_ko: str) -> None:
    conn.execute(
        """INSERT INTO digests (week_start, title_ko, body_ko) VALUES (%s, %s, %s)
           ON CONFLICT (week_start) DO UPDATE SET
             title_ko = EXCLUDED.title_ko, body_ko = EXCLUDED.body_ko, created_at = now()""",
        (week_start, title_ko, body_ko),
    )
