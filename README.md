# Clinical Trials ETL Pipeline

A lightweight ETL pipeline that pulls data from [ClinicalTrials.gov API v2](https://clinicaltrials.gov/data-api/api), stores it in SQLite, and exposes it via a FastAPI endpoint.

---

## What this project does

1. **Full load** (`load.py`) — fetches all ~572k trials from ClinicalTrials.gov and stores them in a local SQLite database (`trials.db`). Only runs once on first deploy when the DB is empty — subsequent deploys skip this step.
2. **Daily sync** (`sync.py`) — fetches only trials updated since yesterday and upserts them, keeping the DB current
3. **API** (`api.py`) — serves trial data over HTTP so downstream systems (e.g. OpenAlex) can query by last-updated date

---

## How to run locally

### Install dependencies
```bash
pip install -r requirements.txt
```

### Run the full load (one-time, takes ~10 min)
```bash
python load.py
```

> On Render, this runs automatically on first deploy via `start.sh` when the DB is empty. Subsequent deploys skip it.

### Start the API
```bash
uvicorn api:app --reload --port 8080
```

### Test the API
```bash
curl http://localhost:8080/health
curl "http://localhost:8080/trials?since=2026-02-20"
```

### Run the daily sync manually
```bash
python sync.py
```

---

## Schema

| Field | Type | Notes |
|---|---|---|
| `nct_id` | str | Primary key, e.g. `NCT07137416` |
| `brief_title` | str | Short human-readable title |
| `official_title` | str | Full protocol title |
| `status` | str | e.g. `RECRUITING`, `COMPLETED`, `TERMINATED` |
| `study_type` | str | `INTERVENTIONAL` or `OBSERVATIONAL` |
| `phases` | list | e.g. `["PHASE1"]` or `["NA"]` |
| `start_date` | str | Study start date |
| `completion_date` | str | Estimated or actual completion date |
| `last_updated` | str | **Used for syncing** — date record was last updated on ClinicalTrials.gov |
| `sponsor` | str | Lead sponsor name |
| `sponsor_class` | str | `INDUSTRY`, `NIH`, `FED`, `OTHER` |
| `conditions` | list | Medical conditions being studied |
| `interventions` | list | `[{"type": str, "name": str}]` |
| `mesh_terms` | list | Condition MeSH terms from NLM |
| `drug_mesh_terms` | list | Intervention MeSH terms from NLM |
| `countries` | list | Unique countries where trial sites are located |
| `enrollment` | int | Target or actual enrollment count |
| `sex` | str | `ALL`, `MALE`, or `FEMALE` |
| `min_age` | str | e.g. `18 Years` |
| `max_age` | str | e.g. `85 Years` |
| `has_results` | bool | Whether results have been posted |
| `source_url` | str | Direct link to trial on ClinicalTrials.gov |

### Why these fields?

- **`last_updated`** is the core field enabling incremental sync — without it the pipeline would need to re-fetch everything daily
- **`mesh_terms` / `drug_mesh_terms`** are NLM-standardised vocabulary, making them far more useful for cross-referencing with OpenAlex than free-text condition names
- **`sponsor_class`** lets consumers quickly filter by funding source (industry vs. NIH vs. government)
- **`interventions`** structured as `{type, name}` pairs preserves enough detail for drug/device queries without the full arms breakdown

---

## What was deliberately left out

| Omitted | Reason |
|---|---|
| Eligibility criteria text | Long free-text blob, not useful for structured queries, adds ~30% to DB size |
| Full location detail (city, facility name, coordinates) | Only `country` is needed for geographic filtering; full detail would require a separate table |
| References / citations | Not relevant to the downstream OpenAlex use case |
| Collaborators | Lead sponsor is sufficient for most filtering; collaborators add complexity for marginal gain |
| Outcome measures | Highly variable free text; would need a separate table to be useful |
| Arms / groups detail | Interventions list captures the key drug/device info without the full arms structure |

---

## How the sync works

The daily sync is handled by APScheduler running inside the FastAPI process — no external cron job or Render cron service needed. On app startup, a background scheduler is registered that fires `sync.main()` every day at 2am UTC.

1. At 2am UTC, the scheduler calls `sync.py` — no external trigger required
2. `sync.py` calls `fetch_trials(since_date=yesterday)` — ClinicalTrials.gov supports date-range filtering natively via `AREA[LastUpdatePostDate]RANGE[date,MAX]`
3. All returned trials are upserted (`INSERT ... ON CONFLICT DO UPDATE`) so new trials are added and updated trials overwrite the old record
4. The `last_updated` index ensures `get_since()` queries stay fast even at 572k rows

To trigger a sync manually (e.g. to backfill missed days):
```
GET /sync
```

---

## How OpenAlex should integrate

Call the `/trials` endpoint daily with the date of the last successful sync:

```
GET /trials?since=2026-02-21
```

This returns only trials that changed since that date, keeping the integration lightweight. Suggested flow:

1. Store `last_sync_date` in OpenAlex
2. Each day: `GET /trials?since={last_sync_date}`
3. Process returned trials and index/link them as needed
4. Update `last_sync_date = today`

---

## Trade-offs made

- **SQLite over Postgres** — sufficient for 572k rows with simple queries; avoids infrastructure complexity. Can be swapped for Postgres with minimal code changes if concurrent writes become necessary.
- **Flat table over normalised schema** — list fields stored as JSON strings keeps the schema simple and avoids joins. The trade-off is you can't efficiently query *inside* lists (e.g. "trials with mesh term X") from SQL alone, but that filtering can happen in the API layer.
- **No async fetching** — the fetcher uses synchronous `httpx` with `sleep(0.5)`. An async fetcher could be ~5x faster but adds complexity and risks hitting rate limits.
- **No authentication on the API** — appropriate for an internal service; add an API key header if this becomes public-facing.
- **Render persistent disk for SQLite** — simple and cheap, but means the DB lives on a single instance. If horizontal scaling is needed, migrate to a hosted database.
- **Encoding mojibake in upstream data** — a small number of records from ClinicalTrials.gov contain mangled UTF-8/Latin-1 encoding (e.g. `TÃ¼rkiye` instead of `Türkiye`). This is an upstream API issue, not a pipeline bug. Not fixed to avoid introducing a dependency (`ftfy`) for a rare edge case; revisit if the API doesn't resolve it.
- **Render free tier spin-down** — the free tier spins down after inactivity, meaning the first request after an idle period takes ~30 seconds to wake up. Currently on the Starter paid tier ($7/month) to avoid this, but worth noting for cost review.
