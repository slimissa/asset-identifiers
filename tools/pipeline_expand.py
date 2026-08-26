#!/usr/bin/env python3
"""
Pipeline orchestrator for Asset Identifier Registry expansion.

Runs the complete expansion pipeline:
    1. SEC EDGAR → ticker, name, exchange, LEI
    2. Yahoo Finance → CUSIP → ISIN derivation
    3. OpenFIGI → FIGI
    4. Merge → Validate → Build → Test

Usage:
    python3 tools/pipeline_expand.py --dry-run              # Preview only
    python3 tools/pipeline_expand.py --limit 50             # Test with 50 tickers
    python3 tools/pipeline_expand.py --skip-sec             # Skip SEC EDGAR step
    python3 tools/pipeline_expand.py --skip-yahoo           # Skip Yahoo Finance step
    python3 tools/pipeline_expand.py --skip-openfigi        # Skip OpenFIGI step
    python3 tools/pipeline_expand.py --report-only          # Only show coverage report
    python3 tools/pipeline_expand.py --full                 # Full run (all 10,388 tickers)

Exit codes:
    0 — success
    1 — validation failed
    2 — usage error
"""

import json
import sys
import time
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# ─── Constants ────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.parent

SP500_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "NFLX",
    "JPM", "BAC", "GS", "V", "MA", "JNJ", "PFE", "UNH",
    "PG", "KO", "PEP", "WMT", "COST", "CAT", "BA", "GE",
    "HON", "XOM", "CVX", "DIS", "AMD", "TSLA", "INTC",
    "QCOM", "AVGO", "CSCO", "CRM", "PYPL", "SBUX", "BRK.B",
    "VTI", "VEA", "SPY", "QQQ", "IWM",
]

# ─── Reporting ────────────────────────────────────────────────────────

def print_section(title: str) -> None:
    """Print a formatted section header."""
    print()
    print("═" * 60)
    print(f"  {title}")
    print("═" * 60)


def coverage_report(data: Dict) -> None:
    """Print coverage statistics for the registry."""
    instruments = data.get("instruments", [])
    total = len(instruments)

    isin_count = sum(1 for i in instruments if i.get("isin"))
    cusip_count = sum(1 for i in instruments if i.get("cusip"))
    sedol_count = sum(1 for i in instruments if i.get("sedol"))
    figi_count = sum(1 for i in instruments if i.get("figi"))
    lei_count = sum(1 for i in instruments if i.get("lei"))

    print_section("Identifier Coverage Report")
    print(f"Instruments: {total}")
    print(f"ISIN:  {isin_count}/{total} ({100*isin_count//total}%)")
    print(f"CUSIP: {cusip_count}/{total} ({100*cusip_count//total}%)")
    print(f"SEDOL: {sedol_count}/{total} ({100*sedol_count//total}%)")
    print(f"FIGI:  {figi_count}/{total} ({100*figi_count//total}%)")
    print(f"LEI:   {lei_count}/{total} ({100*lei_count//total}%)")

    # Exchange coverage
    exchanges = set(i.get("exchange") for i in instruments if i.get("exchange"))
    print(f"\nExchanges: {len(exchanges)}")
    for exchange in sorted(exchanges):
        count = sum(1 for i in instruments if i.get("exchange") == exchange)
        print(f"  {exchange}: {count}")

    # Asset class coverage
    asset_classes = set(i.get("asset_class") for i in instruments if i.get("asset_class"))
    print(f"\nAsset classes: {len(asset_classes)}")
    for asset_class in sorted(asset_classes):
        count = sum(1 for i in instruments if i.get("asset_class") == asset_class)
        print(f"  {asset_class}: {count}")


def run_step(step_name: str, command: List[str], cwd: Path = PROJECT_ROOT) -> bool:
    """
    Run a pipeline step as a subprocess.

    Args:
        step_name: Human-readable step name
        command: Command to run
        cwd: Working directory

    Returns:
        True if successful, False otherwise
    """
    print_section(step_name)
    print(f"Running: {' '.join(command)}")
    print()

    result = subprocess.run(command, cwd=cwd, text=True)

    if result.returncode != 0:
        print(f"FAILED: {step_name} (exit code {result.returncode})", file=sys.stderr)
        return False

    print(f"OK: {step_name}")
    return True


