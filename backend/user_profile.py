"""Create / read / update the signed-in user's financial profile.
Also holds the user's Settings (dark mode) and chat History (conversations)."""
from datetime import datetime, timezone
from typing import Literal, Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from auth import get_current_user
from context_validator import completeness, validate_context
from database import profiles, settings as settings_col, conversations as conv_col

router = APIRouter(prefix="/profile", tags=["profile"])

Risk = Literal["conservative", "moderate", "aggressive"]
Level = Literal["low", "medium", "high"]
Goal = Literal[
    "wealth_creation", "retirement", "capital_preservation",
    "regular_income", "major_purchase", "emergency_fund",
    "home_purchase", "education", "short_term_savings", "other",
]

FIELDS = [
    "age", "income", "monthly_expenses", "investment_amount", "investment_horizon",
    "financial_goal", "risk_preference", "risk_capacity", "existing_investments",
    "liquidity_requirement", "liabilities", "target_return_percent",
]


class ProfileIn(BaseModel):
    """Every field is optional so an incomplete profile can still be saved;
    the context validator then reports exactly what is missing."""
    age: Optional[int] = Field(None, ge=18, le=100)
    income: Optional[float] = Field(None, ge=0)              # monthly, INR
    monthly_expenses: Optional[float] = Field(None, ge=0)
    investment_amount: Optional[float] = Field(None, ge=0)
    investment_horizon: Optional[float] = Field(None, gt=0, le=50)  # years
    financial_goal: Optional[Goal] = None
    risk_preference: Optional[Risk] = None
    risk_capacity: Optional[Level] = None
    existing_investments: Optional[float] = Field(None, ge=0)  # current value, INR
    liquidity_requirement: Optional[Level] = None
    liabilities: Optional[float] = Field(None, ge=0)          # total outstanding, INR
    target_return_percent: Optional[float] = Field(None, ge=0, le=200)


def _response(doc: dict) -> dict:
    data = {f: doc.get(f) for f in FIELDS}
    return {
        "profile": {
            **data,
            "created_at": doc["created_at"].isoformat(),
            "updated_at": doc["updated_at"].isoformat(),
        },
        "completeness": completeness(data),
        "context": validate_context(data),
    }


@router.get("")
def get_profile(user: dict = Depends(get_current_user)):
    doc = profiles.find_one({"user_id": str(user["_id"])})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No profile yet")
    return _response(doc)


@router.post("", status_code=201)
def create_profile(body: ProfileIn, user: dict = Depends(get_current_user)):
    user_id = str(user["_id"])
    if profiles.find_one({"user_id": user_id}):
        raise HTTPException(status.HTTP_409_CONFLICT, "Profile already exists. Use PUT to update it.")
    now = datetime.now(timezone.utc)
    doc = {"user_id": user_id, **body.model_dump(), "created_at": now, "updated_at": now}
    profiles.insert_one(doc)
    return _response(doc)


@router.put("")
def update_profile(body: ProfileIn, user: dict = Depends(get_current_user)):
    user_id = str(user["_id"])
    now = datetime.now(timezone.utc)
    # Full replace of the form fields, so clearing a field in the UI really clears it.
    updated = profiles.find_one_and_update(
        {"user_id": user_id},
        {"$set": {**body.model_dump(), "updated_at": now}},
        return_document=True,
    )
    if not updated:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No profile yet. Create one first.")
    return _response(updated)


# =========================================================
# SETTINGS (dark mode) — saved per user in the "settings" collection
# =========================================================
settings_router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsIn(BaseModel):
    dark_mode: bool = False


@settings_router.get("")
def get_settings(user: dict = Depends(get_current_user)):
    doc = settings_col.find_one({"user_id": str(user["_id"])})
    
    return {"dark_mode": bool(doc and doc.get("dark_mode"))}


@settings_router.put("")
def save_settings(body: SettingsIn, user: dict = Depends(get_current_user)):
    settings_col.update_one(
        {"user_id": str(user["_id"])},
        {"$set": {"dark_mode": body.dark_mode, "updated_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    return {"dark_mode": body.dark_mode}


# =========================================================
# CONVERSATIONS (chat history) — saved in the "conversations" collection
# =========================================================
conv_router = APIRouter(prefix="/conversations", tags=["conversations"])


class MessageIn(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(min_length=1, max_length=4000)


class ConvCreateIn(BaseModel):
    message: MessageIn  # first message of the chat


class ConvRenameIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)


def _now():
    return datetime.now(timezone.utc)


def _owned(conv_id: str, user: dict) -> dict:
    """Find a conversation that belongs to the signed-in user, or 404."""
    try:
        doc = conv_col.find_one({"_id": ObjectId(conv_id), "user_id": str(user["_id"])})
    except InvalidId:
        doc = None
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return doc


def _summary(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "title": doc["title"],
        "created_at": doc["created_at"].isoformat(),
        "updated_at": doc["updated_at"].isoformat(),
        "message_count": len(doc["messages"]),
    }


def _full(doc: dict) -> dict:
    return {
        **_summary(doc),
        "messages": [
            {"role": m["role"], "text": m["text"], "at": m["at"].isoformat()}
            for m in doc["messages"]
        ],
    }


@conv_router.get("")
def list_conversations(user: dict = Depends(get_current_user)):
    docs = conv_col.find({"user_id": str(user["_id"])}).sort("updated_at", -1)
    return [_summary(d) for d in docs]


@conv_router.post("", status_code=201)
def create_conversation(body: ConvCreateIn, user: dict = Depends(get_current_user)):
    now = _now()
    doc = {
        "user_id": str(user["_id"]),
        "user_email": user["email"],
        "title": body.message.text[:60],
        "messages": [{**body.message.model_dump(), "at": now}],
        "created_at": now,
        "updated_at": now,
    }
    doc["_id"] = conv_col.insert_one(doc).inserted_id
    return _full(doc)


@conv_router.get("/{conv_id}")
def get_conversation(conv_id: str, user: dict = Depends(get_current_user)):
    return _full(_owned(conv_id, user))


@conv_router.post("/{conv_id}/messages")
def add_message(conv_id: str, body: MessageIn, user: dict = Depends(get_current_user)):
    _owned(conv_id, user)
    now = _now()
    updated = conv_col.find_one_and_update(
        {"_id": ObjectId(conv_id)},
        {"$push": {"messages": {**body.model_dump(), "at": now}}, "$set": {"updated_at": now}},
        return_document=True,
    )
    return _full(updated)


@conv_router.put("/{conv_id}")
def rename_conversation(conv_id: str, body: ConvRenameIn, user: dict = Depends(get_current_user)):
    _owned(conv_id, user)
    updated = conv_col.find_one_and_update(
        {"_id": ObjectId(conv_id)},
        {"$set": {"title": body.title.strip()}},
        return_document=True,
    )
    return _summary(updated)


@conv_router.delete("/{conv_id}")
def delete_conversation(conv_id: str, user: dict = Depends(get_current_user)):
    _owned(conv_id, user)
    conv_col.delete_one({"_id": ObjectId(conv_id)})
    return {"ok": True}