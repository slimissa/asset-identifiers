#!/bin/bash
# Run Yahoo Finance fetcher in small batches with cooldown
# Usage: bash tools/fetch_yahoo_batch_runner.sh

BATCH_SIZE=20
COOLDOWN=90  # 90 seconds between batches

while true; do
    echo "$(date): Running batch of $BATCH_SIZE tickers..."
    python3 tools/fetch_yahoo_cusip.py --limit "$BATCH_SIZE" 2>&1 | tail -5

    # Check if any tickers left
    REMAINING=$(python3 -c "
import json
with open('identifiers.json') as f:
    data = json.load(f)
missing = sum(1 for i in data['instruments'] if not i.get('isin'))
print(missing)
")
    echo "$(date): $REMAINING tickers still missing ISIN"

    if [ "$REMAINING" -eq 0 ]; then
        echo "$(date): ALL DONE!"
        break
    fi

    echo "$(date): Cooling down for $COOLDOWN seconds..."
    sleep $COOLDOWN
done
