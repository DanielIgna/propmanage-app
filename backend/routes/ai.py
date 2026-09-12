"""PropManage router: ai."""
import os
import logging
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db import db
from core_utils import serialize_doc
from deps import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["ai"])


from emergentintegrations.llm.chat import LlmChat, UserMessage
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

# ============= AI ASSISTANT# ============= AI ASSISTANT (Claude Haiku 4.5) =============

class AiChatIn(BaseModel):
    message: str
    session_id: Optional[str] = None  # client-managed for conversation continuity


def _build_system_prompt(role: str) -> str:
    base = """Ești PropManage Assistant, un AI util pentru utilizatorii platformei PropManage (Property Operating System).
Răspunzi concis, prietenos, în română.

Despre PropManage:
- Marketplace pentru servicii de mentenanță proprietăți (HVAC, electric, sanitar, alte categorii)
- 4 roluri: Client (proprietar), Specialist (tehnician), Operator (validator), Admin
- Wallet: bani reali pentru plăți, Tokens pentru recompense (+100/job confirmat, +20/review, +500/referral)
- Specialiști plătesc 40-50 RON per lead acceptat
- Plățile sunt securizate în Escrow până la confirmarea lucrării (5% comision platformă)
- Specialiști au tier-uri: ENTRY → VERIFIED (10+ joburi, rating 4.8+) → PREMIUM
- Digital Twin = replică 3D a proprietății cu istoric mentenanță și scor sănătate
"""
    if role == "client":
        return base + """
Ești specializat să ajuți CLIENTUL:
- Diagnoză probleme: dacă utilizatorul spune "AC nu mai răcește" → sugerează categoria HVAC, prioritate Urgent, buget estimat 200-500 RON
- Format răspuns pentru diagnoză: "Categorie: X | Prioritate: Y | Buget estimat: Z RON | Sugestie titlu: ..."
- Răspunde FAQ despre escrow, tokens, cum funcționează platforma
"""
    elif role == "specialist":
        return base + """
Ești specializat să ajuți SPECIALISTUL:
- Sfaturi pentru a deveni VERIFIED rapid
- Cum să răspunzi profesional la clienți
- Cum funcționează lead-urile și plata fee-ului
- Cum să-ți construiești reputația
"""
    return base + "Răspunde la întrebări generale despre platformă."


@router.post("/ai/chat")
async def ai_chat(data: AiChatIn, user: dict = Depends(get_current_user)):
    """AI Assistant chat using Claude Haiku 4.5 via Emergent LLM key"""
    if not EMERGENT_LLM_KEY:
        raise HTTPException(503, "AI Assistant not configured")
    
    session_id = data.session_id or f"{user['id']}:default"
    role = user.get("role", "client")
    
    try:
        # Rebuild conversation history from DB — a fresh LlmChat instance per
        # request has no memory, so previous turns must be replayed explicitly.
        prev = await db.ai_messages.find(
            {"session_id": session_id, "user_id": user["id"]}
        ).sort("created_at", 1).to_list(40)
        initial_messages = [{"role": "system", "content": _build_system_prompt(role)}]
        for m in prev[-20:]:  # cap replayed context at last 20 messages
            if m.get("role") in ("user", "assistant") and m.get("text"):
                initial_messages.append({"role": m["role"], "content": m["text"]})

        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=session_id,
            system_message=_build_system_prompt(role),
            initial_messages=initial_messages,
        ).with_model("anthropic", "claude-haiku-4-5-20251001")
        
        # Send to LLM (history replayed via initial_messages above)
        response_text = await chat.send_message(UserMessage(text=data.message))
        
        # Persist both messages only on success (no orphans)
        now = datetime.now(timezone.utc).isoformat()
        await db.ai_messages.insert_many([
            {"session_id": session_id, "user_id": user["id"], "role": "user", "text": data.message, "created_at": now},
            {"session_id": session_id, "user_id": user["id"], "role": "assistant", "text": response_text, "created_at": now},
        ])
        
        return {"reply": response_text, "session_id": session_id}
    except Exception as e:
        logger.error(f"AI chat error: {e}")
        # Friendly fallback message
        err_str = str(e)
        if "budget" in err_str.lower() or "exceeded" in err_str.lower():
            raise HTTPException(503, "AI Assistant indisponibil - cota a fost depășită. Contactează administratorul pentru a alimenta cheia.")
        raise HTTPException(500, f"AI error: {err_str}")


@router.get("/ai/history")
async def ai_history(session_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    sid = session_id or f"{user['id']}:default"
    msgs = await db.ai_messages.find({"session_id": sid, "user_id": user["id"]}).sort("created_at", 1).to_list(100)
    return [serialize_doc(m) for m in msgs]


