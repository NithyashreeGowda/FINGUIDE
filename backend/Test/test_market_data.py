import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from rag.market_data import _build_yahoo_ticker, fetch_stock_quote


def test_manual_provider_returns_structured_unavailable_payload():
    result = fetch_stock_quote("RELIANCE", provider="manual")

    assert result["ticker"] == "RELIANCE"
    assert result["exchange"] == "NSE"
    assert result["status"] == "not_available"
    assert result["price"] is None
    assert result["provider"] == "manual"


def test_provider_lookup_respects_runtime_env(monkeypatch):
    monkeypatch.setenv("FINGUIDE_MARKET_DATA_PROVIDER", "manual")
    result = fetch_stock_quote("TCS")
    assert result["status"] == "not_available"
    assert result["provider"] == "manual"


def test_yahoo_ticker_conversion_uses_exchange_suffix():
    assert _build_yahoo_ticker("RELIANCE", "NSE") == "RELIANCE.NS"
    assert _build_yahoo_ticker("RELIANCE", "BSE") == "RELIANCE.BO"
