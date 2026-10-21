"""FinGuide history features: summaries, knowledge map, and exports."""

from collections import Counter
from datetime import datetime, timezone
from io import BytesIO
from typing import Optional
import json
import re

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

from auth import get_current_user
from database import conversations as conv_col


router = APIRouter(
    prefix="/history-tools",
    tags=["history tools"],
)


# ---------------------------------------------------------
# FINANCIAL TOPIC KEYWORDS
# ---------------------------------------------------------

TOPIC_KEYWORDS = {
    "Budgeting": (
        "budget", "monthly expenses", "spending", "cash flow",
    ),
    "Saving": (
        "saving", "savings", "emergency fund", "deposit",
    ),
    "Investing basics": (
        "invest", "investment", "portfolio", "asset allocation",
    ),
    "Stocks": (
        "stock", "shares", "equity", "nifty", "sensex", "nasdaq",
    ),
    "Mutual funds": (
        "mutual fund", "sip", "systematic investment", "nav",
        "fund manager",
    ),
    "Risk management": (
        "risk", "volatility", "diversification", "drawdown",
    ),
    "Retirement": (
        "retirement", "pension", "provident fund", "epf", "nps",
    ),
    "Tax": (
        "tax", "income tax", "capital gains", "deduction", "itr",
    ),
    "Debt & loans": (
        "loan", "debt", "emi", "interest rate", "credit score",
    ),
    "Insurance": (
        "insurance", "premium", "health cover", "term plan",
    ),
    "Real estate": (
        "real estate", "property", "home loan", "housing",
    ),
    "Financial goals": (
        "financial goal", "wealth creation", "long term", "short term",
    ),
    "Market news": (
        "market news", "headline", "market trend", "sentiment",
        "company analysis",
    ),
}


# ---------------------------------------------------------
# REQUEST MODELS
# ---------------------------------------------------------

class SummaryIn(BaseModel):
    key_takeaways: list[str] = Field(default_factory=list, max_length=12)
    decisions: list[str] = Field(default_factory=list, max_length=12)
    follow_up_topics: list[str] = Field(default_factory=list, max_length=12)
    generated_at: Optional[str] = None


# ---------------------------------------------------------
# GENERAL HELPERS
# ---------------------------------------------------------

def _now():
    return datetime.now(timezone.utc)


def _to_iso(value):
    """Safely convert a datetime or other value to a string."""
    if value is None:
        return None

    if hasattr(value, "isoformat"):
        return value.isoformat()

    return str(value)


def _owned(conv_id: str, user: dict) -> dict:
    """Return a conversation only if it belongs to the logged-in user."""
    try:
        oid = ObjectId(conv_id)
    except (InvalidId, TypeError):
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    user_id = str(user.get("_id", ""))

    doc = conv_col.find_one({
        "_id": oid,
        "user_id": user_id,
    })

    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    return doc


def _text(doc: dict) -> str:
    """Convert saved messages into searchable text."""
    parts = []

    for message in doc.get("messages", []):
        role = str(message.get("role", "unknown"))
        message_text = str(message.get("text", "") or "")
        parts.append(f"{role}: {message_text}")

    return "\n".join(parts)


def _sentences(text: str) -> list[str]:
    """Split text into unique sentence-like pieces."""
    parts = re.split(r"(?<=[.!?])\s+|\n+", text or "")
    seen = set()
    result = []

    for part in parts:
        cleaned = re.sub(
            r"^(user|assistant)\s*:\s*",
            "",
            part.strip(),
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"\s+", " ", cleaned)

        if len(cleaned) < 24:
            continue

        key = cleaned.lower()

        if key not in seen:
            seen.add(key)
            result.append(cleaned[:420])

    return result


# ---------------------------------------------------------
# SMART SUMMARY
# ---------------------------------------------------------

