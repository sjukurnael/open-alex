"""
api.py — FastAPI app exposing clinical trials data.
"""

from fastapi import FastAPI, Query
from database import get_since, init_db

app = FastAPI(title="Clinical Trials API")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/trials")
def get_trials(since: str = Query(..., description="ISO date string e.g. 2026-02-20")):
    trials = get_since(since)
    return {"count": len(trials), "trials": trials}
