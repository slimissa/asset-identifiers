# ADR 0001 — Data Licensing Model

- **Date:** 2026-09-10
- **Status:** Accepted
- **Author:** slimissa

## Context

The Asset Identifier Registry began as a public Apache-2.0 repository
containing a curated `identifiers.json` with ISIN, CUSIP, FIGI, LEI,
ticker, and exchange values for hundreds of instruments.

That data was sourced from Financial Modeling Prep, OpenFIGI, Yahoo
Finance, and public filings. A review in v1.4.0 concluded that:

- FMP terms of service prohibit redistribution of derived data.
- OpenFIGI's terms restrict redistribution of FIGI values beyond
  attribution-required use.
- CUSIP is a proprietary identifier owned by CUSIP Global Services;
  redistribution requires a license.
- ISIN data, while structurally public, is allocated by national
  numbering agencies whose databases are frequently licensed.

Continuing to distribute the data under Apache-2.0 would expose both
the project and its downstream users to legal claims.

## Decision

The project will follow **Option C: private data, public code.**

The public repository contains:

- The schema (`schema.json`)
- The validator (`tools/validate.py`)
- The fixture generator (`tools/gen_test_fixture.py`)
- The synthetic test fixture (`tests/fixtures/identifiers.test.json`)
- Language wrappers (Python, JavaScript, Rust, Go)
- The test suites for all wrappers
- Documentation including this ADR

The public repository does not contain, and will not contain, real
identifier data.

Users who need real data supply their own. Three access models are
supported:

1. **Bring your own file.** A user with a licensed data feed writes
   their own `identifiers.json` in the documented schema and passes it
   to any wrapper. The wrappers do not know where the file came from.
2. **Private registry instance.** An operator runs their own copy of
   the project with their licensed data, never publishing it.
3. **Future hosted service.** If a hosted registry is ever offered, it
   will require the operator to obtain the appropriate distribution
   license from CUSIP Global Services, Bloomberg (for FIGI), and other
   providers.

## Consequences

**Positive.**

- No legal exposure for the public repository.
- The schema, tools, and wrappers remain Apache-2.0.
- Users with a license can still use the project end-to-end.
- The test suites remain comprehensive via the synthetic fixture.
- The project is honest about what it is and is not.

**Negative.**

- The project can no longer claim to be a "canonical registry of
  identifiers."
- Adoption requires users to source their own data.
- Cross-language consistency tests use synthetic values only.
- Coverage expansion is no longer a maintainer task; it is a user task.

**Neutral.**

- The fixture remains the single source of truth for tests.
- The anchor rule (documented in CONTRIBUTING.md) still applies.
- Downstream integrations (LAS_Shell, Tempus) contract with the code,
  not with a specific data instance.

## Alternatives Considered

**Option A — Commercial license.** Rejected at this time on cost
grounds. Revisit if a hosted service becomes viable.

**Option B — Public data only.** Rejected because it removes ISIN and
CUSIP entirely, gutting the registry's usefulness for the quant and
institutional use cases that motivated the project.

## References

- DATA_LICENSE.md
- CONTRIBUTING.md
- tools/gen_test_fixture.py
- tests/fixtures/identifiers.test.json
- CUSIP Global Services Terms of Service
- OpenFIGI Terms of Service
- Financial Modeling Prep Terms of Service