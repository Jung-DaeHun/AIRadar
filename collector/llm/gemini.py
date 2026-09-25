from .base import Provider


class GeminiProvider(Provider):
    def __init__(self, api_key: str, model: str):
        from google import genai

        self.client = genai.Client(api_key=api_key)
        self.model = model

    def complete(self, prompt: str) -> str:
        return self.client.models.generate_content(model=self.model, contents=prompt).text or ""
