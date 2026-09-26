from contextlib import nullcontext
from datetime import date, datetime, timezone

import pytest

from collector import run_digest

NEWS = [{"title": "T", "summary_ko": "요약", "source": "hackernews"}]
REPOS = [{"full_name": "o/r", "description": "d", "summary_ko": "레포 요약", "weekly_star_delta": 120}]


class FakeProvider:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def summarize(self, text, kind):
        self.calls.append((text, kind))
        return self.result


def _fake_deps(monkeypatch, news, provider, saved):
    monkeypatch.setattr(run_digest.db, "connect", lambda: nullcontext(object()))
    monkeypatch.setattr(run_digest.db, "apply_schema", lambda conn: None)
    monkeypatch.setattr(run_digest.db, "week_news", lambda conn: news)
    monkeypatch.setattr(run_digest.db, "rising_repos", lambda conn, n: REPOS)
    monkeypatch.setattr(run_digest.db, "upsert_digest", lambda conn, *a: saved.append(a))
    monkeypatch.setattr(run_digest, "get_provider", lambda: provider)


def test_week_start_is_monday_in_kst():
    # 일요일 16:00 UTC는 KST로 월요일 01:00이다
    assert run_digest.week_start(datetime(2026, 9, 27, 16, tzinfo=timezone.utc)) == date(2026, 9, 28)
    assert run_digest.week_start(datetime(2026, 9, 27, 14, tzinfo=timezone.utc)) == date(2026, 9, 21)


def test_build_text_keeps_repos_within_llm_limit_for_long_news():
    news = [{"title": f"T{i}", "summary_ko": "요" * 300, "source": "hackernews"} for i in range(40)]
    text = run_digest.build_text(news, REPOS)
    assert "o/r" in text[:8000]


def test_main_skips_without_llm_key(monkeypatch):
    saved = []
    _fake_deps(monkeypatch, NEWS, None, saved)
    run_digest.main()
    assert saved == []


def test_main_exits_on_llm_config_error(monkeypatch):
    saved = []
    _fake_deps(monkeypatch, NEWS, None, saved)
    monkeypatch.setattr(run_digest, "get_provider", lambda: (_ for _ in ()).throw(ValueError("bad")))
    with pytest.raises(SystemExit):
        run_digest.main()
    assert saved == []


def test_main_skips_when_no_news(monkeypatch):
    saved = []
    provider = FakeProvider({"title_ko": "t", "body_ko": "b"})
    _fake_deps(monkeypatch, [], provider, saved)
    run_digest.main()
    assert provider.calls == [] and saved == []


def test_main_saves_digest(monkeypatch):
    saved = []
    provider = FakeProvider({"title_ko": "이번 주 AI", "body_ko": "- 뉴스"})
    _fake_deps(monkeypatch, NEWS, provider, saved)
    run_digest.main()
    [(text, kind)] = provider.calls
    assert kind == "digest" and "요약" in text and "o/r" in text
    [(week, title, body)] = saved
    assert isinstance(week, date) and week.weekday() == 0
    assert (title, body) == ("이번 주 AI", "- 뉴스")


def test_main_exits_when_llm_returns_nothing(monkeypatch):
    saved = []
    _fake_deps(monkeypatch, NEWS, FakeProvider(None), saved)
    with pytest.raises(SystemExit):
        run_digest.main()
    assert saved == []
