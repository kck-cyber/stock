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


@app.get("/stock")
def stock(
    code: str,
    name: str | None = None,
    preset: str = "균형형",
) -> dict[str, Any]:
    """Compatibility endpoint for one-stock analysis."""
    stock_name = name or code

    try:
        records = get_bridge().build_records(
            [{"code": code, "name": stock_name}],
            preset=preset,
            analyze=True,
            max_workers=1,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not records:
        raise HTTPException(status_code=404, detail="stock not found")

    return {
        "record": records[0],
        "loaded_at": f"{datetime.now():%Y-%m-%d %H:%M}",
    }


@app.post("/stock")
def stock_post(payload: dict[str, Any]) -> dict[str, Any]:
    code = str(payload.get("code") or "").strip()

    if not code:
        raise HTTPException(status_code=400, detail="code is required")

    return stock(
        code=code,
        name=payload.get("name"),
        preset=str(payload.get("preset") or "균형형"),
    )


@app.get("/news")
def news_compat(
    name: str | None = None,
    code: str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    keyword = (name or code or "").strip()

    if not keyword:
        raise HTTPException(status_code=400, detail="name or code is required")

    return news(keyword, limit=limit)


@app.post("/news")
def news_post(payload: dict[str, Any]) -> dict[str, Any]:
    return news_compat(
        name=payload.get("name"),
        code=payload.get("code"),
        limit=int(payload.get("limit") or 5),
    )


@app.post("/chat")
def chat(payload: dict[str, Any]) -> dict[str, Any]:
    message = str(payload.get("message") or payload.get("prompt") or "").strip()
    stocks = payload.get("stocks") or []

    if not message and not stocks:
        raise HTTPException(
            status_code=400,
            detail="message or stocks is required",
        )

    if stocks and not isinstance(stocks, list):
        raise HTTPException(status_code=400, detail="stocks must be a list")

    records_result: dict[str, Any] | None = None

    if stocks:
        records_result = records({
            "stocks": stocks,
            "holdings": payload.get("holdings") or {},
            "preset": payload.get("preset") or "균형형",
            "analyze": payload.get("analyze", True),
            "max_workers": payload.get("max_workers") or 4,
        })

    record_items = (records_result or {}).get("records") or []
    top_items = record_items[:3]

    if top_items:
        summary = ", ".join(
            f"{item.get('name', item.get('code'))} {item.get('final_score', 0):.1f}점"
            for item in top_items
        )
        answer = (
            f"분석 기준으로 상위 종목은 {summary}입니다. "
            "각 종목의 factor_scores와 score_reason을 함께 확인하면 "
            "점수 근거를 더 정확히 볼 수 있습니다."
        )
    else:
        answer = (
            "현재 서버는 실시간 대화형 AI 모델 대신 주식 분석 API를 제공합니다. "
            "stocks 목록을 함께 보내면 퀀트/뉴스 점수와 요약을 반환합니다."
        )

    return {
        "answer": answer,
        "message": message,
        "records": record_items,
        "loaded_at": f"{datetime.now():%Y-%m-%d %H:%M}",
    }
