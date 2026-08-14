#!/usr/bin/env python3
"""Fetch real FIGI from OpenFIGI API."""

import json
import time
import requests
from pathlib import Path

def fetch_figi(ticker, exchange_code):
    """Fetch FIGI from OpenFIGI for a ticker on an exchange."""
    url = "https://api.openfigi.com/v3/mapping"
    headers = {"Content-Type": "application/json"}
    payload = [{"idType": "TICKER", "idValue": ticker, "exchCode": exchange_code}]
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, list) and len(data) > 0:
                first = data[0]
                if "data" in first and first["data"]:
                    return first["data"][0]
                elif "error" in first:
                    print(f"    OpenFIGI error: {first['error']}")
        else:
            print(f"    HTTP {response.status_code}")
    except Exception as e:
        print(f"    Request failed: {e}")
    
    return None

def main():
    data_path = Path("identifiers.json")
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    exch_map = {
        "XNAS": "US",
        "XNYS": "US",
        "XLON": "LN",
        "XTKS": "JP",
        "XHKG": "HK",
        "XETR": "GY",
        "XPAR": "FP",
        "XSWX": "SW",
        "XKRX": "KS",
    }
    
    updated = 0
    
    for instrument in data["instruments"]:
        ticker = instrument.get("ticker")
        exchange = instrument.get("exchange")
        exch_code = exch_map.get(exchange, "US")
        
        print(f"Fetching {ticker} on {exch_code}...")
        result = fetch_figi(ticker, exch_code)
        
        if result:
            figi = result.get("figi")
            if figi:
                instrument["figi"] = figi
                print(f"    FIGI: {figi}")
                updated += 1
            else:
                print(f"    No FIGI in response")
        else:
            print(f"    No data returned")
        
        time.sleep(1)  # Rate limiting
    
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\nUpdated {updated} FIGI(s)")

if __name__ == "__main__":
    main()