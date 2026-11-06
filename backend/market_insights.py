"""
market_insights.py - Market Insights for FinGuide
Yahoo Finance (direct chart endpoint, yfinance as fallback), cached in MongoDB.
Every symbol keeps its last good price, so the page never goes blank.
Also returns sparkline history, market open/closed status and market breadth.
Data is delayed and unofficial: for research and education only.
"""
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from urllib.parse import quote

import requests
from fastapi import APIRouter

from market_news import _db, _now  # same MongoDB helper as the news module

try:
    import yfinance as yf
except ImportError:  # optional
    yf = None

log = logging.getLogger("finguide.insights")
router = APIRouter(tags=["insights"])

REFRESH_MIN = 10    # worker interval
STALE_MIN = 45      # a symbol not refreshed for this long is flagged "stale"
OPEN_LAG_MIN = 30   # a market counts as open if its last trade is newer than this
SPARK_POINTS = 22
HERO_SYMS = ["^NSEI", "^BSESN", "^NSEBANK", "^GSPC", "^IXIC"]  # get chart history + range stats

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{}"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FinGuide/1.0"}

INDICES = [
    ("Nifty 50", "^NSEI", "India"),
    ("Sensex", "^BSESN", "India"),
    ("Bank Nifty", "^NSEBANK", "India"),
    ("India VIX", "^INDIAVIX", "India"),
    ("S&P 500", "^GSPC", "US"),
    ("Nasdaq", "^IXIC", "US"),
    ("Dow Jones", "^DJI", "US"),
]
OTHER = [
    ("USD/INR", "USDINR=X", "\u20b9 per $"),
    ("Gold", "GC=F", "USD/oz"),
    ("Crude Oil", "CL=F", "USD/bbl"),
    ("Bitcoin", "BTC-USD", "USD"),
]
SECTORS = [
    ("IT", "^CNXIT"), ("Bank", "^NSEBANK"), ("Auto", "^CNXAUTO"),
    ("Pharma", "^CNXPHARMA"), ("FMCG", "^CNXFMCG"), ("Metal", "^CNXMETAL"),
    ("Energy", "^CNXENERGY"), ("Realty", "^CNXREALTY"),
]
STOCKS = [
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "BHARTIARTL", "ITC", "SBIN",
    "LT", "KOTAKBANK", "HINDUNILVR", "AXISBANK", "BAJFINANCE", "MARUTI", "SUNPHARMA",
    "ASIANPAINT", "TITAN", "ULTRACEMCO", "NTPC", "ONGC", "M&M", "POWERGRID",
    "TATASTEEL", "WIPRO", "HCLTECH", "ADANIENT", "ADANIPORTS", "JSWSTEEL", "COALINDIA",
    "BAJAJFINSV", "NESTLEIND", "TECHM", "INDUSINDBK", "GRASIM", "CIPLA", "DRREDDY",
    "EICHERMOT", "HEROMOTOCO", "BPCL", "BRITANNIA", "APOLLOHOSP", "HINDALCO",
    "SBILIFE", "HDFCLIFE", "TATACONSUM", "BAJAJ-AUTO", "SHRIRAMFIN", "TRENT",
    "ETERNAL", "JIOFIN",
]


def _all_symbols() -> list:
    syms = (
        [s for _, s, _ in INDICES] + [s for _, s, _ in OTHER]
        + [s for _, s in SECTORS] + [f"{t}.NS" for t in STOCKS]
    )
    return list(dict.fromkeys(syms))


def _mk(price, prev, spark=None, t=None, sess=None, extra=None) -> Optional[dict]:
    if not prev:
        return None
    out = {
        "price": round(price, 2),
        "change": round(price - prev, 2),
        "pct": round((price - prev) / prev * 100, 2),
    }
    if spark:
        out["spark"] = spark
    if t:
        out["t"] = int(t)
    if sess:
        out["sess"] = sess
    if extra:
        out.update({k: v for k, v in extra.items() if v is not None})
    return out


