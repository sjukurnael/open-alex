"""
load.py — Full load script.
Fetches all trials from ClinicalTrials.gov, normalizes, and upserts into trials.db.
"""

import time
from database import init_db, upsert
from fetcher import fetch_trials
from normalizer import normalize


def main() -> None:
    init_db()

    print("Starting full load — fetching all trials (this will take a while) …\n")
    start = time.time()

    raw_trials = fetch_trials()  # no date filter = all trials

    total = len(raw_trials)
    print(f"\nFetched {total} trials. Beginning normalize + upsert …\n")

    for i, raw in enumerate(raw_trials, 1):
        upsert(normalize(raw))
        if i % 1000 == 0:
            elapsed = time.time() - start
            print(f"  Processed {i} / {total}  ({elapsed:.0f}s elapsed)")

    elapsed = time.time() - start
    print(f"\nDone. {total} trials loaded in {elapsed:.1f}s.")


if __name__ == "__main__":
    main()
