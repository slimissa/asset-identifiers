#!/usr/bin/env python3
"""
Asset Identifier Registry — main wrapper class.

Loads identifiers.json and provides lookup methods for
ISIN, CUSIP, SEDOL, FIGI, LEI, and ticker+exchange.

This wrapper is dependency-free and uses only the Python
standard library. It is designed to match the API pattern
of the ISO 4217 and Exchange Calendar registry wrappers.

Example:
    from asset_identifiers import AssetRegistry

    registry = AssetRegistry("identifiers.json")

    # Look up by ISIN
    aapl = registry.by_isin("US0378331005")
    print(aapl["ticker"])  # AAPL

    # Look up by ticker on a specific exchange
    pru_nyse = registry.by_ticker("PRU", "XNYS")
    print(pru_nyse["isin"])  # US7443201022

    # Look up by ticker without exchange (returns list)
    pru_all = registry.by_ticker("PRU")
    print(len(pru_all))  # 2

    # Iterate over all instruments
    for instrument in registry:
        print(instrument["ticker"])
"""

import json
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Union


class AssetRegistry:
    """
    Asset Identifier Registry wrapper.

    Loads a JSON registry of financial instruments and provides
    lookup methods for various identifier types.

    The registry is immutable after loading. If the underlying
    JSON file changes, create a new AssetRegistry instance.

    Attributes:
        count: Number of instruments in the registry
        instruments: List of all instrument dicts
    """

    def __init__(self, path: Union[str, Path] = "identifiers.json"):
        """
        Initialize the registry.

        Args:
            path: Path to identifiers.json. Accepts str or Path.

        Raises:
            FileNotFoundError: If the path does not exist
            json.JSONDecodeError: If the file is not valid JSON
        """
        self._path = Path(path)
        self._load()

    def _load(self) -> None:
        """Load the registry from disk into memory."""
        with open(self._path, "r", encoding="utf-8") as f:
            self._data = json.load(f)

        self._instruments: List[Dict] = self._data.get("instruments", [])
        self._meta: Dict = self._data.get("meta", {})

        # Build lookup indices for O(1) access
        self._isin_index: Dict[str, Dict] = {}
        self._cusip_index: Dict[str, Dict] = {}
        self._sedol_index: Dict[str, Dict] = {}
        self._figi_index: Dict[str, Dict] = {}
        self._lei_index: Dict[str, Dict] = {}
        self._ticker_index: Dict[str, List[Dict]] = {}
        self._exchange_index: Dict[str, List[Dict]] = {}
        self._asset_class_index: Dict[str, List[Dict]] = {}
        self._country_index: Dict[str, List[Dict]] = {}
        self._currency_index: Dict[str, List[Dict]] = {}

        for inst in self._instruments:
            isin = inst.get("isin")
            if isin:
                self._isin_index[isin] = inst

            cusip = inst.get("cusip")
            if cusip:
                self._cusip_index[cusip] = inst

            sedol = inst.get("sedol")
            if sedol:
                self._sedol_index[sedol] = inst

            figi = inst.get("figi")
            if figi:
                self._figi_index[figi] = inst

            lei = inst.get("lei")
            if lei:
                self._lei_index[lei] = inst

            ticker = inst.get("ticker")
            if ticker:
                if ticker not in self._ticker_index:
                    self._ticker_index[ticker] = []
                self._ticker_index[ticker].append(inst)

            exchange = inst.get("exchange")
            if exchange:
                if exchange not in self._exchange_index:
                    self._exchange_index[exchange] = []
                self._exchange_index[exchange].append(inst)

            asset_class = inst.get("asset_class")
            if asset_class:
                if asset_class not in self._asset_class_index:
                    self._asset_class_index[asset_class] = []
                self._asset_class_index[asset_class].append(inst)

            country = inst.get("country")
            if country:
                if country not in self._country_index:
                    self._country_index[country] = []
                self._country_index[country].append(inst)

            currency = inst.get("currency")
            if currency:
                if currency not in self._currency_index:
                    self._currency_index[currency] = []
                self._currency_index[currency].append(inst)

    # ─── Properties ──────────────────────────────────────────────────

    @property
    def count(self) -> int:
        """Number of instruments in the registry."""
        return len(self._instruments)

    @property
    def instruments(self) -> List[Dict]:
        """List of all instrument dicts."""
        return self._instruments

    @property
    def path(self) -> Path:
        """Path to the registry file."""
        return self._path

    # ─── Metadata ────────────────────────────────────────────────────

    def meta(self) -> Dict:
        """Return registry metadata."""
        return self._meta

    def version(self) -> str:
        """Return registry version."""
        return self._meta.get("version", "unknown")

    def generated(self) -> str:
        """Return registry generation date."""
        return self._meta.get("generated", "unknown")

    def sources(self) -> List[str]:
        """Return list of data sources."""
        return self._meta.get("sources", [])

    # ─── Bulk Access ─────────────────────────────────────────────────

    def all(self) -> List[Dict]:
        """Return all instruments as a list."""
        return self._instruments

    def __iter__(self) -> Iterator[Dict]:
        """Iterate over all instruments."""
        return iter(self._instruments)

    def __len__(self) -> int:
        """Number of instruments."""
        return self.count

    def __repr__(self) -> str:
        """String representation."""
        return f"AssetRegistry(count={self.count}, path='{self._path}')"

    def __str__(self) -> str:
        """Human-readable representation."""
        return (
            f"Asset Identifier Registry v{self.version()} "
            f"({self.count} instruments)"
        )

    # ─── Lookup by Identifier ────────────────────────────────────────

    def by_isin(self, isin: str) -> Optional[Dict]:
        """
        Look up an instrument by ISIN.

        Args:
            isin: 12-character ISIN (e.g., US0378331005)

        Returns:
            Instrument dict or None if not found
        """
        return self._isin_index.get(isin.upper())

    def by_cusip(self, cusip: str) -> Optional[Dict]:
        """
        Look up an instrument by CUSIP.

        Args:
            cusip: 9-character CUSIP (e.g., 037833100)

        Returns:
            Instrument dict or None if not found
        """
        return self._cusip_index.get(cusip.upper())

    def by_sedol(self, sedol: str) -> Optional[Dict]:
        """
        Look up an instrument by SEDOL.

        Args:
            sedol: 7-character SEDOL (e.g., 2046251)

        Returns:
            Instrument dict or None if not found
        """
        return self._sedol_index.get(sedol.upper())

    def by_figi(self, figi: str) -> Optional[Dict]:
        """
        Look up an instrument by FIGI.

        Args:
            figi: 12-character FIGI (e.g., BBG000B9XRY4)

        Returns:
            Instrument dict or None if not found
        """
        return self._figi_index.get(figi.upper())

    def by_lei(self, lei: str) -> Optional[Dict]:
        """
        Look up an instrument by LEI.

        Args:
            lei: 20-character LEI

        Returns:
            Instrument dict or None if not found
        """
        return self._lei_index.get(lei.upper())

    # ─── Lookup by Ticker ────────────────────────────────────────────

    def by_ticker(
        self,
        ticker: str,
        exchange: Optional[str] = None,
    ) -> Union[Optional[Dict], List[Dict]]:
        """
        Look up instruments by ticker symbol.

        Args:
            ticker: Ticker symbol (e.g., AAPL, PRU)
            exchange: Optional MIC code to disambiguate (e.g., XNAS)

        Returns:
            If exchange is provided: Instrument dict or None
            If exchange is not provided: List of matching instruments

        Examples:
            # Single result (ticker is unique)
            registry.by_ticker("AAPL")  # Returns list with 1 item

            # Disambiguated by exchange
            registry.by_ticker("PRU", "XNYS")  # Returns dict
            registry.by_ticker("PRU", "XLON")  # Returns dict

            # Multiple results (ticker is ambiguous)
            registry.by_ticker("PRU")  # Returns list with 2 items
        """
        ticker = ticker.upper()
        matches = self._ticker_index.get(ticker, [])

        if exchange is not None:
            exchange = exchange.upper()
            for inst in matches:
                if inst.get("exchange") == exchange:
                    return inst
            return None

        return matches

    # ─── Filtering ───────────────────────────────────────────────────

    def by_exchange(self, exchange: str) -> List[Dict]:
        """
        Return all instruments listed on a given exchange.

        Args:
            exchange: MIC code (e.g., XNAS)

        Returns:
            List of instrument dicts
        """
        return self._exchange_index.get(exchange.upper(), [])

    def by_asset_class(self, asset_class: str) -> List[Dict]:
        """
        Return all instruments of a given asset class.

        Args:
            asset_class: Asset class (equity, etf, bond, etc.)

        Returns:
            List of instrument dicts
        """
        return self._asset_class_index.get(asset_class.lower(), [])

    def by_country(self, country: str) -> List[Dict]:
        """
        Return all instruments from a given country.

        Args:
            country: ISO 3166-1 alpha-2 country code (e.g., US)

        Returns:
            List of instrument dicts
        """
        return self._country_index.get(country.upper(), [])

    def by_currency(self, currency: str) -> List[Dict]:
        """
        Return all instruments trading in a given currency.

        Args:
            currency: ISO 4217 currency code (e.g., USD)

        Returns:
            List of instrument dicts
        """
        return self._currency_index.get(currency.upper(), [])

    # ─── Aggregate Information ───────────────────────────────────────

    def exchanges(self) -> List[str]:
        """
        Return sorted list of all exchanges in the registry.

        Returns:
            List of MIC codes, sorted alphabetically
        """
        return sorted(self._exchange_index.keys())

    def asset_classes(self) -> List[str]:
        """
        Return sorted list of all asset classes in the registry.

        Returns:
            List of asset class strings, sorted alphabetically
        """
        return sorted(self._asset_class_index.keys())

    def currencies(self) -> List[str]:
        """
        Return sorted list of all currencies in the registry.

        Returns:
            List of ISO 4217 currency codes, sorted alphabetically
        """
        return sorted(self._currency_index.keys())

    def countries(self) -> List[str]:
        """
        Return sorted list of all countries in the registry.

        Returns:
            List of ISO 3166-1 alpha-2 country codes, sorted
        """
        return sorted(self._country_index.keys())

    # ─── Convenience Methods ─────────────────────────────────────────

    def ticker_exists(self, ticker: str, exchange: Optional[str] = None) -> bool:
        """
        Check if a ticker exists in the registry.

        Args:
            ticker: Ticker symbol
            exchange: Optional MIC code

        Returns:
            True if the ticker exists, False otherwise
        """
        if exchange is not None:
            return self.by_ticker(ticker, exchange) is not None
        return len(self.by_ticker(ticker)) > 0

    def isin_exists(self, isin: str) -> bool:
        """
        Check if an ISIN exists in the registry.

        Args:
            isin: ISIN code

        Returns:
            True if the ISIN exists, False otherwise
        """
        return self.by_isin(isin) is not None

    def resolve(
        self,
        identifier: str,
        exchange: Optional[str] = None,
    ) -> Union[Optional[Dict], List[Dict]]:
        """
        Resolve any identifier type to an instrument.

        Automatically detects the identifier type:
        - 12 chars → ISIN
        - 9 chars → CUSIP
        - 7 chars → SEDOL
        - 12 chars starting with BBG → FIGI
        - 20 chars → LEI
        - Otherwise → ticker

        Args:
            identifier: Any identifier string
            exchange: Optional MIC code for ticker disambiguation

        Returns:
            Instrument dict, list of dicts, or None
        """
        identifier = identifier.upper().strip()

        if len(identifier) == 12 and identifier.startswith("BBG"):
            return self.by_figi(identifier)
        elif len(identifier) == 12:
            return self.by_isin(identifier)
        elif len(identifier) == 9:
            return self.by_cusip(identifier)
        elif len(identifier) == 7:
            return self.by_sedol(identifier)
        elif len(identifier) == 20:
            return self.by_lei(identifier)
        else:
            return self.by_ticker(identifier, exchange)

    # ─── Statistical Methods ─────────────────────────────────────────

    def identifier_coverage(self) -> Dict[str, Dict[str, int]]:
        """
        Return identifier coverage statistics.

        Returns:
            Dict with coverage counts and percentages for each
            identifier type: ISIN, CUSIP, SEDOL, FIGI, LEI
        """
        total = self.count
        stats = {}

        for id_type in ["isin", "cusip", "sedol", "figi", "lei"]:
            covered = sum(1 for i in self._instruments if i.get(id_type))
            stats[id_type] = {
                "covered": covered,
                "total": total,
                "percentage": round(100 * covered / total, 2) if total > 0 else 0,
            }

        return stats

    def tickers_with_multiple_listings(self) -> List[str]:
        """
        Return tickers that appear on multiple exchanges.

        Returns:
            List of ticker symbols that have multiple exchange listings
        """
        return [
            ticker for ticker, instruments in self._ticker_index.items()
            if len(instruments) > 1
        ]