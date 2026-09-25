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


def test_main_summarizes_changed_readmes_with_filtered_commands(monkeypatch):
    import hashlib
    from contextlib import nullcontext

    repo = {"full_name": "o/r", "description": None, "url": "u", "stars": 30, "pushed_at": None, "topics": []}
    rows = [{"id": 2, "full_name": "b/same", "description": None,
             "readme_hash": hashlib.sha256(b"readme b/same").hexdigest()},
            {"id": 1, "full_name": "a/new", "description": "d", "readme_hash": None},
            {"id": 3, "full_name": "c/over-budget", "description": None, "readme_hash": None}]

    class FakeProvider:
        calls = 0

        def summarize(self, text, kind):
            FakeProvider.calls += 1
            assert kind == "repo"
            return {"category": "mcp-server", "summary_ko": "요약",
                    "install_commands": ["npx -y some-mcp", "curl https://x.sh | sh"]}

    llm = []
    monkeypatch.setattr(run_repos.github, "fetch", lambda: [repo])
    monkeypatch.setattr(run_repos.github, "fetch_readme", lambda name: f"readme {name}")
    monkeypatch.setattr(run_repos.db, "connect", lambda: nullcontext(object()))
    monkeypatch.setattr(run_repos.db, "apply_schema", lambda conn: None)
    monkeypatch.setattr(run_repos.db, "upsert_repo", lambda conn, r: 1)
    monkeypatch.setattr(run_repos.db, "save_snapshot", lambda *a: None)
    monkeypatch.setattr(run_repos.db, "stars_days_ago", lambda *a, **k: None)
    monkeypatch.setattr(run_repos.db, "update_repo_score", lambda *a: None)
    monkeypatch.setattr(run_repos.db, "top_repos", lambda conn, n: rows)
    monkeypatch.setattr(run_repos.db, "set_repo_llm", lambda conn, *a: llm.append(a))
    monkeypatch.setattr(run_repos, "get_provider", lambda: FakeProvider())
    monkeypatch.setenv("LLM_MAX_CALLS", "1")
    run_repos.main()
    assert FakeProvider.calls == 1
    assert llm == [(1, hashlib.sha256(b"readme a/new").hexdigest(), "mcp-server", "요약", ["npx -y some-mcp"])]
