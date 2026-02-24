"""
database.py — SQLite persistence for clinical trials.
"""

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "trials.db"

# List fields that are stored as JSON strings in SQLite
LIST_FIELDS = {
    "phases",
    "conditions",
    "interventions",
    "mesh_terms",
    "drug_mesh_terms",
    "countries",
}

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS trials (
    nct_id          TEXT PRIMARY KEY,
    brief_title     TEXT,
    official_title  TEXT,
    status          TEXT,
    study_type      TEXT,
    phases          TEXT,
    start_date      TEXT,
    completion_date TEXT,
    last_updated    TEXT,
    sponsor         TEXT,
    sponsor_class   TEXT,
    conditions      TEXT,
    interventions   TEXT,
    mesh_terms      TEXT,
    drug_mesh_terms TEXT,
    countries       TEXT,
    enrollment      INTEGER,
    sex             TEXT,
    min_age         TEXT,
    max_age         TEXT,
    has_results     INTEGER,
    source_url      TEXT
);
"""

CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_last_updated ON trials (last_updated);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create table and index if they don't exist."""
    with _connect() as conn:
        conn.execute(CREATE_TABLE)
        conn.execute(CREATE_INDEX)


def is_empty() -> bool:
    """Return True if the trials table has no rows."""
    with _connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM trials").fetchone()[0]
    return count == 0


def _serialize(trial: dict) -> dict:
    """Serialize a normalized trial dict for SQLite storage."""
    row = {}
    for key, value in trial.items():
        if key in LIST_FIELDS:
            row[key] = json.dumps(value)
        elif key == "has_results":
            row[key] = 1 if value else 0
        else:
            row[key] = value
    return row


def upsert(trial: dict) -> None:
    """Insert a trial or update it if the nct_id already exists."""
    row = _serialize(trial)
    columns = ", ".join(row.keys())
    placeholders = ", ".join("?" * len(row))
    updates = ", ".join(f"{k} = excluded.{k}" for k in row if k != "nct_id")
    sql = f"""
        INSERT INTO trials ({columns}) VALUES ({placeholders})
        ON CONFLICT(nct_id) DO UPDATE SET {updates};
    """
    with _connect() as conn:
        conn.execute(sql, list(row.values()))


def upsert_many(trials: list[dict]) -> None:
    """Upsert a batch of trials in a single transaction."""
    if not trials:
        return
    rows = [_serialize(t) for t in trials]
    columns = ", ".join(rows[0].keys())
    placeholders = ", ".join("?" * len(rows[0]))
    updates = ", ".join(f"{k} = excluded.{k}" for k in rows[0] if k != "nct_id")
    sql = f"""
        INSERT INTO trials ({columns}) VALUES ({placeholders})
        ON CONFLICT(nct_id) DO UPDATE SET {updates};
    """
    with _connect() as conn:
        conn.executemany(sql, [list(r.values()) for r in rows])


def get_since(date_str: str) -> list[dict]:
    """Return all trials where last_updated >= date_str."""
    sql = "SELECT * FROM trials WHERE last_updated >= ?"
    with _connect() as conn:
        rows = conn.execute(sql, (date_str,)).fetchall()

    results = []
    for row in rows:
        trial = dict(row)
        for field in LIST_FIELDS:
            trial[field] = json.loads(trial[field] or "[]")
        trial["has_results"] = bool(trial["has_results"])
        results.append(trial)
    return results


# ---------------------------------------------------------------------------
# Quick test — insert 5 normalized trials, then query them back
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json as _json
    from fetcher import fetch_trials
    from normalizer import normalize

    init_db()
    print(f"Database initialised at {DB_PATH}\n")

    print("Fetching 5 trials …")
    raw_trials = fetch_trials(since_date="2026-02-20")
    sample = raw_trials[:5]

    print("Inserting 5 normalized trials …")
    for raw in sample:
        upsert(normalize(raw))

    # Query back using the earliest last_updated among the 5
    normalized_sample = [normalize(r) for r in sample]
    min_date = min(t["last_updated"] for t in normalized_sample if t["last_updated"])

    results = get_since(min_date)
    print(f"\nQueried back {len(results)} trial(s) with last_updated >= {min_date}\n")

    for t in results:
        print(f"  {t['nct_id']} | {t['status']} | phases={t['phases']} | countries={t['countries']}")
