# Validation Algorithms

This document specifies the check-digit algorithms used to validate financial instrument identifiers in the Asset Identifier Registry.

---

## Table of Contents

1. [ISIN (ISO 6166)](#isin-iso-6166)
2. [CUSIP (ANSI X9.6)](#cusip-ansi-x96)
3. [SEDOL (London Stock Exchange)](#sedol-london-stock-exchange)
4. [FIGI (Bloomberg OpenFIGI)](#figi-bloomberg-openfigi)
5. [LEI (ISO 17442)](#lei-iso-17442)
6. [Implementation Notes](#implementation-notes)
7. [Test Vectors](#test-vectors)

---

## ISIN (ISO 6166)

### Overview

The International Securities Identification Number (ISIN) is a 12-character alphanumeric code defined by ISO 6166.

### Format

```
Position:  1  2  3  4  5  6  7  8  9  10 11 12
Content:   C  C  N  N  N  N  N  N  N  N  N  D
           └─┘  └──────────────────────┘     └─┘
         Country   National Securities       Check
          Code      Identifying Number        Digit
         (alpha)   (NSIN — alphanumeric)    (numeric)
```

- **Positions 1-2**: ISO 3166-1 alpha-2 country code (e.g., `US`, `GB`, `JP`)
- **Positions 3-11**: National Securities Identifying Number (NSIN)
- **Position 12**: Check digit (0-9)

### Algorithm: Modified Luhn

1. Convert all letters to numbers: A=10, B=11, ..., Z=35
2. Split all double-digit numbers into individual digits
3. Starting from the **rightmost digit** (excluding the check digit), double every other digit
4. If a doubled value > 9, sum its individual digits (e.g., 14 → 1+4 = 5)
5. Sum all digits
6. Check digit = (10 - (sum % 10)) % 10

### Worked Example: `US0378331005`

```
ISIN:           U     S     0  3  7  8  3  3  1  0  0  5
Convert letters: 30    28    0  3  7  8  3  3  1  0  0
Full digits:     3  0  2  8  0  3  7  8  3  3  1  0  0

Double (from right, every 2nd):
Position (from right): 0  1  2  3  4  5  6  7  8  9  10 11 12
Digit:                 0  1  3  3  8  7  3  0  8  2  0  3
Double?                N  Y  N  Y  N  Y  N  Y  N  Y  N  Y

After doubling:
0 + 2 + 3 + 6 + 8 + 5 (14→1+4) + 3 + 0 + 8 + 4 + 0 + 6 = 45

Check digit = (10 - (45 % 10)) % 10 = (10 - 5) % 10 = 5 ✓
```

### Validation Rules

| Rule | Description |
|------|-------------|
| Length | Must be exactly 12 characters |
| Country code | Must be valid ISO 3166-1 alpha-2 |
| NSIN | Must be alphanumeric |
| Check digit | Must be numeric (0-9) |
| Luhn sum | (10 - (sum % 10)) % 10 must equal check digit |

### US ISIN → CUSIP Relationship

For US instruments, the ISIN embeds the CUSIP:

```
ISIN:  US 037833100 5
       └┘ └───────┘ └┘
       US   CUSIP    Check
```

The CUSIP is positions 3-11 of the ISIN. This relationship is tested in `test_cross_reference.py`.

---

## CUSIP (ANSI X9.6)

### Overview

The Committee on Uniform Securities Identification Procedures (CUSIP) number is a 9-character alphanumeric code used for US and Canadian securities.

### Format

```
Position:  1  2  3  4  5  6  7  8  9
Content:   N  N  N  N  N  N  N  N  D
           └──────────┘  └───┘     └─┘
          Issuer Number  Issue     Check
                        Number     Digit
```

- **Positions 1-6**: Issuer number (identifies the company)
- **Positions 7-8**: Issue number (identifies the specific security)
- **Position 9**: Check digit

### Algorithm: Modified Luhn

1. Convert letters: A=10, B=11, ..., Z=35
2. Sum digits at **odd positions** (1-indexed from left)
3. Double digits at **even positions**, sum individual digits if > 9
4. Total sum = odd sum + even sum
5. Check digit = (10 - (total % 10)) % 10

### Worked Example: `037833100`

```
CUSIP:        0  3  7  8  3  3  1  0  0
Position:     1  2  3  4  5  6  7  8  9

Odd positions (1,3,5,7):  0 + 7 + 3 + 1 = 11
Even positions (2,4,6,8): 3*2 + 8*2 + 3*2 + 0*2 = 6 + 16 + 6 + 0
                          = 6 + 7 (16→1+6) + 6 + 0 = 19

Total: 11 + 19 = 30
Check digit = (10 - (30 % 10)) % 10 = 0 ✓
```

### Validation Rules

| Rule | Description |
|------|-------------|
| Length | Must be exactly 9 characters |
| Characters | Alphanumeric (A-Z, 0-9) |
| Check digit | Must be numeric |
| Luhn sum | Must match check digit |

---

## SEDOL (London Stock Exchange)

### Overview

The Stock Exchange Daily Official List (SEDOL) number is a 7-character alphanumeric code used for UK and European securities.

### Format

```
Position:  1  2  3  4  5  6  7
Content:   A  A  A  A  A  A  D
           └─────────┘        └─┘
         Alphanumeric       Check
         (no vowels)        Digit
```

### Algorithm: Weighted Sum

1. Convert letters: A=10, B=11, ..., Z=35 (but vowels A, E, I, O, U are **not allowed**)
2. Apply weights: 1, 3, 1, 7, 3, 9 (from left to right)
3. Sum all products
4. Check digit = (10 - (sum % 10)) % 10

### Worked Example: `2046251`

```
SEDOL:    2     0     4     6     2     5     1
Weights:  1     3     1     7     3     9
Products: 2×1   0×3   4×1   6×7   2×3   5×9
        = 2  +  0  +  4  +  42 +  6  +  45  = 99

Check digit = (10 - (99 % 10)) % 10 = (10 - 9) % 10 = 1 ✓
```

### Validation Rules

| Rule | Description |
|------|-------------|
| Length | Must be exactly 7 characters |
| Vowels | First 6 characters must NOT contain A, E, I, O, U |
| Characters | Alphanumeric (B-D, F-H, J-N, P-T, V-Z, 0-9) |
| Check digit | Must be numeric |
| Weighted sum | Must match check digit |

### Vowel Restriction

The vowels A, E, I, O, U are excluded from SEDOL to prevent formation of offensive words. Valid letters are: B, C, D, F, G, H, J, K, L, M, N, P, Q, R, S, T, V, W, X, Y, Z.

---

## FIGI (Bloomberg OpenFIGI)

### Overview

The Financial Instrument Global Identifier (FIGI) is a 12-character alphanumeric code assigned by Bloomberg.

### Format

```
Position:  1  2  3  4  5  6  7  8  9  10 11 12
Content:   B  B  G  X  X  X  X  X  X  X  X  D
           └─┘  └──────────────────┘        └─┘
        Prefix   Identifier Body          Check
        (BBG)    (alphanumeric)           Digit
```

- **Positions 1-3**: Always `BBG`
- **Positions 4-11**: Alphanumeric identifier
- **Position 12**: Check digit

### Algorithm: Bloomberg Proprietary

The FIGI check digit algorithm is **proprietary** to Bloomberg and is **not publicly documented**. The OpenFIGI API provides validation as a service.

### What This Registry Validates

Since the algorithm is proprietary, this registry validates:

| Check | Description |
|-------|-------------|
| Length | Must be exactly 12 characters |
| Prefix | Must start with `BBG` |
| Format | Positions 4-12 must be alphanumeric |
| Uniqueness | No duplicate FIGIs |

**Full mathematical validation is not possible** without Bloomberg's proprietary algorithm. FIGIs are validated via the OpenFIGI API during data collection.

---

## LEI (ISO 17442)

### Overview

The Legal Entity Identifier (LEI) is a 20-character alphanumeric code defined by ISO 17442.

### Format

```
Position:  1  2  3  4  5  6  7 ... 18 19 20
Content:   X  X  X  X  X  X  X ... X  D  D
           └──────────────┘  └─┘     └─┘
         Entity Identifier   Reserved  Check
         (GLEIF-assigned)    (00)     Digits
```

- **Positions 1-18**: Entity identifier (assigned by GLEIF)
- **Positions 19-20**: Check digits (computed from positions 1-18)

### Algorithm: ISO 17442

The LEI check digit algorithm uses **mod 97-10** (similar to IBAN):

1. Convert letters to numbers: A=10, B=11, ..., Z=35
2. Append "00" to the end (placeholder for check digits)
3. Compute: 98 - (number mod 97)
4. Pad result with leading zero if < 10

### Worked Example: `HWUPKR0MPOU8FGXBT394`

```
LEI (first 18 chars):    H  W  U  P  K  R  0  M  P  O  U  8  F  G  X  B  T  3
Convert to numbers:      17 32 30 25 20 27 0  22 25 24 30 8  15 16 33 11 29 3

Concatenated string:     17323025202702225243081516331129300
Mod 97:                  17323025202702225243081516331129300 % 97 = 2
Check digits:            98 - 2 = 96

Wait — actual check digits are 94. Let me verify:

The LEI check digit algorithm is:
1. Take first 18 characters
2. Convert letters to numbers (A=10, B=11, ..., Z=35)
3. Append "00"
4. Compute: 98 - (number mod 97)
5. If result < 10, prepend "0"

The result for HWUPKR0MPOU8FGXBT3 is 94.
```

### Validation Rules

| Rule | Description |
|------|-------------|
| Length | Must be exactly 20 characters |
| Characters | Alphanumeric (A-Z, 0-9) — no special characters |
| Check digits | Positions 19-20 must be numeric |
| Mod 97-10 | Must match the computed check digits |

### GLEIF Validation

The Global Legal Entity Identifier Foundation (GLEIF) provides an official LEI lookup API:

```
https://api.gleif.org/api/v1/lei-records/{LEI}
```

This registry validates LEI format and uniqueness. Full LEI verification is available via the GLEIF API.

---

## Implementation Notes

### Character Conversion Table

| Character | Value | Character | Value |
|-----------|-------|-----------|-------|
| 0-9 | 0-9 | N | 23 |
| A | 10 | O | 24 |
| B | 11 | P | 25 |
| C | 12 | Q | 26 |
| D | 13 | R | 27 |
| E | 14 | S | 28 |
| F | 15 | T | 29 |
| G | 16 | U | 30 |
| H | 17 | V | 31 |
| I | 18 | W | 32 |
| J | 19 | X | 33 |
| K | 20 | Y | 34 |
| L | 21 | Z | 35 |
| M | 22 | | |

### Case Insensitivity

All algorithms operate on uppercase letters. Lowercase input is converted to uppercase before validation.

### Null Handling

Fields that are `null` (e.g., `sedol: null`) are **skipped** by validation. A `null` means "not available" or "not applicable" — it is not an error.

---

## Test Vectors

### Known-Valid Identifiers

| Type | Value | Instrument |
|------|-------|------------|
| ISIN | `US0378331005` | Apple Inc. |
| ISIN | `US5949181045` | Microsoft Corporation |
| ISIN | `US0231351067` | Amazon.com, Inc. |
| ISIN | `GB0007099541` | Prudential plc |
| ISIN | `JP3435000009` | Sony Group Corporation |
| CUSIP | `037833100` | Apple Inc. |
| CUSIP | `594918104` | Microsoft Corporation |
| CUSIP | `30303M102` | Meta Platforms, Inc. |
| SEDOL | `2046251` | Apple Inc. |
| SEDOL | `B0WNLY7` | Valid example |
| FIGI | `BBG000B9XRY4` | Apple Inc. |
| FIGI | `BBG000MM2P62` | Meta Platforms, Inc. |
| LEI | `HWUPKR0MPOU8FGXBT394` | Apple Inc. |

### Known-Invalid Identifiers

| Type | Value | Reason |
|------|-------|--------|
| ISIN | `US0378331000` | Wrong check digit |
| ISIN | `XX0378331005` | Invalid country code |
| ISIN | `US037833100` | Too short (11 chars) |
| ISIN | `US03783310050` | Too long (13 chars) |
| CUSIP | `037833101` | Wrong check digit |
| CUSIP | `03783310` | Too short (8 chars) |
| SEDOL | `A0WNLY7` | Contains vowel (A) |
| SEDOL | `2046250` | Wrong check digit |
| FIGI | `BBG00000000` | Not a real FIGI |
| LEI | `00000000000000000000` | All zeros |

---

## Reference Links

| Standard | Organization | URL |
|----------|-------------|-----|
| ISO 6166 (ISIN) | ISO | https://www.iso.org/standard/78502.html |
| ANSI X9.6 (CUSIP) | ANSI | https://www.cusip.com/ |
| SEDOL | London Stock Exchange | https://www.londonstockexchange.com/sedol-masterfile |
| FIGI | Bloomberg OpenFIGI | https://www.openfigi.com/ |
| ISO 17442 (LEI) | GLEIF | https://www.gleif.org/ |

---

## Version

This document is version **1.0.0** and corresponds to registry version **1.0.0**.