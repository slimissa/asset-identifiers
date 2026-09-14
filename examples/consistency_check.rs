//! Cross-language consistency check — Rust side.
//!
//! Loads the synthetic test fixture, looks up every instrument by ISIN
//! through the Rust wrapper, and prints one tab-separated line per
//! instrument: ISIN, ticker, name.
//!
//! See consistency_check.py for the full explanation of how this fits
//! into the cross-language consistency check as a whole.
//!
//! Run:
//!   cd wrappers/rust
//!   cargo run --example consistency_check -- ../../tests/fixtures/identifiers.test.json

use asset_identifiers::AssetRegistry;
use serde_json::Value;
use std::env;
use std::fs;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().collect();
    if args.len() != 2 {
        eprintln!("usage: consistency_check <fixture_path>");
        std::process::exit(2);
    }
    let fixture_path = &args[1];

    let fixture_raw = fs::read_to_string(fixture_path)?;
    let fixture: Value = serde_json::from_str(&fixture_raw)?;
    let registry = AssetRegistry::load(fixture_path)?;

    for expected in fixture["instruments"].as_array().unwrap() {
        let isin = expected["isin"].as_str().unwrap();
        match registry.by_isin(isin) {
            Some(actual) => println!("{}\t{}\t{}", isin, actual.ticker, actual.name),
            None => println!("{}\tMISSING\tMISSING", isin),
        }
    }

    Ok(())
}
