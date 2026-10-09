"""QA Copilot — AI-assisted manual testing engine.

Uses Claude Sonnet 4.5 via Emergent LLM Key to:
1. Analyze user-reported findings (categorize, set severity, suggest next tests)
2. Cross-reference against prior findings (regression memory)
3. Generate a production-ready Emergent prompt from all findings in a session

Code-aware mode (Phase 71): when enabled, the analyzer is given a snapshot of
the actual project file paths so it cannot hallucinate non-existent paths.

All functions are graceful — never raise; return {"error": "..."} on failure.
"""
import os
import uuid
import json
import logging
from typing import Optional

try:
    from ai_core.code_index import build_index_summary, validate_paths
    _CODE_AWARE_AVAILABLE = True
except Exception:
    _CODE_AWARE_AVAILABLE = False
    def build_index_summary(*args, **kwargs):
        return ""
    def validate_paths(suspected):
        return {"valid": list(suspected or []), "invalid": []}

logger = logging.getLogger("propmanage.qa_copilot")

_MODEL = ("anthropic", "claude-sonnet-4-5-20250929")

_ANALYZE_SYS = """You are a senior QA engineer for PropManage — a Romanian SaaS platform for property
management (3D Digital Twin, marketplace of verified specialists, escrow payments, admin tools, Verified Estate
module). The product owner is doing manual exploratory testing and describing what they see.

For EACH finding, output a STRICT JSON object (no markdown, no prose around it) with these keys:
- category: one of [UI_UX, DATA, LOGIC_BUG, MISSING_FEATURE, INTEGRATION, PERFORMANCE, SECURITY]
- severity: one of [P0, P1, P2, P3]  (P0 = blocker, P1 = high, P2 = medium, P3 = low/cosmetic)
- summary: 1 short sentence describing the issue (≤120 chars, Romanian)
- suspected_files: array of 1-4 likely backend/frontend file paths (e.g. "backend/routes/matching.py", "frontend/src/pages/SpecialistDashboard.jsx"). Be specific.
- suggested_next_tests: array of 2-4 follow-up manual tests the user should try to confirm scope/regressions. Each as a short imperative sentence in Romanian.
- related_finding_ids: array of finding_id strings from the provided prior_findings that look related (same root cause, same component, same flow). Empty array if none.

Reply ONLY with valid JSON. No code blocks, no explanation."""


_PROMPT_GEN_SYS = """You are a technical product manager creating a precise, actionable bug-fix prompt for a coding
assistant (Emergent). Given a manual QA session with multiple findings, produce ONE consolidated prompt in Romanian
that the user can paste back into the chat with Emergent.

The prompt MUST contain:
1. Short title (1 line) summarizing the session goal.
2. Numbered list of distinct issues found. For each issue:
   - Severity tag [P0/P1/P2/P3]
   - Reproduction steps (concrete, role-aware: "Login as <role>, go to <path>, click X, observe Y")
   - Expected vs Actual
   - Suspected files (from AI analysis)
3. A "Priorități recomandate" section ordering the issues by impact.
4. A closing sentence: "Te rog confirmă planul înainte să modifici cod și folosește testing_agent_v3_fork după fiecare fix."

Format the output as clean Markdown. NO code fences around the whole prompt. Be concise — total ≤ 1800 words.
Reply ONLY with the Markdown prompt, no commentary."""


def _llm_chat(system_message: str, session_id: str):
    """Build a fresh Claude chat instance. Returns None if key not configured."""
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        return None
    try:
        from llm_chat import LlmChat
        return LlmChat(api_key=key, session_id=session_id, system_message=system_message).with_model(*_MODEL)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[qa_copilot] LLM init failed: {e}")
        return None


def _parse_json(raw: str) -> Optional[dict]:
    """Best-effort JSON extraction from LLM output."""
    if not raw:
        return None
    raw = raw.strip()
    # Strip ```json fences if any
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1] if raw.count("```") >= 2 else raw[3:]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0]
    try:
        return json.loads(raw.strip())
    except Exception:
        # Try to find {...}
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(raw[start:end + 1])
            except Exception:
                return None
    return None


