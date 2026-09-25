import re

_EN = re.compile(
    r"(?<![A-Za-z])(ai|llms?|gpt|claude|gemini|openai|anthropic|agents?|agentic|mcp|rag|"
    r"transformers?|diffusion|copilot|chatbots?|deepmind|hugging ?face)(?![A-Za-z])",
    re.IGNORECASE,
)
_KO = ("인공지능", "에이전트", "머신러닝", "딥러닝", "언어모델", "언어 모델")


def is_ai(text: str) -> bool:
    return bool(_EN.search(text)) or any(k in text for k in _KO)
