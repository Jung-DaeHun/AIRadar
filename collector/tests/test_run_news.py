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
