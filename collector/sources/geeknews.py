from . import rss
from .keywords import is_ai

URL = "https://news.hada.io/rss/news"


def parse(xml: bytes | str) -> list[dict]:
    return [i for i in rss.parse(xml, "geeknews", lang="ko")
            if is_ai(f"{i['title']} {i['excerpt'] or ''}")]


def fetch() -> list[dict]:
    return parse(rss.get(URL))
