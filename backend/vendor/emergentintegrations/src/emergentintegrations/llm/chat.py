from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class UserMessage:
    text: str
    file_contents: Optional[list] = None


@dataclass
class ImageContent:
    url: str = ""
    media_type: str = "image/jpeg"
    image_base64: str = ""


class LlmChat:
    def __init__(self, api_key: str, session_id: str, system_message: str = "", **_kwargs: Any):
        self.api_key = api_key
        self.session_id = session_id
        self.system_message = system_message
        self._provider = "anthropic"
        self._model = "claude-haiku-4-5-20251001"
        self._temperature = 0.7

    def with_model(self, provider: str, model: str) -> "LlmChat":
        self._provider = provider
        self._model = model
        return self

    def with_temperature(self, temperature: float) -> "LlmChat":
        self._temperature = temperature
        return self

    def with_params(self, **_kwargs: Any) -> "LlmChat":
        return self

    async def send_message(self, message: UserMessage, **_: Any) -> str:
        if not self.api_key:
            raise RuntimeError("EMERGENT_LLM_KEY not configured")
        preview = (message.text or "")[:200]
        return f"AI Assistant local stub: configure EMERGENT_LLM_KEY for real responses. Received: {preview}"

    async def send_message_multimodal_response(self, message: UserMessage, **_: Any):
        text = await self.send_message(message)
        return text, []
