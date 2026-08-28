# Security Policy

This document outlines the security policy for the **Asset Identifier Registry** — a canonical, versioned, machine-readable registry of financial instrument identifiers.

---

## Supported Versions

Security updates are applied to the latest release only. Older tags are provided for reproducibility but do not receive security patches.

| Version | Supported |
|---------|-----------|
| v1.0.2 (latest) | ✅ |
| v1.0.1 | ❌ |
| v1.0.0 | ❌ |

---

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

### Preferred: GitHub Private Vulnerability Reporting

Use GitHub's private reporting feature:

```
https://github.com/slimissa/asset-identifiers/security/advisories/new
```

This creates a private advisory visible only to maintainers.

### Alternative: Email

If you cannot use GitHub's private reporting:

```
Email: security@asset-identifiers.dev
Subject: [SECURITY] Brief description
```

### Response Time

| Severity | Initial Response | Fix Target |
|----------|-----------------|------------|
| Critical | Within 24 hours | 48 hours |
| High | Within 72 hours | 7 days |
| Medium | Within 1 week | 30 days |
| Low | Best effort | Next release |

---

## Scope

### In Scope

- `identifiers.json` — registry data integrity
- `schema.json` — schema validation bypasses
- `tools/validate.py` — validation logic flaws
- `tools/build.py` — build artifact tampering
- `tools/fetch_*.py` — data fetching vulnerabilities
- `wrappers/` — wrapper API security issues

### Out of Scope

- Vulnerabilities in third-party APIs (SEC EDGAR, OpenFIGI, Yahoo Finance, Massive)
- Denial of service against public registries
- Social engineering
- Physical security
- Vulnerabilities requiring already-authenticated local access

---

## Data Integrity

The registry's primary security concern is **data integrity** — ensuring that ISINs, CUSIPs, FIGIs, and related identifiers are correct and have not been tampered with.

### Protection Mechanisms

| Mechanism | Description |
|-----------|-------------|
| **Check-digit validation** | Every ISIN, CUSIP, and SEDOL is mathematically verified |
| **SHA-256 audit chain** | Build artifacts record cryptographic hashes |
| **Cross-registry validation** | Currency codes validated against ISO 4217, MICs against Exchange Calendar |
| **Source URL requirement** | Every data entry must cite an official source |
| **Git commit history** | Every change is traceable through git |

### What to Report

- Incorrect ISIN/CUSIP/FIGI that passes validation
- Missing source URLs in data entries
- Duplicate identifiers not caught by uniqueness checks
- Schema validation bypasses
- Check-digit algorithm errors

---

## API Keys

The fetcher tools require API keys for external services. These keys must never be committed to the repository.

### Protected Keys

| Tool | Environment Variable | Where to Store |
|------|---------------------|----------------|
| `fetch_massive.py` | `MASSIVE_API_KEY` | Shell profile, CI secrets |
| `fetch_openfigi_batch.py` | `OPENFIGI_API_KEY` | Shell profile, CI secrets |

### What to Report

- API keys accidentally committed to the repository
- Keys exposed in logs or error messages
- Fetcher code that sends keys to unintended endpoints

---

## Rate Limiting

The fetcher tools implement rate limiting to comply with upstream API terms of service. This is not a security vulnerability but a compliance requirement.

| Tool | Rate Limit | Implementation |
|------|-----------|----------------|
| `fetch_sec_edgar.py` | 10 req/sec | 150ms delay |
| `fetch_yahoo_cusip.py` | ~10 req/sec | 2.0s delay + retry |
| `fetch_openfigi_batch.py` | 25 req/sec | 500ms delay |
| `fetch_massive.py` | 5 req/min | 12.5s delay |

**Do not remove or reduce rate limiting without maintainer approval.**

---

## Supply Chain

### Dependencies

| Language | Dependencies | Risk |
|----------|-------------|------|
| Python | `requests`, `jsonschema`, `pytest` | Low — pinned in CI |
| JavaScript | None (stdlib only) | None |
| Rust | `serde`, `serde_json`, `thiserror` | Low — crates.io verified |
| Go | None (stdlib only) | None |

### Dependency Updates

Dependabot monitors all ecosystems and creates automated pull requests for version updates. Merge only after CI passes.

---

## Secure Development Practices

| Practice | Status |
|----------|--------|
| Code review before merge | ✅ |
| CI validation on every push | ✅ |
| No secrets in repository | ✅ |
| Rate-limited external API access | ✅ |
| User-Agent identification | ✅ |
| Error messages without sensitive data | ✅ |

---

## Disclosure Policy

When a vulnerability is fixed:

1. A patch is applied to the main branch
2. A new patch version is tagged (e.g., v1.0.3)
3. The vulnerability is documented in `CHANGELOG.md` under "Fixed"
4. Credit is given to the reporter unless they request anonymity

---

## Acknowledgments

Thank you to all security researchers who responsibly disclose vulnerabilities. Your work keeps the registry trustworthy.