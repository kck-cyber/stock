from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware


APP_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = APP_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def make_bridge():
    from morning_stock_assistant.shared import SharedAnalysisBridge

    cache_dir = Path(os.getenv("CACHE_DIR", "/tmp/morning-stock-cache"))
    return SharedAnalysisBridge(
        api_key=os.getenv("DART_API_KEY", ""),
        cache_dir=cache_dir,
        year=os.getenv("ANALYSIS_YEAR", "2025"),
        report_code=os.getenv("REPORT_CODE", "11011"),
    )


app = FastAPI(
    title="Morning Stock Assistant API",
    version="0.2.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

bridge = None


def get_bridge():
    global bridge

    if bridge is None:
        bridge = make_bridge()

    return bridge


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "app": "Morning Stock Assistant API",
        "status": "ok",
        "time": f"{datetime.now():%Y-%m-%d %H:%M:%S}",
    }


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok"}


@app.post("/api/records")
def records(payload: dict[str, Any]) -> dict[str, Any]:
    stocks = payload.get("stocks") or []

    if not isinstance(stocks, list):
        raise HTTPException(status_code=400, detail="stocks must be a list")

    holdings = payload.get("holdings") or {}

    if not isinstance(holdings, dict):
        raise HTTPException(status_code=400, detail="holdings must be an object")

    preset = str(payload.get("preset") or "균형형")
    analyze = bool(payload.get("analyze", True))
    max_workers = int(payload.get("max_workers") or 4)
    max_workers = max(1, min(max_workers, 6))

    try:
        result = get_bridge().build_records(
            stocks,
            holdings=holdings,
            preset=preset,
            analyze=analyze,
            max_workers=max_workers,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "records": result,
        "count": len(result),
        "loaded_at": f"{datetime.now():%Y-%m-%d %H:%M}",
    }


@app.get("/api/chart/{code}")
def chart(code: str, period: str = "1mo", interval: str | None = None) -> dict[str, Any]:
    values = get_bridge().chart_values(code, period=period, interval=interval)
    return {
        "code": code.upper(),
        "period": period,
        "interval": interval,
        "values": values,
    }


@app.get("/api/news")
def news(name: str, limit: int = 5) -> dict[str, Any]:
    limit = max(1, min(int(limit), 20))
    return {
        "name": name,
        "items": get_bridge().news_items(name, limit=limit),
    }