def validate_registry(data_path: Path = Path("identifiers.json")) -> bool:
    """Run the validator."""
    return run_step(
        "Validation",
        [sys.executable, "tools/validate.py", "--verbose"],
        cwd=PROJECT_ROOT,
    )


def build_distribution() -> bool:
    """Build distribution artifacts."""
    return run_step(
        "Build Distribution",
        [sys.executable, "tools/build.py"],
        cwd=PROJECT_ROOT,
    )


def run_python_tests() -> bool:
    """Run Python test suite."""
    return run_step(
        "Python Tests",
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        cwd=PROJECT_ROOT,
    )


def run_javascript_tests() -> bool:
    """Run JavaScript test suite."""
    return run_step(
        "JavaScript Tests",
        ["npm", "test"],
        cwd=PROJECT_ROOT / "wrappers" / "javascript",
    )


def run_rust_tests() -> bool:
    """Run Rust test suite."""
    return run_step(
        "Rust Tests",
        ["cargo", "test"],
        cwd=PROJECT_ROOT / "wrappers" / "rust",
    )


def run_go_tests() -> bool:
    """Run Go test suite."""
    return run_step(
        "Go Tests",
        ["go", "test", "./..."],
        cwd=PROJECT_ROOT / "wrappers" / "go",
    )


# ─── Main Pipeline ────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Run the full Asset Identifier Registry expansion pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview all steps without applying changes",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only first N tickers",
    )
    parser.add_argument(
        "--skip-sec",
        action="store_true",
        help="Skip SEC EDGAR fetcher step",
    )
    parser.add_argument(
        "--skip-yahoo",
        action="store_true",
        help="Skip Yahoo Finance CUSIP fetcher step",
    )
    parser.add_argument(
        "--skip-openfigi",
        action="store_true",
        help="Skip OpenFIGI batch fetcher step",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip test suite (faster iteration)",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Only show coverage report, don't run any steps",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Full run (process all tickers, no limit)",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("identifiers.json"),
        help="Path to identifiers.json",
    )

    args = parser.parse_args()

    start_time = time.time()

    print("=" * 60)
    print("  Asset Identifier Registry — Expansion Pipeline")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Load current data for report
    try:
        with open(args.data, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: {args.data} not found", file=sys.stderr)
        sys.exit(2)

    # Initial report
    coverage_report(data)

    if args.report_only:
        sys.exit(0)

    # Build dry-run flag
    dry_flag = ["--dry-run"] if args.dry_run else []
    limit_flag = ["--limit", str(args.limit)] if args.limit else []

    # Step 1: SEC EDGAR
    if not args.skip_sec:
        sec_command = [sys.executable, "tools/fetch_sec_edgar.py"] + dry_flag + limit_flag
        if not run_step("Step 1: SEC EDGAR", sec_command):
            sys.exit(1)

    # Step 2: Yahoo Finance CUSIP
    if not args.skip_yahoo:
        yahoo_command = [sys.executable, "tools/fetch_yahoo_cusip.py"] + dry_flag + limit_flag
        if not run_step("Step 2: Yahoo Finance CUSIP", yahoo_command):
            sys.exit(1)

    # Step 3: OpenFIGI Batch
    if not args.skip_openfigi:
        openfigi_command = [sys.executable, "tools/fetch_openfigi_batch.py"] + dry_flag + limit_flag
        if not run_step("Step 3: OpenFIGI Batch", openfigi_command):
            sys.exit(1)

    # Step 4: Validate
    if not run_step("Step 4: Validate", [sys.executable, "tools/validate.py", "--verbose"]):
        sys.exit(1)

    # Step 5: Build
    if not run_step("Step 5: Build Distribution", [sys.executable, "tools/build.py"]):
        sys.exit(1)

    # Step 6: Tests (optional)
    if not args.skip_tests:
        if not run_python_tests():
            sys.exit(1)
        if not run_javascript_tests():
            sys.exit(1)
        if not run_rust_tests():
            sys.exit(1)
        if not run_go_tests():
            sys.exit(1)

    # Final report
    with open(args.data, "r", encoding="utf-8") as f:
        data = json.load(f)
    coverage_report(data)

    elapsed = time.time() - start_time
    print_section("Pipeline Complete")
    print(f"Elapsed time: {elapsed:.1f} seconds")
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    sys.exit(0)


if __name__ == "__main__":
    main()