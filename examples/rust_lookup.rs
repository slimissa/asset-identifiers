//! Asset Identifier Registry — Rust usage example.
//!
//! This example demonstrates all major features of the
//! Rust wrapper for the asset identifier registry.
//!
//! Run:
//!   cd examples
//!   cargo run --example rust_lookup
//!
//! Or compile directly:
//!   rustc rust_lookup.rs --extern asset_identifiers=../wrappers/rust/target/debug/libasset_identifiers.rlib -L ../wrappers/rust/target/debug/deps

use asset_identifiers::{AssetClass, AssetRegistry};

// ─── Helpers ──────────────────────────────────────────────────────────

fn print_section(title: &str) {
    println!();
    println!("{}", "═".repeat(60));
    println!("  {}", title);
    println!("{}", "═".repeat(60));
}

fn deref_or_nil(value: &Option<String>) -> &str {
    value.as_deref().unwrap_or("nil")
}

// ─── Main ─────────────────────────────────────────────────────────────

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // ─── Load the Registry ──────────────────────────────────────────

    let registry = AssetRegistry::load("../../identifiers.json")?;

    print_section("Registry Overview");
    println!("Version:     {}", registry.version());
    println!("Generated:   {}", registry.generated());
    println!("Instruments: {}", registry.count());
    println!("Path:        {}", registry.path().display());
    println!("Sources:     {:?}", registry.sources());

    // ─── Lookup by ISIN ─────────────────────────────────────────────

    print_section("Lookup by ISIN");

    let aapl = registry.by_isin("US0378331005").ok_or("AAPL not found")?;

    println!("Ticker:      {}", aapl.ticker);
    println!("Name:        {}", aapl.name);
    println!("Exchange:    {}", aapl.exchange);
    println!("Currency:    {}", aapl.currency);
    println!("Asset class: {:?}", aapl.asset_class);
    println!("CUSIP:       {}", deref_or_nil(&aapl.cusip));
    println!("FIGI:        {}", deref_or_nil(&aapl.figi));
    println!("LEI:         {}", deref_or_nil(&aapl.lei));
    println!("Active:      {}", aapl.active);
    println!("Country:     {}", deref_or_nil(&aapl.country));

    // ─── Lookup by Other Identifiers ────────────────────────────────

    print_section("Lookup by Other Identifiers");

    if let Some(msft) = registry.by_cusip("594918104") {
        println!("By CUSIP 594918104 → {} ({})", msft.ticker, msft.name);
    }

    if let Some(aapl_figi) = registry.by_figi("BBG000B9XRY4") {
        println!(
            "By FIGI BBG000B9XRY4 → {} ({})",
            aapl_figi.ticker, aapl_figi.name
        );
    }

    if let Some(aapl_lei) = registry.by_lei("HWUPKR0MPOU8FGXBT394") {
        println!("By LEI HWUPKR... → {} ({})", aapl_lei.ticker, aapl_lei.name);
    }

    // ─── Ticker Lookup ──────────────────────────────────────────────

    print_section("Ticker Lookup");

    let aapl_ticker = registry.by_ticker("AAPL", Some("XNAS"));
    if let Some(inst) = aapl_ticker.first() {
        println!("AAPL on XNAS → {}", inst.isin);
    }

    let pru_all = registry.by_ticker("PRU", None);
    println!("PRU (all exchanges): {} results", pru_all.len());
    for pru in &pru_all {
        println!(
            "  {} on {} → {} ({})",
            pru.ticker, pru.exchange, pru.isin, pru.name
        );
    }

    let pru_london = registry.by_ticker("PRU", Some("XLON"));
    if let Some(inst) = pru_london.first() {
        println!(
            "PRU on XLON → {} ({}, {})",
            inst.isin, inst.name, inst.currency
        );
    }

    let pru_nyse = registry.by_ticker("PRU", Some("XNYS"));
    if let Some(inst) = pru_nyse.first() {
        println!(
            "PRU on XNYS → {} ({}, {})",
            inst.isin, inst.name, inst.currency
        );
    }

    // ─── Filtering ──────────────────────────────────────────────────

    print_section("Filtering");

    let nasdaq = registry.by_exchange("XNAS");
    println!("NASDAQ (XNAS): {} instruments", nasdaq.len());

    let etfs = registry.by_asset_class(AssetClass::Etf);
    println!("ETFs: {} instruments", etfs.len());
    for etf in &etfs {
        println!("  {} ({})", etf.ticker, etf.name);
    }

    let us_instruments = registry.by_country("US");
    println!("US instruments: {}", us_instruments.len());

    let usd_instruments = registry.by_currency("USD");
    println!("USD instruments: {}", usd_instruments.len());

    // ─── Aggregate Information ──────────────────────────────────────

    print_section("Aggregate Information");

    println!("Exchanges:    {:?}", registry.exchanges());
    println!("Asset classes: {:?}", registry.asset_classes());
    println!("Currencies:   {:?}", registry.currencies());
    println!("Countries:    {:?}", registry.countries());

    // ─── Identifier Coverage ────────────────────────────────────────

    print_section("Identifier Coverage");

    let coverage = registry.identifier_coverage();

    println!(
        "ISIN:  {}/{} ({:.1}%)",
        coverage.isin.covered, coverage.isin.total, coverage.isin.percentage
    );
    println!(
        "CUSIP: {}/{} ({:.1}%)",
        coverage.cusip.covered, coverage.cusip.total, coverage.cusip.percentage
    );
    println!(
        "SEDOL: {}/{} ({:.1}%)",
        coverage.sedol.covered, coverage.sedol.total, coverage.sedol.percentage
    );
    println!(
        "FIGI:  {}/{} ({:.1}%)",
        coverage.figi.covered, coverage.figi.total, coverage.figi.percentage
    );
    println!(
        "LEI:   {}/{} ({:.1}%)",
        coverage.lei.covered, coverage.lei.total, coverage.lei.percentage
    );

    // ─── Ticker Changes ─────────────────────────────────────────────

    print_section("Ticker Changes");

    if let Some(meta) = registry.by_isin("US30303M1027") {
        println!("Current ticker: {}", meta.ticker);
        println!("ISIN:           {} (unchanged)", meta.isin);
        println!("History:");
        for event in &meta.history {
            let reason = deref_or_nil(&event.reason);
            println!(
                "  {}  {}  {:?}  ({})",
                event.ticker, event.change_date, event.change_type, reason
            );
        }
    }

    // ─── Multi-Exchange Listings ────────────────────────────────────

    print_section("Multi-Exchange Listings");

    for listing in &aapl.listings {
        println!(
            "{}: {} ({}, {:?})",
            listing.exchange, listing.ticker, listing.currency, listing.status
        );
    }

    // ─── Ambiguous Tickers ──────────────────────────────────────────

    print_section("Ambiguous Tickers");

    let ambiguous = registry.tickers_with_multiple_listings();
    println!("Tickers with multiple listings: {:?}", ambiguous);

    // ─── Existence Checks ───────────────────────────────────────────

    print_section("Existence Checks");

    println!(
        "US0378331005 exists: {}",
        registry.isin_exists("US0378331005")
    );
    println!(
        "XX0000000000 exists: {}",
        registry.isin_exists("XX0000000000")
    );
    println!(
        "AAPL on XNAS exists: {}",
        registry.ticker_exists("AAPL", Some("XNAS"))
    );
    println!(
        "PRU anywhere exists: {}",
        registry.ticker_exists("PRU", None)
    );
    println!(
        "ZZZZ exists:         {}",
        registry.ticker_exists("ZZZZ", None)
    );

    // ─── Iteration ──────────────────────────────────────────────────

    print_section("Iteration (first 10)");

    for (i, inst) in registry.iter().enumerate() {
        if i >= 10 {
            println!("  ...");
            break;
        }
        println!("  {} ({}): {}", inst.ticker, inst.exchange, inst.isin);
    }

    // ─── String Representation ──────────────────────────────────────

    print_section("String Representation");

    println!("{}", registry);

    println!();
    println!("Example complete.");

    Ok(())
}
