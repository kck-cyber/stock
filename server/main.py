from __future__ import annotations

import os
import json
import sys
import time
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

    cache_dir = Path(os.getenv("CACHE_DIR") or APP_ROOT / "cache")
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
records_cache: dict[str, tuple[float, dict[str, Any]]] = {}
chart_cache: dict[str, tuple[float, dict[str, Any]]] = {}
RECORDS_CACHE_TTL_SECONDS = 600
CHART_CACHE_TTL_SECONDS = 600
INTRADAY_CHART_CACHE_TTL_SECONDS = 120
STORAGE_DIR = Path(os.getenv("APP_STORAGE_DIR") or APP_ROOT / "storage")
LATEST_RECORDS_FILE = STORAGE_DIR / "latest_records.json"
ANALYSIS_HISTORY_FILE = STORAGE_DIR / "analysis_history.json"
EVENTS_FILE = STORAGE_DIR / "events.json"
USER_STRATEGIES_FILE = STORAGE_DIR / "user_strategies.json"


def get_bridge():
    global bridge

    if bridge is None:
        bridge = make_bridge()

    return bridge


def cache_key_for_records(payload: dict[str, Any], max_workers: int) -> str:
    key_payload = {
        "stocks": payload.get("stocks") or [],
        "holdings": payload.get("holdings") or {},
        "preset": str(payload.get("preset") or "균형형"),
        "analyze": bool(payload.get("analyze", True)),
        "max_workers": max_workers,
        "events": payload.get("events") or [],
        "user_strategies": payload.get("user_strategies") or {},
        "storage_version": storage_version(),
    }
    return json_dumps_for_cache(key_payload)


def json_dumps_for_cache(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )


