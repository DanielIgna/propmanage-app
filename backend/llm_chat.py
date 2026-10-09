"""LLM chat client (replaces emergentintegrations.llm.chat) on the official provider APIs.

Same surface the codebase already uses:
    chat = LlmChat(api_key=..., session_id=..., system_message=...).with_model("anthropic", "<model>")
    text = await chat.send_message(UserMessage(text="...", file_contents=[ImageContent(image_base64=...)]))
    text, images = await chat.with_params(modalities=["image", "text"]).send_message_multimodal_response(msg)

Providers:
  - "anthropic" → Anthropic Messages API (ANTHROPIC_API_KEY)
  - "gemini"    → Google Gemini generateContent (GEMINI_API_KEY), used for image generation
The conversation history is kept per LlmChat instance (multi-turn within one object).
"""
from __future__ import annotations

import base64
import os
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx
from anthropic import AsyncAnthropic

DEFAULT_MAX_TOKENS = 4096
_GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


@dataclass
class ImageContent:
    url: str = ""
    media_type: str = "image/jpeg"
    image_base64: str = ""


@dataclass
class UserMessage:
    text: str
    file_contents: Optional[list] = field(default=None)


def _image_bytes_b64(img: ImageContent) -> tuple[str, str]:
    """Return (media_type, base64) for an ImageContent given as base64 or URL."""
    if img.image_base64:
        data = img.image_base64.split(",", 1)[1] if img.image_base64.startswith("data:") else img.image_base64
        media = img.media_type or "image/jpeg"
        raw = base64.b64decode(data[:64])  # sniff the format from the header bytes
        if raw.startswith(b"\x89PNG"):
            media = "image/png"
        elif raw[:4] == b"RIFF":
            media = "image/webp"
        elif raw.startswith(b"\xff\xd8"):
            media = "image/jpeg"
        return media, data
    resp = httpx.get(img.url, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    media = resp.headers.get("content-type", img.media_type).split(";")[0]
    return media, base64.b64encode(resp.content).decode()


class LlmChat:
    def __init__(self, api_key: str = "", session_id: str = "", system_message: str = "", **_kwargs: Any):
        self.api_key = api_key
        self.session_id = session_id
        self.system_message = system_message or ""
        self._provider = "anthropic"
        self._model = "claude-haiku-4-5-20251001"
        self._temperature: Optional[float] = None
        self._max_tokens = DEFAULT_MAX_TOKENS
        self._modalities: list[str] = ["text"]
        self._history: list[dict] = []

    # ---- builder API
    def with_model(self, provider: str, model: str) -> "LlmChat":
        self._provider, self._model = provider, model
        return self

    def with_temperature(self, temperature: float) -> "LlmChat":
        self._temperature = temperature
        return self

    def with_max_tokens(self, max_tokens: int) -> "LlmChat":
        self._max_tokens = max_tokens
        return self

    def with_params(self, **kwargs: Any) -> "LlmChat":
        if "modalities" in kwargs:
            self._modalities = list(kwargs["modalities"])
        if "max_tokens" in kwargs:
            self._max_tokens = int(kwargs["max_tokens"])
        if "temperature" in kwargs:
            self._temperature = float(kwargs["temperature"])
        return self

    # ---- keys
    def _anthropic_key(self) -> str:
        key = os.environ.get("ANTHROPIC_API_KEY") or ""
        if not key and (self.api_key or "").startswith("sk-ant-"):
            key = self.api_key
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY not configured")
        return key

    @staticmethod
    def _gemini_key() -> str:
        key = os.environ.get("GEMINI_API_KEY") or ""
        if not key:
            raise RuntimeError("GEMINI_API_KEY not configured")
        return key

    # ---- Anthropic
    async def _anthropic(self, message: UserMessage) -> str:
        content: list[dict] = []
        for img in message.file_contents or []:
            if isinstance(img, ImageContent):
                media, data = _image_bytes_b64(img)
                content.append({"type": "image", "source": {"type": "base64", "media_type": media, "data": data}})
        content.append({"type": "text", "text": message.text or ""})
        self._history.append({"role": "user", "content": content})

        kwargs: dict[str, Any] = {"model": self._model, "max_tokens": self._max_tokens, "messages": self._history}
        if self.system_message:
            kwargs["system"] = self.system_message
        if self._temperature is not None:
            kwargs["temperature"] = self._temperature
        async with AsyncAnthropic(api_key=self._anthropic_key()) as client:
            resp = await client.messages.create(**kwargs)
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        self._history.append({"role": "assistant", "content": text})
        return text

    # ---- Gemini
    async def _gemini(self, message: UserMessage) -> tuple[str, list[dict]]:
        parts: list[dict] = [{"text": message.text or ""}]
        for img in message.file_contents or []:
            if isinstance(img, ImageContent):
                media, data = _image_bytes_b64(img)
                parts.append({"inline_data": {"mime_type": media, "data": data}})
        body: dict[str, Any] = {"contents": [{"role": "user", "parts": parts}]}
        if self.system_message:
            body["system_instruction"] = {"parts": [{"text": self.system_message}]}
        config: dict[str, Any] = {"responseModalities": [m.upper() for m in self._modalities]}
        if self._temperature is not None:
            config["temperature"] = self._temperature
        body["generationConfig"] = config
        async with httpx.AsyncClient(timeout=180) as client:
            r = await client.post(_GEMINI_URL.format(model=self._model),
                                  headers={"x-goog-api-key": self._gemini_key()}, json=body)
        r.raise_for_status()
        out_parts = ((r.json().get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in out_parts)
        images = [{"mime_type": p["inlineData"].get("mimeType", "image/png"), "data": p["inlineData"]["data"]}
                  for p in out_parts if p.get("inlineData")]
        return text, images

    # ---- public
    async def send_message(self, message: UserMessage, **_: Any) -> str:
        if self._provider == "gemini":
            text, _images = await self._gemini(message)
            return text
        if self._provider != "anthropic":
            raise RuntimeError(f"LLM provider not supported: {self._provider}")
        return await self._anthropic(message)

    async def send_message_multimodal_response(self, message: UserMessage, **_: Any):
        """Returns (text, images) where images = [{"mime_type": str, "data": base64 str}]."""
        if self._provider == "gemini":
            return await self._gemini(message)
        return await self.send_message(message), []
