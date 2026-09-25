import httpx

from collector.sources import github
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


def fake_get_timeout_on_third_call():
    calls = []

    def get(url, **kwargs):
        calls.append(url)
        if len(calls) == 3:
            raise httpx.ReadTimeout("timeout")
        return httpx.Response(200, json={"items": [item(f"o/r{len(calls)}")]})
    return get


def test_fetch_skips_topic_on_network_error(monkeypatch):
    monkeypatch.setattr(github.time, "sleep", lambda s: None)
    monkeypatch.setattr(github.httpx, "get", fake_get_timeout_on_third_call())
    names = [r["full_name"] for r in github.fetch()]
    assert names == [f"o/r{i}" for i in range(1, len(github.TOPICS) + 1) if i != 3]


def test_fetch_readme_returns_none_on_network_error(monkeypatch):
    def get(url, **kwargs):
        raise httpx.ReadTimeout("timeout")
    monkeypatch.setattr(github.httpx, "get", get)
    assert github.fetch_readme("o/r") is None