def _f(v):
    try:
        return round(float(v), 2) if v is not None else None
    except (TypeError, ValueError):
        return None


def _chart_quote(sym: str) -> Optional[dict]:
    """Method 1: Yahoo chart endpoint. Last two daily closes + a month of closes for the sparkline."""
    for attempt in range(2):
        try:
            r = requests.get(
                CHART_URL.format(quote(sym, safe="^=")),
                params={"range": "1mo", "interval": "1d"},
                headers=HEADERS, timeout=10,
            )
            if r.status_code == 429:
                time.sleep(1.5 * (attempt + 1))
                continue
            r.raise_for_status()
            res = r.json()["chart"]["result"][0]
            raw = res["indicators"]["quote"][0]["close"]
            pairs = [(ts, c) for ts, c in zip(res.get("timestamp") or [], raw) if c is not None]
            closes = [c for _, c in pairs] if pairs else [c for c in raw if c is not None]
            if len(closes) < 2:
                return None
            meta = res.get("meta") or {}
            extra = {
                "dh": _f(meta.get("regularMarketDayHigh")), "dl": _f(meta.get("regularMarketDayLow")),
                "h52": _f(meta.get("fiftyTwoWeekHigh")), "l52": _f(meta.get("fiftyTwoWeekLow")),
            }
            if sym in HERO_SYMS and pairs:
                extra["hist"] = [[int(ts), round(float(c), 2)] for ts, c in pairs]
            reg = (meta.get("currentTradingPeriod") or {}).get("regular") or {}
            sess = [reg["start"], reg["end"]] if reg.get("start") and reg.get("end") else None
            return _mk(
                float(closes[-1]), float(closes[-2]),
                spark=[round(float(c), 2) for c in closes[-SPARK_POINTS:]],
                t=meta.get("regularMarketTime"), sess=sess, extra=extra,
            )
        except Exception:
            time.sleep(0.4)
    return None


def _from_chart(symbols: list) -> dict:
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(_chart_quote, symbols))
    return {s: q for s, q in zip(symbols, results) if q}


def _from_yfinance(symbols: list) -> dict:
    """Method 2 (fallback): the yfinance library, one batch call."""
    out = {}
    if yf is None or not symbols:
        return out
    try:
        df = yf.download(
            symbols, period="1mo", interval="1d", group_by="ticker",
            auto_adjust=False, progress=False, threads=True,
        )
    except Exception as e:
        log.warning("yfinance fallback failed: %s", e)
        return out
    for sym in symbols:
        try:
            s = df[sym]["Close"].dropna()
            if len(s) >= 2:
                spark = [round(float(c), 2) for c in s.tail(SPARK_POINTS)]
                q = _mk(float(s.iloc[-1]), float(s.iloc[-2]), spark=spark)
                if q:
                    out[sym] = q
        except Exception:
            continue
    return out


_lock = threading.Lock()
_last_run = 0.0


def refresh_insights() -> dict:
    global _last_run
    if not _lock.acquire(blocking=False):
        return {"skipped": "refresh already running"}
    try:
        symbols = _all_symbols()
        fresh = _from_chart(symbols)
        missing = [s for s in symbols if s not in fresh]
        if missing:
            fresh.update(_from_yfinance(missing))

        db = _db()
        old = db.insights.find_one({"_id": "snapshot"}) or {}
        now = _now()

        if not fresh:
            log.warning("Insights refresh got no data - keeping saved snapshot")
            db.insights.update_one(
                {"_id": "snapshot"}, {"$set": {"last_attempt": now, "last_ok": 0}}, upsert=True
            )
            return {"updated": 0, "kept_saved": len(old.get("quotes", []))}

        merged = {q["symbol"]: q for q in old.get("quotes", [])}  # last known good
        for sym, q in fresh.items():
            merged[sym] = {"symbol": sym, **q, "as_of": now}

        db.insights.replace_one(
            {"_id": "snapshot"},
            {"quotes": list(merged.values()), "updated_at": now, "last_attempt": now,
             "last_ok": len(fresh), "total": len(symbols)},
            upsert=True,
        )
        _last_run = time.time()
        log.info("Insights refresh: %s/%s symbols", len(fresh), len(symbols))
        return {"updated": len(fresh), "total": len(symbols), "failed": len(symbols) - len(fresh)}
    finally:
        _lock.release()


