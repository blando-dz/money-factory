"""
Polymarket CLOB client — queries real-time market data from Polymarket's public APIs.
Read-only, no authentication required.
"""
import json
import logging
import urllib.request
from typing import Any

from dotenv import load_dotenv

load_dotenv(r"C:\Users\Ghost\.env")

logger = logging.getLogger(__name__)

GAMMA_API = "https://gamma-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"


def search_markets(query: str, limit: int = 5) -> dict[str, Any]:
    """Search Polymarket markets using the Gamma API."""
    try:
        url = f"{GAMMA_API}/events?search={query}&limit={limit}&active=true"
        req = urllib.request.Request(url, headers={"User-Agent": "money-factory/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            events = data if isinstance(data, list) else data.get("data", [])
            return {"markets": events}
    except Exception as e:
        logger.warning(f"Polymarket Gamma search failed: {e}")
        return {"markets": []}


def get_market_prices(market_id: str) -> dict[str, Any]:
    """Get current prices for a specific market."""
    try:
        url = f"{CLOB_API}/markets/{market_id}"
        req = urllib.request.Request(url, headers={"User-Agent": "money-factory/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        logger.warning(f"Failed to get market prices: {e}")
        return {}


def get_price_history(market_id: str) -> list[dict]:
    """Get price history for a market."""
    try:
        url = f"{CLOB_API}/price-history?market={market_id}"
        req = urllib.request.Request(url, headers={"User-Agent": "money-factory/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning(f"Failed to get price history: {e}")
        return []
