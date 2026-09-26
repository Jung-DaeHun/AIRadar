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


def _fake_main_deps(monkeypatch, saved):
    from contextlib import nullcontext
    monkeypatch.setattr(run_news, "SOURCES", {"a": lambda: [{"url": "u", "published_at": None}]})
    monkeypatch.setattr(run_news.db, "connect", lambda: nullcontext(object()))
    monkeypatch.setattr(run_news.db, "apply_schema", lambda conn: None)
    monkeypatch.setattr(run_news.db, "upsert_news", lambda conn, items: saved.extend(items) or len(items))
    monkeypatch.setattr(run_news.db, "record_run", lambda conn, name: saved.append({"url": f"run:{name}"}))


def test_main_saves_news_even_when_llm_config_is_invalid(monkeypatch):
    saved = []
    _fake_main_deps(monkeypatch, saved)
    monkeypatch.setenv("LLM_API_KEY", "k")
    monkeypatch.setenv("LLM_PROVIDER", "bogus")
    with pytest.raises(SystemExit):
        run_news.main()
    assert [i["url"] for i in saved] == ["u", "run:news"]


def test_main_saves_news_and_returns_without_llm_key(monkeypatch):
    saved = []
    _fake_main_deps(monkeypatch, saved)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    run_news.main()
    assert [i["url"] for i in saved] == ["u", "run:news"]


def test_recent_drops_old_items_and_keeps_undated():
    from datetime import datetime, timedelta, timezone
    now = datetime(2026, 9, 25, tzinfo=timezone.utc)
    items = [{"url": "old", "published_at": now - timedelta(days=15)},
             {"url": "new", "published_at": now - timedelta(days=1)},
             {"url": "none", "published_at": None}]
    assert [i["url"] for i in run_news.recent(items, now)] == ["new", "none"]
