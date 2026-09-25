from .base import Provider

DEFAULT_MODEL = "claude-haiku-4-5-20251001"


class ClaudeProvider(Provider):
    def __init__(self, api_key: str, model: str | None = None):
        import anthropic

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model or DEFAULT_MODEL

    def complete(self, prompt: str) -> str:
        resp = self.client.messages.create(
            model=self.model, max_tokens=1024, messages=[{"role": "user", "content": prompt}]
        )
        return resp.content[0].text