def load_json_file(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default

        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json_file(path: Path, value: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
    except Exception:
        pass


def storage_version() -> dict[str, float]:
    version = {}

    for path in [
        LATEST_RECORDS_FILE,
        ANALYSIS_HISTORY_FILE,
        EVENTS_FILE,
        USER_STRATEGIES_FILE,
    ]:
        try:
            version[path.name] = path.stat().st_mtime
        except OSError:
            version[path.name] = 0

    return version


def get_records_cache(key: str) -> dict[str, Any] | None:
    cached = records_cache.get(key)

    if not cached:
        return None

    created_at, value = cached

    if time.time() - created_at > RECORDS_CACHE_TTL_SECONDS:
        records_cache.pop(key, None)
        return None

    copied = dict(value)
    copied["cached"] = True
    return copied


def set_records_cache(key: str, value: dict[str, Any]) -> None:
    if len(records_cache) > 200:
        oldest_key = min(
            records_cache,
            key=lambda item: records_cache[item][0],
        )
        records_cache.pop(oldest_key, None)

    records_cache[key] = (time.time(), dict(value))


def chart_cache_key(code: str, period: str, interval: str | None) -> str:
    return json_dumps_for_cache({
        "code": str(code or "").strip().upper(),
        "period": period or "1mo",
        "interval": interval or "",
    })


def chart_cache_ttl(period: str, interval: str | None) -> int:
    if period in {"1d", "5d"} or interval in {
        "1m",
        "2m",
        "5m",
        "15m",
        "30m",
        "60m",
        "90m",
        "1h",
    }:
        return INTRADAY_CHART_CACHE_TTL_SECONDS

    return CHART_CACHE_TTL_SECONDS


def get_chart_cache(key: str, ttl: int) -> dict[str, Any] | None:
    cached = chart_cache.get(key)

    if not cached:
        return None

    created_at, value = cached

    if time.time() - created_at > ttl:
        chart_cache.pop(key, None)
        return None

    copied = dict(value)
    copied["cached"] = True
    return copied


def set_chart_cache(key: str, value: dict[str, Any]) -> None:
    if len(chart_cache) > 500:
        oldest_key = min(
            chart_cache,
            key=lambda item: chart_cache[item][0],
        )
        chart_cache.pop(oldest_key, None)

    chart_cache[key] = (time.time(), dict(value))


def latest_records_by_code() -> dict[str, dict[str, Any]]:
    items = load_json_file(LATEST_RECORDS_FILE, {})

    if isinstance(items, dict):
        return {
            str(code).upper(): value
            for code, value in items.items()
            if isinstance(value, dict)
        }

    return {}


def history_by_code() -> dict[str, list[dict[str, Any]]]:
    items = load_json_file(ANALYSIS_HISTORY_FILE, {})

    if isinstance(items, dict):
        return {
            str(code).upper(): value
            for code, value in items.items()
            if isinstance(value, list)
        }

    return {}


def configured_events(payload: dict[str, Any]) -> list[dict[str, Any]]:
    stored = load_json_file(EVENTS_FILE, [])
    incoming = payload.get("events") or []

    if not isinstance(stored, list):
        stored = []
    if not isinstance(incoming, list):
        incoming = []

    return stored + incoming


def configured_user_strategies(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    stored = load_json_file(USER_STRATEGIES_FILE, {})
    incoming = payload.get("user_strategies") or {}

    if not isinstance(stored, dict):
        stored = {}
    if not isinstance(incoming, dict):
        incoming = {}

    merged = {
        str(code).upper(): value
        for code, value in stored.items()
        if isinstance(value, dict)
    }
    merged.update({
        str(code).upper(): value
        for code, value in incoming.items()
        if isinstance(value, dict)
    })
    return merged


def analysis_history_entry(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "analyzed_at": f"{datetime.now():%Y-%m-%d %H:%M:%S}",
        "stock_code": record.get("code"),
        "price_at_analysis": record.get("price"),
        "final_score": record.get("final_score"),
        "rating": record.get("rating") or record.get("grade"),
        "action_summary": record.get("action_summary"),
        "price_after_7d": None,
        "return_after_7d": None,
        "price_after_30d": None,
        "return_after_30d": None,
        "evaluation_result": None,
    }


def update_record_storage(records: list[dict[str, Any]]) -> None:
    latest = latest_records_by_code()
    history = history_by_code()

    for record in records:
        code = str(record.get("code") or "").upper()

        if not code:
            continue

        latest[code] = record
        entries = history.setdefault(code, [])
        entries.append(analysis_history_entry(record))
        history[code] = entries[-120:]

    save_json_file(LATEST_RECORDS_FILE, latest)
    save_json_file(ANALYSIS_HISTORY_FILE, history)


def portfolio_risk_summary(
    records: list[dict[str, Any]],
    holdings: dict[str, Any],
) -> dict[str, Any]:
    rows = []
    total_value = 0.0

    for record in records:
        code = str(record.get("code") or "").upper()
        holding = holdings.get(code, {}) if isinstance(holdings, dict) else {}
        quantity = safe_number(holding.get("quantity", 0))
        price = safe_number(record.get("price", 0))
        avg_price = safe_number(
            holding.get("average_price", holding.get("avg_price", 0))
        )
        value = quantity * price if quantity > 0 and price > 0 else 0
        cost = quantity * avg_price if quantity > 0 and avg_price > 0 else 0
        profit_rate = ((value - cost) / cost * 100) if cost > 0 and value > 0 else 0
        total_value += value
        rows.append({
            "code": code,
            "name": record.get("name", code),
            "value": value,
            "profit_rate": round(profit_rate, 2),
            "stock_type": record.get("stock_type"),
            "data_confidence": record.get("data_confidence"),
            "net_income": safe_number((record.get("finance") or {}).get("net_income", 0)),
            "volatility_flag": abs(safe_number(record.get("change_1d", 0))) >= 5,
            "market": record.get("market"),
        })

    def ratio_for(predicate) -> float:
        if total_value <= 0:
            return 0.0

        value = sum(row["value"] for row in rows if predicate(row))
        return round((value / total_value) * 100, 2)

    max_row = max(rows, key=lambda row: row["value"], default={})
    max_ratio = (
        round(safe_number(max_row.get("value", 0)) / total_value * 100, 2)
        if total_value > 0
        else 0.0
    )
    loss_top3 = sorted(
        [
            {
                "code": row["code"],
                "name": row["name"],
                "profit_rate": row["profit_rate"],
            }
            for row in rows
            if row["profit_rate"] < 0
        ],
        key=lambda item: item["profit_rate"],
    )[:3]
    high_risk_ratio = ratio_for(
        lambda row: row["stock_type"] in {"biotech", "small_cap"}
        or row["net_income"] < 0
        or row["volatility_flag"]
        or row["data_confidence"] == "low"
    )
    concentration_warning = (
        f"{max_row.get('name', max_row.get('code'))} 비중 {max_ratio:.1f}%로 집중도가 높습니다."
        if max_ratio >= 35
        else ""
    )
    risk_messages = []

    if high_risk_ratio >= 40:
        risk_messages.append("고위험 종목 비중이 높습니다.")
    if concentration_warning:
        risk_messages.append(concentration_warning)
    if loss_top3:
        risk_messages.append("손실 종목 상위 3개를 우선 점검하세요.")

    return {
        "total_value": round(total_value, 2),
        "high_risk_ratio": high_risk_ratio,
        "biotech_ratio": ratio_for(lambda row: row["stock_type"] == "biotech"),
        "overseas_growth_ratio": ratio_for(
            lambda row: row["market"] == "해외" and row["stock_type"] == "growth"
        ),
        "loss_company_ratio": ratio_for(lambda row: row["net_income"] < 0),
        "high_volatility_ratio": ratio_for(lambda row: row["volatility_flag"]),
        "low_confidence_ratio": ratio_for(lambda row: row["data_confidence"] == "low"),
        "largest_position_ratio": max_ratio,
        "loss_top3": loss_top3,
        "concentration_warning": concentration_warning,
        "risk_message": " ".join(risk_messages) if risk_messages else "포트폴리오 위험 신호는 제한적입니다.",
    }


def safe_number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


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
    cache_key = cache_key_for_records(payload, max_workers)
    cached = get_records_cache(cache_key)

    if cached is not None:
        return cached

    previous_records = latest_records_by_code()
    analysis_history = history_by_code()
    events = configured_events(payload)
    user_strategies = configured_user_strategies(payload)
    error = ""

    try:
        result = get_bridge().build_records(
            stocks,
            holdings=holdings,
            previous_records=previous_records,
            events=events,
            user_strategies=user_strategies,
            analysis_history=analysis_history,
            preset=preset,
            analyze=analyze,
            max_workers=max_workers,
        )
    except Exception as exc:
        result = []
        error = str(exc)

    try:
        update_record_storage(result)
    except Exception:
        pass

    try:
        portfolio_summary = portfolio_risk_summary(result, holdings)
    except Exception:
        portfolio_summary = {
            "total_value": 0,
            "high_risk_ratio": 0,
            "biotech_ratio": 0,
            "loss_top3": [],
            "concentration_warning": "",
            "risk_message": "포트폴리오 위험 요약을 계산하지 못했습니다.",
        }

    response = {
        "records": result,
        "count": len(result),
        "loaded_at": f"{datetime.now():%Y-%m-%d %H:%M}",
        "cached": False,
        "error": error,
        "portfolio_risk_summary": portfolio_summary,
    }
    set_records_cache(cache_key, response)
    return response


@app.get("/api/chart/{code}")
def chart(code: str, period: str = "1mo", interval: str | None = None) -> dict[str, Any]:
    cache_key = chart_cache_key(code, period, interval)
    cache_ttl = chart_cache_ttl(period, interval)
    cached = get_chart_cache(cache_key, cache_ttl)

    if cached is not None:
        return cached

    try:
        result = get_bridge().chart_data(code, period=period, interval=interval)
        result["cached"] = False
        set_chart_cache(cache_key, result)
        return result
    except Exception as exc:
        code_text = str(code or "").strip().upper()
        ticker = code_text

        if code_text.isdigit() and len(code_text) == 6:
            ticker = f"{code_text}.KS"

        result = {
            "code": code_text,
            "ticker": ticker,
            "period": period,
            "interval": interval,
            "values": [],
            "points": [],
            "error": f"차트 데이터를 불러오지 못했습니다: {exc}",
            "cached": False,
        }
        set_chart_cache(cache_key, result)
        return result


@app.get("/api/news")
def news(name: str, limit: int = 5) -> dict[str, Any]:
    limit = max(1, min(int(limit), 20))
    return {
        "name": name,
        "items": get_bridge().news_items(name, limit=limit),
    }


@app.get("/api/events")
def get_events() -> dict[str, Any]:
    events = load_json_file(EVENTS_FILE, [])
    return {
        "events": events if isinstance(events, list) else [],
        "count": len(events) if isinstance(events, list) else 0,
    }


@app.post("/api/events")
def save_events(payload: dict[str, Any]) -> dict[str, Any]:
    events = payload.get("events")

    if events is None:
        item = {
            "event_title": payload.get("event_title") or payload.get("title") or "이벤트",
            "event_type": payload.get("event_type") or "기타 사용자 입력 이벤트",
            "event_date": payload.get("event_date") or payload.get("date") or "",
            "importance": payload.get("importance") or "medium",
            "memo": payload.get("memo") or "",
            "related_stock_code": str(payload.get("related_stock_code") or payload.get("code") or "").upper(),
        }
        events = load_json_file(EVENTS_FILE, [])

        if not isinstance(events, list):
            events = []

        events.append(item)

    if not isinstance(events, list):
        raise HTTPException(status_code=400, detail="events must be a list")

    save_json_file(EVENTS_FILE, events)
    records_cache.clear()
    return {"events": events, "count": len(events)}


@app.get("/api/user-strategies")
def get_user_strategies() -> dict[str, Any]:
    strategies = load_json_file(USER_STRATEGIES_FILE, {})
    return {"user_strategies": strategies if isinstance(strategies, dict) else {}}


@app.post("/api/user-strategies")
def save_user_strategies(payload: dict[str, Any]) -> dict[str, Any]:
    strategies = payload.get("user_strategies")

    if strategies is None:
        code = str(payload.get("code") or payload.get("stock_code") or "").upper()

        if not code:
            raise HTTPException(status_code=400, detail="code is required")

        strategies = load_json_file(USER_STRATEGIES_FILE, {})

        if not isinstance(strategies, dict):
            strategies = {}

        strategies[code] = {
            "strategy": payload.get("strategy") or payload.get("name") or "",
            "memo": payload.get("memo") or "",
        }

    if not isinstance(strategies, dict):
        raise HTTPException(status_code=400, detail="user_strategies must be an object")

    normalized = {
        str(code).upper(): value
        for code, value in strategies.items()
        if isinstance(value, dict)
    }
    save_json_file(USER_STRATEGIES_FILE, normalized)
    records_cache.clear()
    return {"user_strategies": normalized}


@app.get("/search")
def search(keyword: str, limit: int = 20) -> dict[str, Any]:
    keyword = str(keyword or "").strip()

    if not keyword:
        raise HTTPException(status_code=400, detail="keyword is required")

    limit = max(1, min(int(limit), 50))

    try:
        from morning_stock_assistant.services.search_service import SearchService

        results = SearchService(get_bridge().service.krx).search(keyword)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    normalized = []
    seen = set()

    for item in results or []:
        code = str(
            item.get("code")
            or item.get("symbol")
            or item.get("ticker")
            or ""
        ).strip().upper()
        name = str(item.get("name") or item.get("company") or code).strip()

        if not code or code in seen:
            continue

        seen.add(code)
        normalized.append({
            "code": code,
            "name": name or code,
            "market": item.get("market") or ("국내" if code.isdigit() else "해외"),
        })

        if len(normalized) >= limit:
            break

    return {
        "keyword": keyword,
        "results": normalized,
        "count": len(normalized),
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
