"""LLM client behind a thin interface; tests inject FakeLLMClient, never network."""

import json
import os
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    def complete(self, prompt: str, schema: dict) -> dict: ...


def parse_json_object(text: str) -> dict:
    """Extract the first JSON object from model text, tolerating fences and prose."""
    text = text.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except ValueError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            if isinstance(parsed, dict):
                return parsed
        except ValueError:
            pass
    raise ValueError(f"no JSON object in model response: {text[:120]!r}")


class GeminiLLMClient:
    def __init__(self, api_key: str | None = None, model: str = "gemini-3.5-flash-lite"):
        self._api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        self._model = model

    def complete(self, prompt: str, schema: dict) -> dict:
        from google import genai

        client = genai.Client(api_key=self._api_key)
        response = client.models.generate_content(
            model=self._model,
            contents=prompt,
        )
        return parse_json_object(response.text)


class FakeLLMClient:
    def __init__(self, scripted: dict | list[dict]):
        if isinstance(scripted, list):
            self._single = None
            self._queue = list(scripted)
        else:
            self._single = dict(scripted)
            self._queue = []

    def complete(self, prompt: str, schema: dict) -> dict:
        if self._single is not None:
            return dict(self._single)
        if not self._queue:
            raise RuntimeError("FakeLLMClient exhausted scripted responses")
        return self._queue.pop(0)