def _make_summary(doc: dict) -> dict:
    """Create a summary from the saved conversation messages."""
    messages = doc.get("messages", [])

    user_text = " ".join(
        str(message.get("text", "") or "")
        for message in messages
        if message.get("role") == "user"
    )

    all_text = _text(doc)
    sentences = _sentences(all_text)

    important_words = (
        "decided", "choose", "should", "must", "important",
        "because", "next", "implement", "use ", "avoid",
        "recommend", "goal", "risk", "budget", "invest",
    )

    ranked = sorted(
        enumerate(sentences),
        key=lambda pair: (
            sum(
                word in pair[1].lower()
                for word in important_words
            ),
            min(len(pair[1]), 240),
            -pair[0],
        ),
        reverse=True,
    )

    takeaways = [
        sentence for _, sentence in ranked[:5]
    ]

    if not takeaways:
        takeaways = [
            str(message.get("text", ""))[:420]
            for message in messages[:3]
            if message.get("text")
        ]

    decision_markers = (
        "decided to",
        "we'll use",
        "we will use",
        "use ",
        "chosen",
        "choose",
        "will implement",
        "agreed",
    )

    decisions = []

    for sentence in sentences:
        lowered = sentence.lower()

        if (
            any(marker in lowered for marker in decision_markers)
            and sentence not in decisions
        ):
            decisions.append(sentence)

        if len(decisions) >= 4:
            break

    combined_text = (user_text + " " + all_text).lower()

    found_topics = [
        topic
        for topic, keywords in TOPIC_KEYWORDS.items()
        if any(keyword in combined_text for keyword in keywords)
    ]

    followups = found_topics[:5]

    if not followups:
        followups = [
            "Review the conversation for unresolved questions."
        ]

    return {
        "key_takeaways": takeaways[:5],
        "decisions": decisions,
        "follow_up_topics": followups,
        "generated_at": _now().isoformat(),
        "method": "built-in extractive summary",
    }


@router.get("/summary/{conv_id}")
def get_summary(
    conv_id: str,
    user: dict = Depends(get_current_user),
):
    doc = _owned(conv_id, user)
    saved = doc.get("smart_summary")

    return {
        "conversation_id": conv_id,
        "summary": saved or _make_summary(doc),
        "saved": bool(saved),
    }


@router.put("/summary/{conv_id}")
def save_summary(
    conv_id: str,
    body: SummaryIn,
    user: dict = Depends(get_current_user),
):
    _owned(conv_id, user)

    # model_dump() is for Pydantic v2; dict() supports v1.
    if hasattr(body, "model_dump"):
        summary = body.model_dump()
    else:
        summary = body.dict()

    summary["generated_at"] = (
        summary.get("generated_at") or _now().isoformat()
    )

    conv_col.update_one(
        {
            "_id": ObjectId(conv_id),
            "user_id": str(user.get("_id", "")),
        },
        {
            "$set": {
                "smart_summary": summary,
                "updated_at": _now(),
            }
        },
    )

    return {
        "conversation_id": conv_id,
        "summary": summary,
        "saved": True,
    }
# ---------------------------------------------------------
# ROW PREVIEWS
# ---------------------------------------------------------

def _preview(doc: dict, limit: int = 110) -> str:
    """One short line: the latest assistant reply, else the last message."""
    messages = doc.get("messages") or []
    pick = next(
        (m for m in reversed(messages) if m.get("role") != "user" and m.get("text")),
        None,
    ) or (messages[-1] if messages else None)

    text = re.sub(r"\s+", " ", str((pick or {}).get("text", "") or "")).strip()
    return text if len(text) <= limit else text[:limit].rstrip() + "…"


@router.get("/previews")
def previews(user: dict = Depends(get_current_user)):
    user_id = str(user.get("_id", ""))

    docs = conv_col.find(
        {"user_id": user_id},
        {"messages": {"$slice": -2}},  # only the last two messages
    )

    return {"previews": {str(doc["_id"]): _preview(doc) for doc in docs}}

