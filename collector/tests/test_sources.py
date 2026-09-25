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
