import logging
import os
import time
from datetime import date, datetime, timedelta

import httpx

log = logging.getLogger("airadar.github")

API = "https://api.github.com"
TOPICS = ["claude-code", "claude-code-plugin", "claude-skills", "mcp-server",
          "model-context-protocol", "cursor-rules", "ai-agents"]


def _headers(raw: bool = False) -> dict:
    h = {"Accept": "application/vnd.github.raw" if raw else "application/vnd.github+json",
         "User-Agent": "airadar/0.1"}
    if token := os.environ.get("GITHUB_TOKEN"):
        h["Authorization"] = f"Bearer {token}"
    return h


def _dt(s: str | None) -> datetime | None:
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def parse_search(data: dict) -> list[dict]:
    return [{"full_name": r["full_name"], "description": r.get("description"), "url": r["html_url"],
             "stars": r["stargazers_count"], "pushed_at": _dt(r.get("pushed_at")),
             "created_at": _dt(r.get("created_at")), "topics": r.get("topics", [])}
            for r in data.get("items", []) if not r.get("archived")]


def merge(batches: list[list[dict]]) -> list[dict]:
    seen: dict[str, dict] = {}
    for batch in batches:
        for repo in batch:
            seen.setdefault(repo["full_name"], repo)
    return list(seen.values())


def fetch() -> list[dict]:
    since = date.today() - timedelta(days=90)
    created = date.today() - timedelta(days=30)
    delay = 2 if os.environ.get("GITHUB_TOKEN") else 7  # Search API 분당 호출 제한
    # 인기 레포 + 최근 30일 내 생성된 신규 레포(stars 정렬 상위 50에 밀려 누락되지 않게)
    queries = [q for t in TOPICS for q in (f"topic:{t} stars:>=20 pushed:>={since}",
                                           f"topic:{t} stars:>=20 created:>={created}")]
    batches = []
    for i, q in enumerate(queries):
        if i:
            time.sleep(delay)
        try:
            r = httpx.get(f"{API}/search/repositories", headers=_headers(), timeout=20, params={
                "q": q, "sort": "stars", "order": "desc", "per_page": 50,
            })
        except httpx.HTTPError as e:
            log.warning("search %s failed: %s", q, e)
            continue
        if r.status_code != 200:
            log.warning("search %s failed: %s", q, r.status_code)
            continue
        batches.append(parse_search(r.json()))
    return merge(batches)


def fetch_readme(full_name: str) -> str | None:
    try:
        r = httpx.get(f"{API}/repos/{full_name}/readme", headers=_headers(raw=True),
                      timeout=20, follow_redirects=True)
    except httpx.HTTPError as e:
        log.warning("readme %s failed: %s", full_name, e)
        return None
    return r.text if r.status_code == 200 else None
