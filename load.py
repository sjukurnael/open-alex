"""
load.py — Full load script.
Fetches all trials page by page (1000 at a time), normalizes and upserts each
page before fetching the next — never holding more than one page in memory.
"""

import time
import httpx
from database import init_db, upsert_many
from normalizer import normalize

BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
PAGE_SIZE = 1000
SLEEP_BETWEEN = 0.5
RETRY_429_WAIT = 60


def main() -> None:
    init_db()
    start = time.time()
    processed = 0
    total = None

    params: dict = {"pageSize": PAGE_SIZE, "format": "json"}

    print("Starting full load …\n")

    with httpx.Client(timeout=30) as client:
        while True:
            # Fetch one page with 429 retry
            while True:
                response = client.get(BASE_URL, params=params)
                if response.status_code == 429:
                    print(f"  Rate limited (429). Waiting {RETRY_429_WAIT}s …")
                    time.sleep(RETRY_429_WAIT)
                    continue
                response.raise_for_status()
                break

            data = response.json()

            if total is None:
                total = data.get("totalCount", "?")
                print(f"Total trials reported by API: {total}\n")

            studies = data.get("studies", [])

            # Normalize and upsert the whole page in one transaction
            upsert_many([normalize(s) for s in studies])

            processed += len(studies)
            elapsed = time.time() - start
            print(f"  Processed {processed} / {total}  ({elapsed:.0f}s elapsed)")

            next_token = data.get("nextPageToken")
            if not next_token:
                break

            params["pageToken"] = next_token
            time.sleep(SLEEP_BETWEEN)

    elapsed = time.time() - start
    print(f"\nDone. {processed} trials loaded in {elapsed:.1f}s.")


if __name__ == "__main__":
    main()
