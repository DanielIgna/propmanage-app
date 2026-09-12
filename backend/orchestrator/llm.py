"""Shared Claude JSON helper for orchestrator playbooks (Emergent LLM Key)."""
import json
import os
import uuid


async def claude_json(system: str, prompt: str, session_prefix: str) -> dict:
    key = (os.environ.get("EMERGENT_LLM_KEY") or "").strip()
    if not key:
        raise RuntimeError("EMERGENT_LLM_KEY missing")
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(
        api_key=key,
        session_id=f"{session_prefix}_{uuid.uuid4().hex[:8]}",
        system_message=system,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")
    raw = await chat.send_message(UserMessage(text=prompt))
    text = (raw or "").strip()
    if text.startswith("```"):
        text = "\n".join(line for line in text.splitlines() if not line.startswith("```"))
    i, j = text.find("{"), text.rfind("}")
    if i == -1 or j <= i:
        raise RuntimeError("AI nu a returnat JSON valid")
    return json.loads(text[i:j + 1])
