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
