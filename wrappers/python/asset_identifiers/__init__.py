#!/usr/bin/env python3
"""
Asset Identifier Registry — Python wrapper.

A lightweight, dependency-free Python interface to the
canonical asset identifier registry (identifiers.json).

Example:
    from asset_identifiers import AssetRegistry

    registry = AssetRegistry("identifiers.json")

    # Look up by ISIN
    aapl = registry.by_isin("US0378331005")
    print(aapl["ticker"])  # AAPL

    # Look up by CUSIP
    aapl = registry.by_cusip("037833100")
    print(aapl["name"])  # Apple Inc.

    # Look up by ticker+exchange
    aapl = registry.by_ticker("AAPL", "XNAS")
    print(aapl["isin"])  # US0378331005

    # Get all instruments
    all_instruments = registry.all()
    print(len(all_instruments))  # 50

    # Filter by exchange
    nasdaq = registry.by_exchange("XNAS")

    # Get registry metadata
    meta = registry.meta()
    print(meta["version"])  # 0.1.0
"""

from .registry import AssetRegistry

__version__ = "0.1.0"
__author__ = "Le P'tit"
__license__ = "Apache-2.0"
__all__ = ["AssetRegistry"]