async def analyze_finding(finding_text: str, *, role: str, area: str, prior_findings: list[dict], code_aware: bool = True) -> dict:
    """Analyze a single finding using Claude.

    Args:
        finding_text: User's free-text description of what they observed.
        role: Role being tested (client/specialist/operator/admin).
        area: Free-text area being tested (e.g. "Match specialist").
        prior_findings: List of {id, text, summary} from same/previous sessions.
        code_aware: When True (default), injects the real project file tree so
            the AI cannot hallucinate paths. Validates suspected_files after.

    Returns: dict with category, severity, summary, suspected_files, suggested_next_tests, related_finding_ids.
             On failure returns {"error": "...", "category": "UI_UX", "severity": "P2", ...} fallback.
    """
    fallback = {
        "category": "UI_UX",
        "severity": "P2",
        "summary": (finding_text or "")[:120],
        "suspected_files": [],
        "suggested_next_tests": [],
        "related_finding_ids": [],
        "code_aware": code_aware,
    }
    if not (finding_text or "").strip():
        return {**fallback, "error": "Empty finding"}

    sys_msg = _ANALYZE_SYS
    if code_aware and _CODE_AWARE_AVAILABLE:
        index = build_index_summary()
        if index:
            sys_msg = _ANALYZE_SYS + (
                "\n\nCODE-AWARE MODE: Below is the REAL list of files in this project. "
                "When choosing `suspected_files`, you MUST pick paths that appear in this list. "
                "Do NOT invent paths. If unsure, return fewer entries rather than guessing.\n\n"
                + index
            )

    chat = _llm_chat(sys_msg, f"qa-copilot-analyze-{uuid.uuid4().hex[:8]}")
    if chat is None:
        return {**fallback, "error": "ANTHROPIC_API_KEY not configured"}

    prior_block = ""
    if prior_findings:
        prior_block = "\n\nPRIOR FINDINGS (for related_finding_ids):\n" + "\n".join(
            f"- id={f['id']} :: {(f.get('summary') or f.get('text') or '')[:140]}"
            for f in prior_findings[-30:]
        )

    user_text = (
        f"ROLE TESTED: {role}\nAREA: {area}\n\nCURRENT FINDING:\n{finding_text.strip()}{prior_block}\n\n"
        "Return JSON only."
    )

    try:
        from llm_chat import UserMessage
        raw = await chat.send_message(UserMessage(text=user_text))
        parsed = _parse_json(raw)
        if not parsed:
            return {**fallback, "error": "Could not parse AI response", "raw": (raw or "")[:500]}
        suspected_raw = [str(x)[:200] for x in (parsed.get("suspected_files") or [])][:6]
        # Validate against real codebase if code-aware
        validation = validate_paths(suspected_raw) if code_aware else {"valid": suspected_raw, "invalid": []}
        return {
            "category": parsed.get("category") or fallback["category"],
            "severity": parsed.get("severity") or fallback["severity"],
            "summary": (parsed.get("summary") or fallback["summary"])[:200],
            "suspected_files": validation["valid"],
            "invalid_paths_filtered": validation["invalid"],
            "suggested_next_tests": [str(x)[:300] for x in (parsed.get("suggested_next_tests") or [])][:6],
            "related_finding_ids": [str(x) for x in (parsed.get("related_finding_ids") or [])][:10],
            "code_aware": code_aware,
        }
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[qa_copilot.analyze] failed: {e}")
        return {**fallback, "error": f"{type(e).__name__}: {str(e)[:200]}"}


async def generate_emergent_prompt(session: dict) -> dict:
    """Compile all findings of a session into a single Emergent-ready prompt.

    Args:
        session: full session dict with title, goal, role_being_tested, area, findings[].

    Returns: {"prompt": "...", "provider": "claude-sonnet-4-5"} or {"error": "..."}.
    """
    findings = session.get("findings") or []
    if not findings:
        return {"error": "No findings in session"}

    chat = _llm_chat(_PROMPT_GEN_SYS, f"qa-copilot-prompt-{uuid.uuid4().hex[:8]}")
    if chat is None:
        return {"error": "ANTHROPIC_API_KEY not configured"}

    findings_block = []
    for i, f in enumerate(findings, 1):
        a = f.get("ai_analysis") or {}
        findings_block.append(
            f"### Finding {i}\n"
            f"- ts: {f.get('ts', '')}\n"
            f"- text: {f.get('text', '')}\n"
            f"- ai.category: {a.get('category', '')}\n"
            f"- ai.severity: {a.get('severity', '')}\n"
            f"- ai.summary: {a.get('summary', '')}\n"
            f"- ai.suspected_files: {', '.join(a.get('suspected_files') or [])}\n"
            f"- ai.next_tests: {' | '.join(a.get('suggested_next_tests') or [])}"
        )

    user_text = (
        f"# Session: {session.get('title', '(no title)')}\n"
        f"- Goal: {session.get('goal', '')}\n"
        f"- Role tested: {session.get('role_being_tested', '')}\n"
        f"- Area: {session.get('area', '')}\n\n"
        f"## Findings ({len(findings)})\n\n" + "\n\n".join(findings_block) +
        "\n\nProduce the consolidated Markdown bug-fix prompt now."
    )

    try:
        from llm_chat import UserMessage
        raw = await chat.send_message(UserMessage(text=user_text))
        return {"prompt": (raw or "").strip(), "provider": "claude-sonnet-4-5"}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[qa_copilot.generate_prompt] failed: {e}")
        return {"error": f"{type(e).__name__}: {str(e)[:200]}"}
