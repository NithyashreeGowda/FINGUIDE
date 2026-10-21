"""
market_news.py - Market News for FinGuide

How it works
  * A background thread refreshes news every RSS_INTERVAL_MIN minutes.
  * RSS feeds (Indian finance sites) are fetched every refresh.
  * Marketaux is fetched at most once per MX_INTERVAL_MIN minutes and never more
    than MX_DAILY_BUDGET requests per day (free plan = 100/day, 3 articles each).
  * Everything is saved in MongoDB (collection "news"). Users only ever read
    from MongoDB, so their traffic never touches the news APIs.
  * GET /api/news returns the last 48 hours. If nothing is that fresh
    (APIs down, weekend), it returns the last saved items with stale=true.

Needs:  pip install requests feedparser
.env:   MARKETAUX_API_KEY=...   (MONGODB_URI and MONGODB_DB already exist)
"""
import calendar
import hashlib
import html
import logging
import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import feedparser
import requests
from fastapi import APIRouter, Query
from pymongo import DESCENDING, MongoClient

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # .env is loaded elsewhere
    pass

log = logging.getLogger("finguide.news")
router = APIRouter(tags=["news"])

# ----------------------------------------------------------------- settings
RSS_INTERVAL_MIN = 15          # how often the worker wakes up
MX_INTERVAL_MIN = 60           # min gap between Marketaux fetches
MX_DAILY_BUDGET = 90           # stay under the 100/day free limit
KEEP_DAYS = 7                  # old items are deleted after this
WINDOW_HOURS = 48              # what users see by default

CATEGORIES = ["Markets", "Stocks", "Economy", "Commodities", "Crypto"]
REGIONS = ["India", "US", "Global"]

# Marketaux: one request per entry (3 articles each on the free plan)
MX_URL = "https://api.marketaux.com/v1/news/all"
MX_QUERIES = [
    {"region": "India", "params": {"countries": "in"}},
    {"region": "US", "params": {"countries": "us"}},
    {"region": "Global", "params": {"search": "stock market"}},
]

