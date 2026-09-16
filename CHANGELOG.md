# Changelog

All notable changes to this project.

## [Unreleased]

Tier 3 documentation and schema-versioning fixes in progress. No functional changes pending.

## [1.4.0] — 2026-09-14

The licensing-review release. Real identifier data is removed from the public repository (ADR 0001), and every wrapper package, `schema.json`'s `schema_version`, and the registry's own `meta.version` are unified at 1.4.0 — the version this project had already reached internally before the relicensing review, and the version `wrappers/python/asset_identifiers/__init__.py` and `wrappers/javascript/package.json` already carried. `meta.version` and `schema_version` previously lagged behind at 1.0.0; that drift is resolved here.

### Changed

- Repository ships code, schema, validator, and a synthetic test fixture only. Real identifier data is no longer distributed — see [DATA_LICENSE.md](./DATA_LICENSE.md) and [ADR 0001](./docs/decisions/0001-data-license.md).
- Tests derive expected values from per-language fixture anchors instead of hardcoded literals.

### Added

- ADR 0001: private data, public code.
- Cross-language consistency example scripts (`examples/consistency_check.{py,js,rs,go}`).
- Regression tests for validator edge cases.
- `schema_version` field on the registry's `meta` object, tracking which version of `schema.json` produced a given data file. Moves in lockstep with the package version as of this release.

### Fixed

- Validator no longer crashes on an empty `instruments` array or wrong-typed fields.
- CUSIP check digit handles multi-digit letter values correctly.
- ISIN country allow-list accepts supranational prefixes (XS, EU) alongside ISO 3166-1 codes.
- LEI validation includes the ISO 17442 mod-97 checksum; previously length/pattern only.
- `build.py` schema-validates its merged output before writing distribution artifacts, instead of only validating the pre-merge source file.
- CI no longer references `identifiers.json`, which this repository never contains by design.
- Documentation describing the CUSIP coverage gap corrected — see below.
- `meta.version` and `schema_version` brought in line with the package version (both previously read 1.0.0 while the wrapper packages already read 1.4.0).

### Known limitation carried over from 1.2.1

- `history/ticker_changes.json` ships empty. Event log not yet populated.

## [1.2.1] — 2026-08-14

Initial public release. 50 instruments, full ISIN/CUSIP/SEDOL/FIGI/LEI support, validation tooling, and wrappers in Python, JavaScript, Rust, and Go. See git history prior to the 1.4.0 relicensing for full detail — this repository's earlier commit history predates the data removal described above and is not reproduced here.
