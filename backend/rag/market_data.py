from __future__ import annotations

import json
import os
from typing import Any
from urllib import request, error


DEFAULT_PROVIDER = os.getenv("FINGUIDE_MARKET_DATA_PROVIDER", "manual")


class MarketDataUnavailable(RuntimeError):
    pass


def _normalize_provider(value: str | None) -> str:
    if value is None:
        return "manual"
    provider = str(value).strip().lower()
    aliases = {
        "manual": "manual",
        "none": "manual",
        "yahoo": "yahoo",
        "finance": "yahoo",
        "alphavantage": "alphavantage",
        "alpha_vantage": "alphavantage",
        "alpha": "alphavantage",
    }
    return aliases.get(provider, provider)


def _normalize_exchange(value: str | None) -> str:
    exchange = (value or "NSE").strip().upper()
    aliases = {"INDIA": "NSE", "BOM": "BSE", "BSEINDIA": "BSE"}
    return aliases.get(exchange, exchange)


def _build_yahoo_ticker(ticker: str, exchange: str) -> str:
    cleaned = ticker.strip().upper()
    if not cleaned:
        return ""
    if exchange == "NSE" and not cleaned.endswith(".NS"):
        return f"{cleaned}.NS"
    if exchange == "BSE" and not cleaned.endswith(".BO"):
        return f"{cleaned}.BO"
    return cleaned


def _fetch_json(url: str) -> dict[str, Any]:
    try:
        with request.urlopen(url, timeout=15) as response:
            payload = response.read()
        return json.loads(payload.decode("utf-8"))
    except (error.URLError, ValueError, TimeoutError, OSError) as exc:  # pragma: no cover - network-dependent
        raise MarketDataUnavailable(f"Could not fetch live market data from {url}: {exc}") from exc


def fetch_stock_quote(
    ticker: str,
    *,
    exchange: str | None = None,
    provider: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Return either a live quote when supported or a structured unavailable payload."""
    cleaned_ticker = (ticker or "").strip().upper()
    if not cleaned_ticker:
        raise ValueError("ticker cannot be empty.")

    selected_provider = _normalize_provider(
        provider or os.getenv("FINGUIDE_MARKET_DATA_PROVIDER") or DEFAULT_PROVIDER
    )
    selected_exchange = _normalize_exchange(
        exchange or os.getenv("FINGUIDE_MARKET_EXCHANGE") or "NSE"
    )
    selected_api_key = api_key or os.getenv("FINGUIDE_API_KEY") or os.getenv("ALPHA_VANTAGE_API_KEY")

    if selected_provider == "manual":
        return {
            "ticker": cleaned_ticker,
            "exchange": selected_exchange,
            "currency": "INR",
            "price": None,
            "timestamp": None,
            "provider": "manual",
            "status": "not_available",
            "reason": "No live market-data provider is configured.",
        }

    if selected_provider == "yahoo":
        yahoo_ticker = _build_yahoo_ticker(cleaned_ticker, selected_exchange)
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_ticker}?interval=1d&range=1d"
        try:
            payload = _fetch_json(url)
            chart = payload.get("chart", {}).get("result", [])
            if not chart:
                raise MarketDataUnavailable("Yahoo response did not include chart data.")
            meta = chart[0].get("meta", {})
            return {
                "ticker": cleaned_ticker,
                "exchange": selected_exchange,
                "currency": meta.get("currency") or "INR",
                "price": meta.get("regularMarketPrice"),
                "timestamp": meta.get("regularMarketTime"),
                "provider": "yahoo",
                "status": "ok",
            }
        except MarketDataUnavailable:
            return {
                "ticker": cleaned_ticker,
                "exchange": selected_exchange,
                "currency": "INR",
                "price": None,
                "timestamp": None,
                "provider": "yahoo",
                "status": "not_available",
                "reason": "Live market data could not be retrieved.",
            }

    if selected_provider == "alphavantage":
        if not selected_api_key:
            raise ValueError("ALPHA_VANTAGE_API_KEY must be set when using the alphavantage provider.")
        url = (
            f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={cleaned_ticker}"
            f"&apikey={selected_api_key}"
        )
        try:
            payload = _fetch_json(url)
            quote = payload.get("Global Quote", {})
            price = quote.get("05. price")
            if not price:
                raise MarketDataUnavailable("Alpha Vantage quote was missing the price field.")
            return {
                "ticker": cleaned_ticker,
                "exchange": selected_exchange,
                "currency": os.getenv("FINGUIDE_CURRENCY", "INR"),
                "price": float(price),
                "timestamp": quote.get("07. latest trading day"),
                "provider": "alphavantage",
                "status": "ok",
            }
        except MarketDataUnavailable:
            return {
                "ticker": cleaned_ticker,
                "exchange": selected_exchange,
                "currency": os.getenv("FINGUIDE_CURRENCY", "INR"),
                "price": None,
                "timestamp": None,
                "provider": "alphavantage",
                "status": "not_available",
                "reason": "Live market data could not be retrieved.",
            }

    raise ValueError(f"Unsupported market-data provider: {selected_provider}")
