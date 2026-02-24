"""
api.py — FastAPI app exposing clinical trials data.
Includes a background scheduler that runs sync.py daily at 2am UTC.
"""

from fastapi import FastAPI, Query
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from database import get_since, init_db
from sync import main as run_sync

app = FastAPI(title="Clinical Trials API")
scheduler = BackgroundScheduler()


@app.on_event("startup")
def startup() -> None:
    init_db()
    scheduler.add_job(run_sync, CronTrigger(hour=2, minute=0, timezone="UTC"))
    scheduler.start()


@app.on_event("shutdown")
def shutdown() -> None:
    scheduler.shutdown()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/trials")
def get_trials(since: str = Query(..., description="ISO date string e.g. 2026-02-20")):
    trials = get_since(since)
    return {"count": len(trials), "trials": trials}