# ---------------------------------------------------------
# FINANCIAL KNOWLEDGE MAP
# ---------------------------------------------------------

@router.get("/knowledge-map")
def knowledge_map(
    user: dict = Depends(get_current_user),
):
    user_id = str(user.get("_id", ""))

    docs = list(
        conv_col.find({"user_id": user_id})
    )

    topic_ids = {}

    for doc in docs:
        conversation_text = _text(doc).lower()

        for topic, keywords in TOPIC_KEYWORDS.items():
            if any(keyword in conversation_text for keyword in keywords):
                topic_ids.setdefault(topic, []).append(
                    str(doc["_id"])
                )

    topics = [
        {
            "name": topic,
            "count": len(ids),
            "conversation_ids": ids,
        }
        for topic, ids in sorted(
            topic_ids.items(),
            key=lambda item: (-len(item[1]), item[0]),
        )
    ]

    topic_pairs = Counter()

    for doc in docs:
        conversation_text = _text(doc).lower()

        matched_topics = [
            topic
            for topic, keywords in TOPIC_KEYWORDS.items()
            if any(
                keyword in conversation_text
                for keyword in keywords
            )
        ]

        for index, left in enumerate(matched_topics):
            for right in matched_topics[index + 1:]:
                topic_pairs[tuple(sorted((left, right)))] += 1

    links = [
        {
            "source": left,
            "target": right,
            "count": count,
        }
        for (left, right), count in topic_pairs.most_common(12)
    ]

    return {
        "topics": topics,
        "links": links,
        "conversation_count": len(docs),
    }


# ---------------------------------------------------------
# PDF TEXT HELPERS
# ---------------------------------------------------------

def make_pdf_safe(value, max_chunk=25):
    """
    Replace unsupported characters and break very long words/tokens.
    This prevents FPDF from failing when a line has no breakable spaces.
    """
    text = str(value or "")
    text = text.encode("latin-1", errors="replace").decode("latin-1")

    return re.sub(
        rf"\S{{{max_chunk},}}",
        lambda match: "\n".join(
            match.group(0)[index:index + max_chunk]
            for index in range(0, len(match.group(0)), max_chunk)
        ),
        text,
    )


# ---------------------------------------------------------
# EXPORT CENTER: PDF / TXT / JSON
# ---------------------------------------------------------

