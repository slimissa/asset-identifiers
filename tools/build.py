#!/usr/bin/env python3
"""
Asset Identifier Registry build script.

Builds a single distribution artifact from source files:
1. Reads identifiers.json (core registry)
2. Reads history/ticker_changes.json (historical events)
3. Merges history into instrument entries
4. Validates the merged result
5. Writes identifiers.dist.json (distribution artifact)

Exit codes:
  0 — build succeeded
  1 — build failed (validation errors)
  2 — usage error (missing files, bad arguments)
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, date, timezone

# Import validator functions
sys.path.insert(0, str(Path(__file__).parent))
from validate import (
    validate_registry,
    validate_check_digits,
    validate_uniqueness,
    validate_business_rules,
    validate_temporal_consistency,
)


# ─── Build functions ──────────────────────────────────────────────────

def load_source_files(data_path: Path, history_path: Optional[Path]) -> Tuple[Dict, Dict]:
    """Load source files."""
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: File not found: {data_path}", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {data_path}: {e}", file=sys.stderr)
        sys.exit(2)

    history = {}
    if history_path and history_path.exists():
        try:
            with open(history_path, "r", encoding="utf-8") as f:
                history = json.load(f)
        except FileNotFoundError:
            print(f"WARNING: History file not found: {history_path}", file=sys.stderr)
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON in {history_path}: {e}", file=sys.stderr)
            sys.exit(2)

    return data, history


def merge_history(instruments: List[Dict], history: Dict) -> List[Dict]:
    """
    Merge historical ticker changes into instrument entries.

    The history file has the format:
    {
      "events": [
        {
          "isin": "US30303M1027",
          "old_ticker": "FB",
          "new_ticker": "META",
          "change_date": "2022-06-09",
          "change_type": "rename",
          "reason": "COMPANY_REBRANDING",
          "source": "NASDAQ official announcement",
          "source_url": "https://..."
        }
      ]
    }
    """
    if not history or "events" not in history:
        return instruments

    events = history.get("events", [])

    # Build lookup: ISIN → list of events
    events_by_isin: Dict[str, List[Dict]] = {}
    for event in events:
        isin = event.get("isin")
        if isin:
            if isin not in events_by_isin:
                events_by_isin[isin] = []
            events_by_isin[isin].append(event)

    # Merge events into instruments
    for instrument in instruments:
        isin = instrument.get("isin")
        if isin in events_by_isin:
            instrument_events = events_by_isin[isin]

            # Sort events by date
            instrument_events.sort(key=lambda e: e.get("change_date", ""))

            # Build history array
            history_array = []

            # Initial listing event
            if instrument.get("listing_date"):
                history_array.append({
                    "ticker": instrument.get("ticker"),
                    "change_date": instrument.get("listing_date"),
                    "change_type": "none",
                    "reason": "INITIAL_LISTING",
                    "source": None,
                    "source_url": None,
                })

            # Add all change events
            for event in instrument_events:
                history_array.append({
                    "ticker": event.get("new_ticker", instrument.get("ticker")),
                    "change_date": event.get("change_date"),
                    "change_type": event.get("change_type", "rename"),
                    "reason": event.get("reason"),
                    "source": event.get("source"),
                    "source_url": event.get("source_url"),
                })

            # If no history, create minimal history
            if not history_array:
                history_array.append({
                    "ticker": instrument.get("ticker"),
                    "change_date": instrument.get("listing_date"),
                    "change_type": "none",
                    "reason": "INITIAL_LISTING",
                    "source": None,
                    "source_url": None,
                })

            instrument["history"] = history_array

    return instruments


def update_metadata(data: Dict) -> Dict:
    """Update metadata with build information."""
    if "meta" not in data:
        data["meta"] = {}

    data["meta"]["count"] = len(data.get("instruments", []))
    data["meta"]["generated"] = date.today().isoformat()
    data["meta"]["build_timestamp"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    data["meta"]["build_version"] = "1.0.0"

    # Update coverage statistics
    coverage = data["meta"].get("coverage", {})
    exchanges = set()
    asset_classes = set()
    countries = set()

    for instrument in data.get("instruments", []):
        exchange = instrument.get("exchange")
        if exchange:
            exchanges.add(exchange)

        asset_class = instrument.get("asset_class")
        if asset_class:
            asset_classes.add(asset_class)

        country = instrument.get("country")
        if country:
            countries.add(country)

        # Also check secondary listings
        for listing in instrument.get("listings", []):
            listing_exchange = listing.get("exchange")
            if listing_exchange:
                exchanges.add(listing_exchange)

    coverage["exchanges"] = sorted(exchanges)
    coverage["asset_classes"] = sorted(asset_classes)
    coverage["countries"] = sorted(countries)
    data["meta"]["coverage"] = coverage

    return data


def build_distribution(data: Dict) -> Dict:
    """Create distribution artifact."""
    dist = {
        "meta": data.get("meta", {}),
        "instruments": data.get("instruments", []),
    }
    return dist


def write_output(data: Dict, output_path: Path, pretty: bool = True) -> None:
    """Write output file."""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            if pretty:
                json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        print(f"OK: Built {output_path}")
    except OSError as e:
        print(f"ERROR: Could not write {output_path}: {e}", file=sys.stderr)
        sys.exit(1)


def build_minified(data: Dict, output_path: Path) -> None:
    """Write minified version."""
    write_output(data, output_path, pretty=False)


def build_summary(data: Dict) -> str:
    """Generate build summary."""
    instruments = data.get("instruments", [])
    meta = data.get("meta", {})

    lines = []
    lines.append("=" * 60)
    lines.append("Asset Identifier Registry — Build Summary")
    lines.append("=" * 60)
    lines.append(f"Version:       {meta.get('version', 'unknown')}")
    lines.append(f"Generated:     {meta.get('generated', 'unknown')}")
    lines.append(f"Instruments:   {len(instruments)}")
    lines.append(f"Build time:    {meta.get('build_timestamp', 'unknown')}")

    # Coverage statistics
    coverage = meta.get("coverage", {})
    if coverage:
        lines.append(f"Exchanges:     {len(coverage.get('exchanges', []))}")
        lines.append(f"Asset classes: {len(coverage.get('asset_classes', []))}")
        lines.append(f"Countries:     {len(coverage.get('countries', []))}")

    # Identifier coverage
    isin_count = sum(1 for i in instruments if i.get("isin"))
    cusip_count = sum(1 for i in instruments if i.get("cusip"))
    sedol_count = sum(1 for i in instruments if i.get("sedol"))
    figi_count = sum(1 for i in instruments if i.get("figi"))
    lei_count = sum(1 for i in instruments if i.get("lei"))

    lines.append("")
    lines.append("Identifier coverage:")
    lines.append(f"  ISIN:  {isin_count}/{len(instruments)} ({100*isin_count//len(instruments)}%)")
    lines.append(f"  CUSIP: {cusip_count}/{len(instruments)} ({100*cusip_count//len(instruments)}%)")
    lines.append(f"  SEDOL: {sedol_count}/{len(instruments)} ({100*sedol_count//len(instruments)}%)")
    lines.append(f"  FIGI:  {figi_count}/{len(instruments)} ({100*figi_count//len(instruments)}%)")
    lines.append(f"  LEI:   {lei_count}/{len(instruments)} ({100*lei_count//len(instruments)}%)")

    # History coverage
    history_count = sum(1 for i in instruments if i.get("history"))
    lines.append(f"  History: {history_count}/{len(instruments)} ({100*history_count//len(instruments)}%)")

    lines.append("=" * 60)
    return "\n".join(lines)


# ─── Main build ───────────────────────────────────────────────────────

def build(
    data_path: Path = Path("identifiers.json"),
    schema_path: Path = Path("schema.json"),
    history_path: Optional[Path] = Path("history/ticker_changes.json"),
    output_path: Path = Path("identifiers.dist.json"),
    minified_path: Optional[Path] = Path("identifiers.dist.min.json"),
    validate: bool = True,
    pretty: bool = True,
) -> bool:
    """Run the full build process."""
    print(f"Loading {data_path}...")
    data, history = load_source_files(data_path, history_path)

    print(f"Merging history from {history_path}...")
    data["instruments"] = merge_history(data.get("instruments", []), history)

    print("Updating metadata...")
    data = update_metadata(data)

    if validate:
        print("Validating...")
        success, errors = validate_registry(data_path, schema_path)

        # Also validate the merged data in memory
        instruments = data.get("instruments", [])
        errors.extend(validate_check_digits(instruments))
        errors.extend(validate_uniqueness(instruments))
        errors.extend(validate_business_rules(instruments))
        errors.extend(validate_temporal_consistency(instruments))

        if errors:
            print(f"ERROR: Validation failed with {len(errors)} error(s):", file=sys.stderr)
            for error in errors[:20]:
                print(f"  - {error}", file=sys.stderr)
            if len(errors) > 20:
                print(f"  ... and {len(errors) - 20} more", file=sys.stderr)
            return False
        else:
            print("OK: Validation passed")

    # Build distribution
    print("Building distribution artifact...")
    dist = build_distribution(data)
    write_output(dist, output_path, pretty=pretty)

    # Build minified version
    if minified_path:
        build_minified(dist, minified_path)

    # Print summary
    print()
    print(build_summary(data))
    return True


# ─── CLI ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Build the Asset Identifier Registry distribution artifact",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("identifiers.json"),
        help="Path to source identifiers.json (default: identifiers.json)",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("schema.json"),
        help="Path to schema.json (default: schema.json)",
    )
    parser.add_argument(
        "--history",
        type=Path,
        default=Path("history/ticker_changes.json"),
        help="Path to ticker_changes.json (default: history/ticker_changes.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("identifiers.dist.json"),
        help="Output path for distribution artifact (default: identifiers.dist.json)",
    )
    parser.add_argument(
        "--minified",
        type=Path,
        default=Path("identifiers.dist.min.json"),
        help="Output path for minified version (default: identifiers.dist.min.json)",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip validation (not recommended)",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Write compact JSON (no indentation)",
    )

    args = parser.parse_args()

    # Check input files exist
    if not args.data.exists():
        print(f"ERROR: Data file not found: {args.data}", file=sys.stderr)
        sys.exit(2)

    if not args.schema.exists():
        print(f"ERROR: Schema file not found: {args.schema}", file=sys.stderr)
        sys.exit(2)

    # Run build
    success = build(
        data_path=args.data,
        schema_path=args.schema,
        history_path=args.history,
        output_path=args.output,
        minified_path=args.minified,
        validate=not args.no_validate,
        pretty=not args.compact,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()