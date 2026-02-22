"""
sync.py — Daily sync script. Fetches trials updated yesterday and upserts them.
Intended to run on a daily cron job.
"""

from datetime import date, timedelta
from database import init_db, upsert
from fetcher import fetch_trials
from normalizer import normalize


def main() -> None:
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    print(f"Syncing trials updated since {yesterday} …\n")

    init_db()
    raw_trials = fetch_trials(since_date=yesterday)

    count = 0
    for raw in raw_trials:
        upsert(normalize(raw))
        count += 1

    print(f"\nDone. {count} trial(s) updated.")


if __name__ == "__main__":
    main()