_started = False


def start_insights_worker():
    """Call once at app startup."""
    global _started
    if _started:
        return
    _started = True

    def loop():
        while True:
            try:
                refresh_insights()
            except Exception:
                log.exception("Insights refresh failed")
            time.sleep(REFRESH_MIN * 60)

    threading.Thread(target=loop, daemon=True, name="insights-worker").start()


# ---------------------------------------------------------------- API
def _pub(item: dict, spark: bool = False) -> dict:
    out = {k: item[k] for k in ("price", "change", "pct", "stale")}
    if spark:
        for k in ("spark", "hist", "dh", "dl", "h52", "l52"):
            if item.get(k) is not None:
                out[k] = item[k]
    return out


def _is_open(item: Optional[dict]) -> bool:
    """Open = inside the regular session AND the last trade is recent (so holidays read closed)."""
    if not item or not item.get("t") or not item.get("sess"):
        return False
    now = time.time()
    start, end = item["sess"]
    return start <= now < end and (now - item["t"]) < OPEN_LAG_MIN * 60


def _sections(q: dict) -> dict:
    indices = [{"name": n, "symbol": s, "region": r, **_pub(q[s], True)} for n, s, r in INDICES if s in q]
    other = [{"name": n, "symbol": s, "unit": u, **_pub(q[s], True)} for n, s, u in OTHER if s in q]
    sectors = sorted(
        ({"name": n, "symbol": s, **_pub(q[s])} for n, s in SECTORS if s in q),
        key=lambda x: x["pct"], reverse=True,
    )
    stocks = [{"name": t, "symbol": f"{t}.NS", **_pub(q[f"{t}.NS"])} for t in STOCKS if f"{t}.NS" in q]
    stocks.sort(key=lambda x: x["pct"], reverse=True)
    return {
        "indices": indices,
        "other": other,
        "sectors": sectors,
        "gainers": [s for s in stocks[:5] if s["pct"] > 0],
        "losers": [s for s in reversed(stocks[-5:]) if s["pct"] < 0],
        "breadth": {
            "advancing": sum(1 for s in stocks if s["pct"] > 0),
            "declining": sum(1 for s in stocks if s["pct"] < 0),
            "unchanged": sum(1 for s in stocks if s["pct"] == 0),
            "total": len(stocks),
        },
        "market": {
            "india_open": _is_open(q.get("^NSEI")), "us_open": _is_open(q.get("^GSPC")),
            "india_t": (q.get("^NSEI") or {}).get("t"), "us_t": (q.get("^GSPC") or {}).get("t"),
        },
    }


@router.get("/api/insights")
def get_insights():
    snap = _db().insights.find_one({"_id": "snapshot"})
    if not snap or not snap.get("quotes"):
        threading.Thread(target=refresh_insights, daemon=True).start()
        return {"ready": False}

    now = _now()
    q = {}
    for item in snap["quotes"]:
        age = (now - item["as_of"]).total_seconds() / 60
        data = {k: v for k, v in item.items() if k not in ("symbol", "as_of")}
        data["stale"] = age > STALE_MIN
        q[item["symbol"]] = data
    age_min = round((now - snap["updated_at"]).total_seconds() / 60)
    out = _sections(q)
    out.update({
        "ready": True,
        "updated_at": snap["updated_at"].isoformat() + "Z",
        "age_min": age_min,
        "status": "ok" if age_min <= REFRESH_MIN * 3 else "saved",
    })
    return out


@router.post("/api/insights/refresh")
def manual_refresh():
    """For testing. Limited to once a minute."""
    if time.time() - _last_run < 60:
        return {"skipped": "refreshed less than a minute ago"}
    return refresh_insights()