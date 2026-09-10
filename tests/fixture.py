#!/usr/bin/env python3
"""
Fixture-derived test anchors.

Single source of truth for every Python test assertion. Tests must not
hardcode fixture values; they import constants from this module instead.

If a fixture value changes and an anchor disappears, this module raises a
clear error at import time. If a test hardcodes a value the fixture no
longer contains, the drift will not be caught here — the test will fail
later with a confusing message. Do not hardcode. Import from here.

Usage:
    from tests.fixture import TESTA, NEWTICK, MULTI, DUP_US, DUP_UK, ETFSYN
    assert registry.by_isin(TESTA["isin"])["ticker"] == TESTA["ticker"]

Regenerate the underlying fixture with:
    python3 tools/gen_test_fixture.py
"""

import json
from pathlib import Path
from typing import Any, Dict, List

# ─── Fixture location ────────────────────────────────────────────────

FIXTURE_PATH: Path = Path(__file__).parent / "fixtures" / "identifiers.test.json"


# ─── Loading ─────────────────────────────────────────────────────────

def _load() -> Dict[str, Any]:
    if not FIXTURE_PATH.exists():
        raise FileNotFoundError(
            f"Fixture not found: {FIXTURE_PATH}\n"
            f"Regenerate it with: python3 tools/gen_test_fixture.py"
        )
    with FIXTURE_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


_DATA: Dict[str, Any] = _load()
_INSTRUMENTS: List[Dict[str, Any]] = _DATA.get("instruments", [])


# ─── Lookup helpers ──────────────────────────────────────────────────

def by_ticker_exchange(ticker: str, exchange: str) -> Dict[str, Any]:
    """Return the single instrument matching ticker+exchange.

    Raises AssertionError with a clear message if the fixture is missing
    the instrument or has multiple matches.
    """
    hits = [
        i for i in _INSTRUMENTS
        if i.get("ticker") == ticker and i.get("exchange") == exchange
    ]
    assert len(hits) == 1, (
        f"fixture missing or ambiguous: {ticker}@{exchange} "
        f"(got {len(hits)} match(es))"
    )
    return hits[0]


def all_by_ticker(ticker: str) -> List[Dict[str, Any]]:
    """Return all instruments with the given ticker (may be empty)."""
    return [i for i in _INSTRUMENTS if i.get("ticker") == ticker]


def all_instruments() -> List[Dict[str, Any]]:
    """Return every instrument in the fixture."""
    return list(_INSTRUMENTS)


def by_isin(isin: str) -> Dict[str, Any]:
    """Return the single instrument matching the ISIN, or raise."""
    hits = [i for i in _INSTRUMENTS if i.get("isin") == isin]
    assert len(hits) == 1, f"fixture missing or ambiguous ISIN: {isin}"
    return hits[0]


def meta() -> Dict[str, Any]:
    """Return the fixture meta block."""
    return _DATA.get("meta", {})


def count() -> int:
    """Return the number of instruments in the fixture."""
    return len(_INSTRUMENTS)


def exchanges() -> set:
    """Return the set of primary exchanges present in the fixture."""
    return {i["exchange"] for i in _INSTRUMENTS if i.get("exchange")}


def currencies() -> set:
    """Return the set of currencies present in the fixture."""
    return {i["currency"] for i in _INSTRUMENTS if i.get("currency")}


def countries() -> set:
    """Return the set of countries present in the fixture."""
    return {i["country"] for i in _INSTRUMENTS if i.get("country")}


def asset_classes() -> set:
    """Return the set of asset classes present in the fixture."""
    return {i["asset_class"] for i in _INSTRUMENTS if i.get("asset_class")}


# ─── Anchors ─────────────────────────────────────────────────────────
#
# Every test reads its expectations from these. Add a new anchor here
# when a test needs a fixture instrument that isn't already covered.

TESTA   = by_ticker_exchange("TESTA",   "XNAS")  # simple US equity
TESTB   = by_ticker_exchange("TESTB",   "XNAS")  # second US equity
NEWTICK = by_ticker_exchange("NEWTICK", "XNAS")  # renamed from OLDTICK
MULTI   = by_ticker_exchange("MULTI",   "XNAS")  # two listings (XNAS + XETR)
DUP_US  = by_ticker_exchange("DUP",     "XNAS")  # ambiguous ticker, US side
DUP_UK  = by_ticker_exchange("DUP",     "XLON")  # ambiguous ticker, UK side
ETFSYN  = by_ticker_exchange("ETFSYN",  "XNAS")  # ETF

# Convenience: (ticker, exchange) pairs that the fixture treats as
# "ambiguous" — meaning `by_ticker(ticker)` returns more than one hit.
AMBIGUOUS_TICKERS: List[str] = sorted(
    {i["ticker"] for i in _INSTRUMENTS}
    - {i["ticker"] for i in _INSTRUMENTS if i["ticker"] == "DUP"}  # keep only multi-hit
    | {"DUP"}  # explicit: DUP is the ambiguous one
)

# Tickers used in a rename chain, in chronological order.
RENAME_HISTORY = {
    "current": NEWTICK["ticker"],
    "previous": "OLDTICK",
}

# The three exchanges present in the fixture (primary + MULTI's secondary).
EXPECTED_EXCHANGES = {"XNAS", "XLON", "XETR"}