@router.get("/export")
def export_history(
    scope: str = Query(
        "all",
        pattern="^(all|selected|summaries)$",
    ),
    format: str = Query(
        "pdf",
        pattern="^(pdf|txt|json)$",
    ),
    conversation_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    user_id = str(user.get("_id", ""))

    # Fetch only the logged-in user's conversations.
    if scope == "selected":
        if not conversation_id:
            raise HTTPException(
                status_code=400,
                detail=(
                    "conversation_id is required "
                    "for selected export"
                ),
            )

        docs = [_owned(conversation_id, user)]

    else:
        docs = list(
            conv_col.find({"user_id": user_id}).sort("updated_at", -1)
        )

    records = []

    for doc in docs:
        record = {
            "id": str(doc["_id"]),
            "title": doc.get("title") or "Untitled conversation",
            "created_at": _to_iso(doc.get("created_at")),
            "updated_at": _to_iso(doc.get("updated_at")),
        }

        if scope == "summaries":
            summary = doc.get("smart_summary")

            if summary:
                record["summary"] = summary

        else:
            record["messages"] = [
                {
                    "role": message.get("role", "unknown"),
                    "text": message.get("text", "") or "",
                    "at": _to_iso(message.get("at")),
                }
                for message in doc.get("messages", [])
            ]

            if doc.get("smart_summary"):
                record["summary"] = doc["smart_summary"]

        records.append(record)

    # Summaries-only export includes conversations with saved summaries.
    if scope == "summaries":
        records = [
            record for record in records
            if "summary" in record
        ]

    filename = f"finguide-{scope}-history.{format}"

    # -----------------------------------------------------
    # JSON EXPORT
    # -----------------------------------------------------
    if format == "json":
        content = {
            "scope": scope,
            "count": len(records),
            "items": records,
        }

        return JSONResponse(
            content=json.loads(json.dumps(content, default=str)),
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{filename}"'
                )
            },
        )

    # -----------------------------------------------------
    # TXT EXPORT
    # -----------------------------------------------------
    if format == "txt":
        chunks = []

        for item in records:
            chunks.append(
                f"# {item['title']}\n"
                f"Created: {item.get('created_at') or 'unknown'}"
            )

            if "summary" in item:
                summary = item["summary"]

                chunks.extend([
                    "",
                    "SMART SUMMARY",
                    "Key takeaways:",
                    *[
                        f"- {value}"
                        for value in summary.get("key_takeaways", [])
                    ],
                    "Decisions:",
                    *[
                        f"- {value}"
                        for value in summary.get("decisions", [])
                    ],
                    "Follow-up topics:",
                    *[
                        f"- {value}"
                        for value in summary.get("follow_up_topics", [])
                    ],
                ])

            for message in item.get("messages", []):
                chunks.append(
                    f"\n[{str(message.get('role', 'unknown')).upper()}] "
                    f"{message.get('at') or ''}\n"
                    f"{message.get('text', '')}"
                )

            chunks.append("\n" + "-" * 60)

        text_content = (
            "\n".join(chunks)
            if chunks
            else "No saved summaries or conversations found."
        )

        return PlainTextResponse(
            text_content,
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{filename}"'
                )
            },
        )

    # -----------------------------------------------------
    # PDF EXPORT — FIXED FOR LONG TEXT
    # -----------------------------------------------------
    try:
        from fpdf import FPDF
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="PDF export dependency missing. Run: pip install fpdf2",
        )

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    def write_pdf_text(value, height=5, size=9, bold=False):
        """Write safe text using the full available page width."""
        pdf.set_font("Helvetica", "B" if bold else "", size)
        pdf.set_x(pdf.l_margin)

        safe_text = make_pdf_safe(value)

        if not safe_text:
            safe_text = " "

        pdf.multi_cell(
            pdf.epw,
            height,
            safe_text,
        )

    write_pdf_text(
        "FinGuide Conversation Export",
        height=11,
        size=18,
        bold=True,
    )

    write_pdf_text(
        f"Export type: {scope} | Conversations: {len(records)}",
        height=6,
        size=9,
    )

    if not records:
        pdf.ln(4)
        write_pdf_text("No conversations or summaries found.")

    for item in records:
        pdf.ln(3)

        write_pdf_text(
            item.get("title", "Untitled conversation"),
            height=8,
            size=13,
            bold=True,
        )

        write_pdf_text(
            f"Created: {item.get('created_at') or 'unknown'}",
            height=5,
        )

        if "summary" in item:
            summary = item["summary"] or {}

            for heading, key in (
                ("Key takeaways", "key_takeaways"),
                ("Decisions", "decisions"),
                ("Follow-up topics", "follow_up_topics"),
            ):
                pdf.ln(1)

                write_pdf_text(
                    heading,
                    height=6,
                    size=11,
                    bold=True,
                )

                values = summary.get(key, [])

                if not values:
                    write_pdf_text("- None recorded", height=5)
                else:
                    for value in values:
                        write_pdf_text(f"- {value}", height=5)

        for message in item.get("messages", []):
            pdf.ln(1)

            role = str(
                message.get("role", "unknown")
            ).upper()

            write_pdf_text(
                role,
                height=5,
                size=9,
                bold=True,
            )

            write_pdf_text(
                message.get("text", ""),
                height=5,
                size=9,
            )

    output = pdf.output()

    # fpdf2 returns bytearray; this converts it safely to bytes.
    raw = bytes(output)

    return StreamingResponse(
        BytesIO(raw),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            )
        },
    )