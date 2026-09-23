"""Lead Credits participation debit — shared by Marketplace submit_offer (D2).

Not a new engine: atomic $gte+$inc, same-event 45 RON fallback, technical refund only.
"""
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException
from pymongo import ReturnDocument

from db import db

LEAD_CREDIT_COST = 45
LEAD_FEE_RON = 45.0
INSUFFICIENT_MSG = "Sold insuficient. Ai nevoie de 45 Lead Credits sau 45 RON în portofel."


async def debit_participation(uid: ObjectId) -> dict:
    """Debit 45 Lead Credits, else 45 RON. Never both. Never negative."""
    after_credit = await db.users.find_one_and_update(
        {"_id": uid, "lead_credits": {"$gte": LEAD_CREDIT_COST}},
        {"$inc": {"lead_credits": -LEAD_CREDIT_COST}},
        return_document=ReturnDocument.AFTER,
    )
    if after_credit:
        return {
            "payment": "credit",
            "remaining_credits": int(after_credit.get("lead_credits") or 0),
            "wallet_after": float(after_credit.get("wallet_balance") or 0),
            "monetary_fee": 0.0,
        }
    after_wallet = await db.users.find_one_and_update(
        {"_id": uid, "wallet_balance": {"$gte": LEAD_FEE_RON}},
        {"$inc": {"wallet_balance": -LEAD_FEE_RON}},
        return_document=ReturnDocument.AFTER,
    )
    if after_wallet:
        return {
            "payment": "wallet",
            "remaining_credits": int(after_wallet.get("lead_credits") or 0),
            "wallet_after": float(after_wallet.get("wallet_balance") or 0),
            "monetary_fee": LEAD_FEE_RON,
        }
    raise HTTPException(400, INSUFFICIENT_MSG)


async def refund_participation(uid: ObjectId, payment: str) -> None:
    """Reverse a debit after a technical / concurrency failure. Not used on lose/withdraw."""
    if payment == "credit":
        await db.users.update_one({"_id": uid}, {"$inc": {"lead_credits": LEAD_CREDIT_COST}})
    elif payment == "wallet":
        await db.users.update_one({"_id": uid}, {"$inc": {"wallet_balance": LEAD_FEE_RON}})


async def write_participation_ledger(
    user_id: str,
    request_id: str,
    debit: dict,
    offer_id: str | None = None,
) -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    if debit["payment"] == "credit":
        doc = {
            "user_id": user_id,
            "type": "lead_credit",
            "amount": -LEAD_CREDIT_COST,
            "currency": "lead_credits",
            "request_id": request_id,
            "remaining": debit["remaining_credits"],
            "created_at": now_iso,
        }
        if offer_id:
            doc["offer_id"] = offer_id
        await db.transactions.insert_one(doc)
    elif debit["payment"] == "wallet":
        doc = {
            "user_id": user_id,
            "type": "lead_fee",
            "amount": -LEAD_FEE_RON,
            "currency": "RON",
            "request_id": request_id,
            "created_at": now_iso,
        }
        if offer_id:
            doc["offer_id"] = offer_id
        await db.transactions.insert_one(doc)


def paid_with_label(debit: dict) -> str:
    return "lead_credit" if debit["payment"] == "credit" else "wallet"
