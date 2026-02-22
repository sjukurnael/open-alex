"""
fetcher.py — ClinicalTrials.gov API v2 fetcher
Fetches all studies (or studies updated since a given date) using cursor pagination.
"""

import time
import httpx

BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
PAGE_SIZE = 1000
SLEEP_BETWEEN = 0.5   # seconds between successful requests
RETRY_429_WAIT = 60   # seconds to wait on rate-limit


def fetch_trials(since_date: str | None = None) -> list[dict]:
    """
    Fetch all trials from ClinicalTrials.gov.

    Args:
        since_date: Optional ISO date string (e.g. "2026-02-19").
                    If provided, only trials with LastUpdatePostDate >= since_date
                    are returned.

    Returns:
        List of raw study dicts as returned by the API.
    """
    params: dict = {"pageSize": PAGE_SIZE, "format": "json"}

    if since_date:
        params["query.term"] = f"AREA[LastUpdatePostDate]RANGE[{since_date},MAX]"

    studies: list[dict] = []
    page = 0

    with httpx.Client(timeout=30) as client:
        while True:
            response = _get_with_retry(client, BASE_URL, params)
            data = response.json()

            page_studies = data.get("studies", [])
            studies.extend(page_studies)
            page += 1
            print(f"  Fetched page {page} — {len(studies)} trials so far")

            next_token = data.get("nextPageToken")
            if not next_token:
                break

            params["pageToken"] = next_token
            time.sleep(SLEEP_BETWEEN)

    return studies


def _get_with_retry(client: httpx.Client, url: str, params: dict) -> httpx.Response:
    """GET with automatic retry on 429."""
    while True:
        response = client.get(url, params=params)
        if response.status_code == 429:
            print(f"  Rate limited (429). Waiting {RETRY_429_WAIT}s …")
            time.sleep(RETRY_429_WAIT)
            continue
        response.raise_for_status()
        return response


# ---------------------------------------------------------------------------
# Quick test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    SINCE = "2026-02-20"
    print(f"Fetching trials updated since {SINCE} …\n")

    trials = fetch_trials(since_date=SINCE)

    print(f"\nTotal trials returned : {len(trials)}")

    if trials:
        first = trials[0]
        nct_id = (
            first.get("protocolSection", {})
                 .get("identificationModule", {})
                 .get("nctId", "N/A")
        )
        print(f"First result nctId   : {nct_id}")