# Edit freely. A feed that fails is logged and skipped, it never breaks the rest.
RSS_FEEDS = [
    ("Economic Times", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
    ("Economic Times", "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms"),
    ("Moneycontrol", "https://www.moneycontrol.com/rss/marketreports.xml"),
    ("Moneycontrol", "https://www.moneycontrol.com/rss/business.xml"),
    ("Mint", "https://www.livemint.com/rss/markets"),
]

# ----------------------------------------------------------------- database
_client = None
_indexed = False


def _db():
    global _client, _indexed
    if _client is None:
        _client = MongoClient(os.getenv("MONGODB_URI"), serverSelectionTimeoutMS=5000)
    db = _client[os.getenv("MONGODB_DB", "finguide")]
    if not _indexed:
        db.news.create_index("uid", unique=True)
        db.news.create_index([("published_at", DESCENDING)])
        _indexed = True
    return db


def _now() -> datetime:
    """Naive UTC datetime (how we store dates in MongoDB)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ----------------------------------------------------------------- helpers
def _clean(text: Optional[str], limit: int = 220) -> str:
    text = re.sub(r"<[^>]+>", " ", html.unescape(text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "\u2026"


def _uid(title: str) -> str:
    """Same headline from two sources -> same id -> stored once."""
    key = re.sub(r"[^a-z0-9]", "", title.lower())
    return hashlib.sha1(key.encode()).hexdigest()


_CATEGORY_WORDS = [
    ("Crypto", ("bitcoin", "ethereum", "crypto", "blockchain", "token")),
    ("Commodities", ("gold", "silver", "crude", "brent", "oil price", "commodit", "natural gas")),
    ("Economy", ("rbi", "inflation", "gdp", "fed ", "federal reserve", "interest rate",
                 "repo rate", "budget", "tariff", "recession", "fiscal", "cpi", "economy")),
    ("Stocks", ("share", "stock", "sensex", "nifty", "ipo", "earnings", "results", "q1", "q2",
                "q3", "q4", "dividend", "target price", "buy", "sell")),
]


def _categorize(text: str) -> str:
    t = text.lower()
    for name, words in _CATEGORY_WORDS:
        if any(w in t for w in words):
            return name
    return "Markets"


def _sentiment_label(score: Optional[float]) -> Optional[str]:
    if score is None:
        return None
    if score > 0.15:
        return "positive"
    if score < -0.15:
        return "negative"
    return "neutral"


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


# ----------------------------------------------------------------- Marketaux
def _mx_item(a: dict, region: str) -> Optional[dict]:
    title = (a.get("title") or "").strip()
    url = a.get("url")
    published = _parse_iso(a.get("published_at"))
    if not title or not url or not published:
        return None
    entities = a.get("entities") or []
    scores = [e["sentiment_score"] for e in entities
              if isinstance(e.get("sentiment_score"), (int, float))]
    score = sum(scores) / len(scores) if scores else None
    summary = _clean(a.get("description") or a.get("snippet"))
    return {
        "uid": _uid(title),
        "title": _clean(title, 200),
        "summary": summary,
        "url": url,
        "source": a.get("source") or "Marketaux",
        "published_at": published,
        "category": _categorize(f"{title} {summary}"),
        "region": region,
        "tickers": [e["symbol"] for e in entities if e.get("symbol")][:3],
        "sentiment": _sentiment_label(score),
        "score": round(score, 2) if score is not None else None,
        "image": a.get("image_url") or None,
        "provider": "marketaux",
        "fetched_at": _now(),
    }


def _fetch_marketaux(db) -> int:
    key = os.getenv("MARKETAUX_API_KEY")
    if not key:
        log.warning("MARKETAUX_API_KEY missing - skipping Marketaux")
        return 0

    today = _now().strftime("%Y-%m-%d")
    meta = db.news_meta.find_one({"_id": "marketaux"}) or {}
    used = meta.get("used", 0) if meta.get("day") == today else 0
    last = meta.get("last_fetch")
    if last and _now() - last < timedelta(minutes=MX_INTERVAL_MIN):
        return 0
    if used + len(MX_QUERIES) > MX_DAILY_BUDGET:
        log.info("Marketaux daily budget reached (%s used)", used)
        return 0

    after = (_now() - timedelta(hours=WINDOW_HOURS)).strftime("%Y-%m-%dT%H:%M")
    items, calls = [], 0
    for q in MX_QUERIES:
        params = {"api_token": key, "language": "en", "limit": 3,
                  "published_after": after, **q["params"]}
        try:
            r = requests.get(MX_URL, params=params, timeout=12)
            calls += 1
            if r.status_code in (402, 429):   # quota / rate limit
                log.warning("Marketaux %s: %s", r.status_code, r.text[:120])
                break
            r.raise_for_status()
            for a in r.json().get("data", []):
                item = _mx_item(a, q["region"])
                if item:
                    items.append(item)
        except Exception as e:
            log.warning("Marketaux %s failed: %s", q["region"], e)

    db.news_meta.update_one(
        {"_id": "marketaux"},
        {"$set": {"day": today, "used": used + calls, "last_fetch": _now()}},
        upsert=True,
    )
    return _save(db, items)


# ----------------------------------------------------------------- RSS
def _rss_image(e) -> Optional[str]:
    for key in ("media_content", "media_thumbnail"):
        for m in e.get(key) or []:
            if m.get("url"):
                return m["url"]
    for l in e.get("links") or []:
        if str(l.get("type", "")).startswith("image") and l.get("href"):
            return l["href"]
    m = re.search(r'<img[^>]+src=["\']([^"\']+)', e.get("summary") or "")
    return m.group(1) if m else None


def _fetch_rss(db) -> int:
    items = []
    for source, url in RSS_FEEDS:
        try:
            r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0 FinGuide"})
            r.raise_for_status()
            feed = feedparser.parse(r.content)
        except Exception as e:
            log.warning("RSS %s failed: %s", url, e)
            continue
        for e in feed.entries:
            title = (e.get("title") or "").strip()
            link = e.get("link")
            if not title or not link:
                continue
            stamp = e.get("published_parsed") or e.get("updated_parsed")
            published = datetime.utcfromtimestamp(calendar.timegm(stamp)) if stamp else _now()
            summary = _clean(e.get("summary"))
            items.append({
                "uid": _uid(title),
                "title": _clean(title, 200),
                "summary": summary,
                "url": link,
                "source": source,
                "published_at": published,
                "category": _categorize(f"{title} {summary}"),
                "region": "India",
                "tickers": [],
                "sentiment": None,
                "score": None,
                "image": _rss_image(e),
                "provider": "rss",
                "fetched_at": _now(),
            })
    return _save(db, items)


# ----------------------------------------------------------------- storage
def _save(db, items: list) -> int:
    cutoff = _now() - timedelta(hours=WINDOW_HOURS)
    new = 0
    for it in items:
        if it["published_at"] < cutoff:
            continue
        doc = {k: v for k, v in it.items() if k != "uid"}
        res = db.news.update_one({"uid": it["uid"]}, {"$setOnInsert": doc}, upsert=True)
        if res.upserted_id:
            new += 1
        elif it.get("image"):  # older saved item without a picture: add it
            db.news.update_one({"uid": it["uid"], "image": None}, {"$set": {"image": it["image"]}})
    return new


_lock = threading.Lock()
_last_run = 0.0


def refresh_all() -> dict:
    """Fetch everything once. Safe to call from anywhere."""
    global _last_run
    if not _lock.acquire(blocking=False):
        return {"skipped": "refresh already running"}
    try:
        db = _db()
        result = {"rss": _fetch_rss(db), "marketaux": _fetch_marketaux(db)}
        db.news.delete_many({"published_at": {"$lt": _now() - timedelta(days=KEEP_DAYS)}})
        db.news_meta.update_one({"_id": "status"}, {"$set": {"updated_at": _now()}}, upsert=True)
        _last_run = time.time()
        log.info("News refresh: %s", result)
        return result
    finally:
        _lock.release()


_started = False


def start_news_worker():
    """Call once at app startup."""
    global _started
    if _started:
        return
    _started = True

    def loop():
        while True:
            try:
                refresh_all()
            except Exception:
                log.exception("News refresh failed")
            time.sleep(RSS_INTERVAL_MIN * 60)

    threading.Thread(target=loop, daemon=True, name="news-worker").start()


# ----------------------------------------------------------------- API
def _out(d: dict) -> dict:
    return {
        "id": d["uid"] if "uid" in d else str(d["_id"]),
        "title": d["title"],
        "summary": d.get("summary", ""),
        "url": d["url"],
        "source": d.get("source", ""),
        "published_at": d["published_at"].isoformat() + "Z",
        "category": d.get("category", "Markets"),
        "region": d.get("region", "Global"),
        "tickers": d.get("tickers", []),
        "sentiment": d.get("sentiment"),
        "image": d.get("image"),
    }


@router.get("/api/news")
def get_news(
    category: Optional[str] = None,
    region: Optional[str] = None,
    limit: int = Query(40, ge=1, le=100),
    hours: int = Query(WINDOW_HOURS, ge=1, le=72),
):
    db = _db()
    q: dict = {}
    cats = {c.lower(): c for c in CATEGORIES}
    regs = {r.lower(): r for r in REGIONS}
    if category and category.lower() in cats:
        q["category"] = cats[category.lower()]
    if region and region.lower() in regs:
        q["region"] = regs[region.lower()]

    fresh = {**q, "published_at": {"$gte": _now() - timedelta(hours=hours)}}
    docs = list(db.news.find(fresh).sort("published_at", DESCENDING).limit(limit))
    stale = False
    if not docs:  # last saved copy, so the page is never empty
        docs = list(db.news.find(q).sort("published_at", DESCENDING).limit(limit))
        stale = bool(docs)

    status = db.news_meta.find_one({"_id": "status"}) or {}
    updated = status.get("updated_at")
    return {
        "items": [_out(d) for d in docs],
        "count": len(docs),
        "stale": stale,
        "updated_at": updated.isoformat() + "Z" if updated else None,
    }


@router.post("/api/news/refresh")
def manual_refresh():
    """For testing. Limited to once a minute."""
    if time.time() - _last_run < 60:
        return {"skipped": "refreshed less than a minute ago"}
    return refresh_all()