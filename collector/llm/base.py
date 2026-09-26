import json
import logging
import os
import re
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

log = logging.getLogger("airadar.llm")

Kind = Literal["news", "repo", "digest"]
CATEGORIES = ("claude-code-plugin", "skill", "mcp-server", "cursor-rules", "agent-framework", "other")


class NewsSummary(BaseModel):
    summary_ko: str = Field(min_length=1)


class RepoSummary(BaseModel):
    category: Literal[CATEGORIES]
    summary_ko: str = Field(min_length=1)
    install_commands: list[str] = []


class DigestSummary(BaseModel):
    title_ko: str = Field(min_length=1)
    body_ko: str = Field(min_length=1)


MODELS = {"news": NewsSummary, "repo": RepoSummary, "digest": DigestSummary}

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
    "digest": (
        "다음은 이번 주 AI 뉴스 요약과 급상승 AI 코딩 도구 목록이다. 주어진 항목만 사용하고 추측하지 마라. "
        "뉴스 핵심 5~7개와 주목할 도구 3~5개를 한국어 불릿(- )으로 정리한 주간 브리핑을 써라.\n"
        'JSON만 출력: {"title_ko": "이번 주를 요약한 한 줄 제목", "body_ko": "뉴스\\n- ...\\n\\n도구\\n- ..."}\n\n'
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
