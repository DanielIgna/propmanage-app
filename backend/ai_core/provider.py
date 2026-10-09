"""LLM Provider Abstraction Layer.

Single async `call_llm()` entrypoint. Today routes Claude/OpenAI/Gemini via
Emergent LLM Key. Tomorrow Ollama/Qwen/DeepSeek (when user supplies keys).

Provider config is dynamic — read at each call from app_settings.ai_ecosystem
section so admin can switch model from UI without redeploy.
"""
import os
import logging
import uuid
from typing import Optional

from db import db

logger = logging.getLogger("propmanage.ai_core.provider")


# Default provider/model — used when app_settings is missing or feature disabled.
_DEFAULTS = {
    "provider": "anthropic",
    "model": "claude-sonnet-4-5-20250929",
    "temperature": 0.3,
    "max_tokens": 2048,
    "enabled": True,
}

# Supported providers and their models (for UI dropdowns).
PROVIDERS = {
    "anthropic": {
        "label": "Claude (Anthropic)",
        "models": ["claude-sonnet-4-5-20250929", "claude-opus-4-5", "claude-haiku-4-5"],
        "via": "emergent_llm_key",
        "active": True,
    },
    "openai": {
        "label": "OpenAI",
        "models": ["gpt-5.2", "gpt-4o", "gpt-4o-mini"],
        "via": "emergent_llm_key",
        "active": True,
    },
    "gemini": {
        "label": "Google Gemini",
        "models": ["gemini-3-pro", "gemini-3-flash"],
        "via": "emergent_llm_key",
        "active": True,
    },
    "ollama": {
        "label": "Ollama (self-hosted)",
        "models": ["llama-4", "qwen-3", "deepseek-r2"],
        "via": "user_supplied",
        "active": False,  # Requires OLLAMA_BASE_URL + custom config (Phase 5)
    },
}


async def get_ai_config() -> dict:
    """Read live AI config from app_settings or return defaults."""
    doc = await db.app_settings.find_one({"_id": "app_settings"})
    if not doc:
        return {**_DEFAULTS}
    cfg = (doc.get("ai_ecosystem") or {})
    return {
        "enabled": cfg.get("enabled", _DEFAULTS["enabled"]),
        "provider": cfg.get("provider", _DEFAULTS["provider"]),
        "model": cfg.get("model", _DEFAULTS["model"]),
        "temperature": float(cfg.get("temperature", _DEFAULTS["temperature"])),
        "max_tokens": int(cfg.get("max_tokens", _DEFAULTS["max_tokens"])),
    }


async def ecosystem_enabled() -> bool:
    """Global kill-switch for the AI ecosystem (memory + new agents).

    Legacy modules (Concierge, AI Investigator, QA Copilot) keep working
    regardless of this flag — they manage their own state independently.
    """
    cfg = await get_ai_config()
    return bool(cfg.get("enabled", True))


async def call_llm(
    system_message: str,
    user_message: str,
    *,
    session_id: Optional[str] = None,
    override: Optional[dict] = None,
) -> dict:
    """Unified LLM call.

    Returns: {"text": str, "provider": str, "model": str} on success,
             {"error": str, "text": ""} on failure (never raises).
    `override` lets callers force a specific provider/model/temperature
    (used by sub-agents that need a different model than the global default).
    """
    cfg = await get_ai_config()
    if override:
        cfg = {**cfg, **{k: v for k, v in override.items() if v is not None}}

    provider = cfg["provider"]
    model = cfg["model"]
    temperature = cfg["temperature"]

    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        return {"error": "ANTHROPIC_API_KEY not configured", "text": ""}

    # llm_chat implements "anthropic" (Messages API) and "gemini"; other providers raise.
    if provider not in ("anthropic", "openai", "gemini"):
        return {"error": f"Provider '{provider}' not active in Phase 1", "text": ""}

    try:
        from llm_chat import LlmChat, UserMessage
        chat = (
            LlmChat(
                api_key=key,
                session_id=session_id or f"ai-core-{uuid.uuid4().hex[:8]}",
                system_message=system_message,
            )
            .with_model(provider, model)
        )
        # Temperature support varies by SDK version — wrap defensively.
        try:
            chat = chat.with_temperature(temperature)
        except Exception:  # noqa: BLE001
            pass
        text = await chat.send_message(UserMessage(text=user_message))
        return {"text": text or "", "provider": provider, "model": model}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ai_core.call_llm] {provider}/{model} failed: {e}")
        return {"error": f"{type(e).__name__}: {str(e)[:200]}", "text": "", "provider": provider, "model": model}
