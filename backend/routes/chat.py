"""PropManage router: chat."""
import logging
from typing import List, Dict
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from db import db
from core_utils import serialize_doc
from deps import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])


from fastapi import WebSocket, WebSocketDisconnect
import jwt
from core_utils import JWT_SECRET, JWT_ALGORITHM

# ============= WEBSOCKET CHAT =============

class ConnectionManager:
    def __init__(self):
        # request_id -> list of (user_id, websocket)
        self.active: Dict[str, List[tuple]] = {}
    
    async def connect(self, request_id: str, user_id: str, ws: WebSocket):
        await ws.accept()
        self.active.setdefault(request_id, []).append((user_id, ws))
    
    def disconnect(self, request_id: str, ws: WebSocket):
        if request_id in self.active:
            self.active[request_id] = [(u, w) for u, w in self.active[request_id] if w != ws]
            if not self.active[request_id]:
                del self.active[request_id]
    
    async def broadcast(self, request_id: str, message: dict):
        if request_id not in self.active:
            return
        dead = []
        for uid, ws in self.active[request_id]:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for w in dead:
            self.disconnect(request_id, w)

manager = ConnectionManager()


@router.get("/chat/{request_id}/messages")
async def get_messages(request_id: str, user: dict = Depends(get_current_user)):
    """Get chat history for a request (client or assigned specialist only)"""
    req = await db.requests.find_one({"_id": ObjectId(request_id)})
    if not req:
        raise HTTPException(404, "Request not found")
    if user["role"] == "client" and req.get("client_id") != user["id"]:
        raise HTTPException(403, "Not your request")
    if user["role"] == "specialist" and req.get("specialist_id") != user["id"]:
        raise HTTPException(403, "Not assigned to you")
    
    msgs = await db.chat_messages.find({"request_id": request_id}).sort("timestamp", 1).to_list(200)
    return [serialize_doc(m) for m in msgs]


@router.websocket("/ws/chat/{request_id}")
async def chat_ws(websocket: WebSocket, request_id: str):
    """WebSocket endpoint for real-time chat. Auth via token query param."""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001)
        return
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        uid = payload["sub"]
        user = await db.users.find_one({"_id": ObjectId(uid)})
        if not user:
            await websocket.close(code=4001); return
        user_id = str(user["_id"])
        user_name = user.get("name", "User")
        user_role = user.get("role", "client")
    except Exception:
        await websocket.close(code=4001)
        return
    
    # Verify access to request
    req = await db.requests.find_one({"_id": ObjectId(request_id)})
    if not req:
        await websocket.close(code=4004); return
    if user_role == "client" and req.get("client_id") != user_id:
        await websocket.close(code=4003); return
    if user_role == "specialist" and req.get("specialist_id") != user_id:
        await websocket.close(code=4003); return
    
    await manager.connect(request_id, user_id, websocket)
    try:
        # Send system message: user joined
        join_msg = {
            "type": "system",
            "text": f"{user_name} a intrat în conversație",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await manager.broadcast(request_id, join_msg)
        
        while True:
            data = await websocket.receive_json()
            text = (data.get("text") or "").strip()
            if not text:
                continue
            msg = {
                "type": "message",
                "request_id": request_id,
                "user_id": user_id,
                "user_name": user_name,
                "user_role": user_role,
                "text": text[:2000],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            # Persist
            await db.chat_messages.insert_one(dict(msg))
            # Broadcast (without _id)
            await manager.broadcast(request_id, msg)
    except WebSocketDisconnect:
        manager.disconnect(request_id, websocket)
    except Exception as e:
        logger.error(f"WS error: {e}")
        manager.disconnect(request_id, websocket)


