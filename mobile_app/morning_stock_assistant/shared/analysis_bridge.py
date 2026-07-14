from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from morning_stock_assistant.ai.analyzer import StockAnalyzer
from morning_stock_assistant.services.stock_service import StockService


def safe_number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


FACTOR_MAX = {
    "value": 100,
    "quality": 130,
    "growth": 60,
    "stability": 20,
    "dividend": 10,
    "momentum": 50,
}

QUANT_WEIGHTS = {
    "value": 0.20,
    "quality": 0.25,
    "growth": 0.20,
    "stability": 0.15,
    "momentum": 0.15,
    "dividend": 0.05,
}

STOCK_TYPE_WEIGHTS = {
    "default": QUANT_WEIGHTS,
    "large_cap": {
        "value": 0.18,
        "quality": 0.27,
        "growth": 0.18,
        "stability": 0.20,
        "momentum": 0.12,
        "dividend": 0.05,
    },
    "growth": {
        "value": 0.10,
        "quality": 0.22,
        "growth": 0.28,
        "stability": 0.10,
        "momentum": 0.25,
        "dividend": 0.05,
    },
    "biotech": {
        "value": 0.08,
        "quality": 0.20,
        "growth": 0.27,
        "stability": 0.10,
        "momentum": 0.30,
        "dividend": 0.05,
    },
    "small_cap": {
        "value": 0.15,
        "quality": 0.20,
        "growth": 0.20,
        "stability": 0.20,
        "momentum": 0.20,
        "dividend": 0.05,
    },
    "etf": {
        "value": 0.08,
        "quality": 0.12,
        "growth": 0.20,
        "stability": 0.20,
        "momentum": 0.35,
        "dividend": 0.05,
    },
    "financial": {
        "value": 0.25,
        "quality": 0.25,
        "growth": 0.12,
        "stability": 0.23,
        "momentum": 0.10,
        "dividend": 0.05,
    },
}


@dataclass
class BridgeStockRecord:
    code: str
    name: str
    market: str
    asset_type: str
    price: float
    currency: str
    price_date: str
    freshness_label: str
    freshness_days: int
    change_1d: float
    change_1m: float
    change_3m: float
    quant_score: float
    news_score: float
    final_score: float
    grade: str
    rating: str
    machine_rating: str
    signal: str
    analyst: str
    target_price: float
    target_upside: float
    comment: str
    news: list[dict[str, Any]]
    finance: dict[str, Any]
    factor_scores: dict[str, float] = field(default_factory=dict)
    score_reason: str = ""
    score_adjustments: list[dict[str, Any]] = field(default_factory=list)
    stock_type: str = "default"
    stock_type_weights: dict[str, float] = field(default_factory=dict)
    data_confidence: str = "medium"
    data_confidence_reasons: list[str] = field(default_factory=list)
    risk_reasons: list[str] = field(default_factory=list)
    risk_adjustment_penalty_total: float = 0.0
    profit_rate: float = 0.0
    action_summary: str = ""
    score_change: dict[str, Any] = field(default_factory=dict)
    previous_final_score: float | None = None
    current_final_score: float | None = None
    final_score_diff: float | None = None
    previous_rating: str | None = None
    current_rating: str | None = None
    rating_changed: bool = False
    score_change_reason: str = ""
    events: list[dict[str, Any]] = field(default_factory=list)
    event_warning: str = ""
    user_strategy: dict[str, Any] = field(default_factory=dict)
    user_adjusted_action: str = ""
    user_strategy_reason: str = ""
    prediction_history: list[dict[str, Any]] = field(default_factory=list)
    analysis_history: list[dict[str, Any]] = field(default_factory=list)
    buy_reason: str = ""
    risk_factors: str = ""
    stop_loss_basis: str = ""
    add_buy_basis: str = ""
    hold_reason: str = ""
    next_check_date: str = ""
    daily_status: str = ""
    daily_core: str = ""
    daily_judgment: str = ""
    holding_quantity: float = 0.0
    holding_avg_price: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SharedAnalysisBridge:
    """GUI와 모바일 앱이 함께 쓰는 얇은 분석 입구."""

    def __init__(
        self,
        api_key: str = "",
        cache_dir: str | Path = "cache",
        year: str = "2025",
        report_code: str = "11011",
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.year = year
        self.report_code = report_code
        self.service = StockService(api_key, self.cache_dir)

    def build_records(
        self,
        stocks: list[dict[str, Any]],
        holdings: dict[str, dict[str, Any]] | None = None,
        previous_records: dict[str, dict[str, Any]] | None = None,
        events: list[dict[str, Any]] | None = None,
        user_strategies: dict[str, dict[str, Any]] | None = None,
        analysis_history: dict[str, list[dict[str, Any]]] | None = None,
        preset: str = "균형형",
        analyze: bool = True,
        progress_callback=None,
        max_workers: int = 4,
    ) -> list[dict[str, Any]]:
        holdings = holdings or {}
        previous_records = previous_records or {}
        events = events or []
        user_strategies = user_strategies or {}
        analysis_history = analysis_history or {}
        valid_stocks = [
            stock
            for stock in stocks
            if str(stock.get("code", "")).strip()
        ]

        def build_one(stock: dict[str, Any]) -> dict[str, Any] | None:
            code = str(stock.get("code", "")).strip().upper()

            if not code:
                return None

            name = stock.get("name") or code
            result = self._analyze(code, preset) if analyze else None
            metrics = self._metrics(code, result)
            holding = holdings.get(code, {})
            factor_scores = self.factor_scores(result)
            stock_type = self.stock_type(result, code, name)
            stock_type_weights = self.quant_weights_for_type(stock_type)
            score_adjustments = self.quant_adjustments(
                result,
                factor_scores,
                stock_type,
            )
            quant_score = self.quant_score_from_components(
                factor_scores,
                score_adjustments,
                stock_type_weights,
            )
            news_score = self.news_normalized_score(result)
            final_score = (
                round((quant_score * 0.7) + (news_score * 0.3), 1)
                if result
                else 0.0
            )
            price_date = (
                metrics.get("price_date")
                or getattr(result, "price_date", "")
                or ""
            )
            price = safe_number(metrics.get("price", 0))
            target_price = safe_number(getattr(result, "analyst_target_mean", 0))
            target_upside = self.target_upside(result)
            data_confidence = self.data_confidence(
                result,
                stock_type,
                price_date,
                factor_scores,
            )
            risk_reasons = [
                str(item.get("reason", ""))
                for item in score_adjustments
                if safe_number(item.get("points", 0)) < 0 and item.get("reason")
            ]
            risk_adjustment_penalty_total = sum(
                safe_number(item.get("points", 0))
                for item in score_adjustments
                if safe_number(item.get("points", 0)) < 0
            )
            profit_rate = self.profit_rate(price, holding)
            machine_rating = self.final_grade(result, final_score)
            action_summary = self.action_summary(
                final_score,
                profit_rate,
                holding,
                news_score,
                target_upside,
            )
            related_events = self.events_for_stock(events, code)
            event_warning = self.event_warning(related_events)
            user_strategy = user_strategies.get(code, {})
            user_adjusted_action, user_strategy_reason = self.user_adjusted_action(
                machine_rating,
                action_summary,
                user_strategy,
                profit_rate,
            )
            score_change = self.score_change(
                previous_records.get(code),
                {
                    "final_score": final_score,
                    "quant_score": quant_score,
                    "news_score": news_score,
                    "rating": machine_rating,
                    "factor_scores": factor_scores,
                    "data_confidence": data_confidence["level"],
                    "risk_adjustment_penalty_total": risk_adjustment_penalty_total,
                    "profit_rate": profit_rate,
                },
            )
            action_plan = self.action_plan(
                result=result,
                price=price,
                target_price=target_price,
                target_upside=target_upside,
                quant_score=quant_score,
                news_score=news_score,
                final_score=final_score,
                factor_scores=factor_scores,
                holding=holding,
            )
            news_items = self.news_items(
                getattr(result, "name", name) if result else name
            )
            daily_snapshot = self.daily_snapshot(
                result=result,
                metrics=metrics,
                news_items=news_items,
                final_score=final_score,
                news_score=news_score,
            )

            record = BridgeStockRecord(
                code=code,
                name=getattr(result, "name", name) if result else name,
                market="국내" if code.isdigit() else "해외",
                asset_type=getattr(result, "asset_type", "STOCK") if result else "STOCK",
                price=price,
                currency=metrics.get("currency", "KRW"),
                price_date=price_date,
                freshness_label=self.freshness_label(price_date),
                freshness_days=self.price_date_age_days(price_date),
                change_1d=safe_number(metrics.get("change_1d", 0)),
                change_1m=safe_number(metrics.get("change_1m", 0)),
                change_3m=safe_number(metrics.get("change_3m", 0)),
                quant_score=round(quant_score, 1),
                news_score=round(news_score, 1),
                final_score=final_score,
                grade=machine_rating,
                rating=machine_rating,
                machine_rating=machine_rating,
                signal=getattr(result, "signal", "-") if result else "분석 대기",
                analyst=self.analyst_summary(result),
                target_price=target_price,
                target_upside=target_upside,
                comment=self.comment(result, metrics),
                news=news_items,
                finance=self.finance_summary(result),
                factor_scores=factor_scores,
                score_reason=self.score_reason(
                    quant_score,
                    news_score,
                    final_score,
                    score_adjustments,
                    stock_type,
                    stock_type_weights,
                    data_confidence,
                ),
                score_adjustments=score_adjustments,
                stock_type=stock_type,
                stock_type_weights=stock_type_weights,
                data_confidence=data_confidence["level"],
                data_confidence_reasons=data_confidence["reasons"],
                risk_reasons=risk_reasons,
                risk_adjustment_penalty_total=round(risk_adjustment_penalty_total, 1),
                profit_rate=profit_rate,
                action_summary=action_summary,
                score_change=score_change,
                previous_final_score=score_change["previous_final_score"],
                current_final_score=score_change["current_final_score"],
                final_score_diff=score_change["final_score_diff"],
                previous_rating=score_change["previous_rating"],
                current_rating=score_change["current_rating"],
                rating_changed=score_change["rating_changed"],
                score_change_reason=score_change["score_change_reason"],
                events=related_events,
                event_warning=event_warning,
                user_strategy=user_strategy,
                user_adjusted_action=user_adjusted_action,
                user_strategy_reason=user_strategy_reason,
                prediction_history=analysis_history.get(code, [])[-5:],
                analysis_history=analysis_history.get(code, [])[-5:],
                buy_reason=action_plan["buy_reason"],
                risk_factors=action_plan["risk_factors"],
                stop_loss_basis=action_plan["stop_loss_basis"],
                add_buy_basis=action_plan["add_buy_basis"],
                hold_reason=action_plan["hold_reason"],
                next_check_date=action_plan["next_check_date"],
                daily_status=daily_snapshot["daily_status"],
                daily_core=daily_snapshot["daily_core"],
                daily_judgment=daily_snapshot["daily_judgment"],
                holding_quantity=safe_number(holding.get("quantity", 0)),
                holding_avg_price=safe_number(
                    holding.get("average_price", holding.get("avg_price", 0))
                ),
            )
            return record.to_dict()

        records = []
        worker_count = max(1, min(max_workers, len(valid_stocks) or 1))

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = {
                executor.submit(build_one, stock): stock
                for stock in valid_stocks
            }

            for index, future in enumerate(as_completed(futures), start=1):
                stock = futures[future]
                code = str(stock.get("code", "")).strip().upper()
                name = stock.get("name") or code

                if progress_callback:
                    progress_callback(index, len(valid_stocks), name, code)

                try:
                    record = future.result()
                except Exception:
                    record = None

                if record:
                    records.append(record)

        records.sort(key=lambda item: item["final_score"], reverse=True)
        return records

    def chart_values(
        self,
        stock_code: str,
        period: str = "1mo",
        interval: str | None = None,
    ) -> list[float]:
        try:
            hist = self.service.price.get_history(
                stock_code,
                period=period,
                interval=interval,
            )

            if hist is None or hist.empty or "Close" not in hist:
                return []

            return [
                safe_number(value)
                for value in hist["Close"].dropna().tolist()
                if safe_number(value) > 0
            ]
        except Exception:
            return []

    def news_items(self, stock_name: str, limit: int = 5) -> list[dict[str, Any]]:
        try:
            items = self.service.news.get_news(stock_name, limit=limit)
        except Exception:
            return []

        normalized = []

        for item in items or []:
            title = str(item.get("title") or "").strip()

            if not title:
                continue

            normalized.append({
                "title": title,
                "date": item.get("date") or "",
                "link": item.get("link") or "",
                "impact_label": item.get("impact_label") or "중립",
                "impact_score": safe_number(item.get("impact_score", 0)),
                "source": item.get("source") or "",
            })

        return normalized

    @staticmethod
    def finance_summary(result) -> dict[str, Any]:
        if result is None:
            return {}

        fields = [
            "sales",
            "operating_profit",
            "net_income",
            "assets",
            "liabilities",
            "equity",
            "roe",
            "roa",
            "debt_ratio",
            "operating_margin",
            "net_margin",
            "per",
            "pbr",
            "psr",
            "pcr",
            "roic",
            "fcf_yield",
            "free_cash_flow",
            "operating_cash_flow",
            "market_cap",
            "dividend_yield",
            "current_ratio",
            "short_ratio",
            "ma20",
            "ma60",
            "ma120",
            "high52",
            "low52",
            "volume_ratio",
            "foreign_net_buy",
            "institution_net_buy",
        ]

        return {
            field: safe_number(getattr(result, field, 0))
            for field in fields
        }

    @staticmethod
    def stock_type(result, code: str = "", name: str = "") -> str:
        if result is None:
            return "default"

        code = str(code or getattr(result, "code", "") or "").upper()
        name = str(name or getattr(result, "name", "") or "").lower()
        asset_type = str(getattr(result, "asset_type", "STOCK") or "STOCK").upper()
        market_cap = safe_number(getattr(result, "market_cap", 0))
        price = safe_number(getattr(result, "price", 0))
        growth = safe_number(getattr(result, "growth", 0))
        momentum = safe_number(getattr(result, "momentum", 0))

        if asset_type == "ETF" or str(getattr(result, "is_etf", "")).lower() == "true":
            return "etf"

        if any(keyword in name for keyword in [
            "bio",
            "pharma",
            "therapeutics",
            "바이오",
            "제약",
        ]):
            return "biotech"

        if any(keyword in name for keyword in [
            "증권",
            "은행",
            "금융",
            "financial",
            "bank",
            "capital",
            "securities",
        ]):
            return "financial"

        if market_cap >= 10_000_000_000_000 or code in {
            "AAPL",
            "MSFT",
            "NVDA",
            "GOOGL",
            "GOOG",
            "AMZN",
            "META",
            "AVGO",
            "TSM",
            "005930",
            "000660",
        }:
            return "large_cap"

        if growth >= 40 or momentum >= 35:
            return "growth"

        if 0 < price < 10 or (0 < market_cap < 500_000_000_000):
            return "small_cap"

        return "default"

    @staticmethod
    def quant_weights_for_type(stock_type: str) -> dict[str, float]:
        return dict(STOCK_TYPE_WEIGHTS.get(stock_type, QUANT_WEIGHTS))

    @staticmethod
    def data_confidence(
        result,
        stock_type: str,
        price_date: str,
        factor_scores: dict[str, float],
    ) -> dict[str, Any]:
        if result is None:
            return {"level": "low", "reasons": ["분석 결과 없음"]}

        reasons = []
        code = str(getattr(result, "code", "") or "").upper()
        asset_type = str(getattr(result, "asset_type", "STOCK") or "STOCK").upper()
        per = safe_number(getattr(result, "per", 0))
        pbr = safe_number(getattr(result, "pbr", 0))
        roe = safe_number(getattr(result, "roe", 0))
        market_cap = safe_number(getattr(result, "market_cap", 0))
        net_income = safe_number(getattr(result, "net_income", 0))
        missing_fundamentals = (
            per <= 0
            and pbr <= 0
            and roe == 0
            and market_cap <= 0
            and net_income == 0
        )
        age_days = SharedAnalysisBridge.price_date_age_days(price_date)

        if age_days >= 7:
            reasons.append(f"가격 기준일 {age_days}일 경과")
        elif not price_date:
            reasons.append("가격 기준일 없음")

        if missing_fundamentals:
            reasons.append("재무 데이터 누락")

        if code and not code.isdigit():
            reasons.append("해외주식 데이터 해석 주의")

        if asset_type == "ETF" or stock_type == "etf":
            reasons.append("ETF는 개별기업 재무점수 해석 주의")

        if stock_type == "biotech":
            reasons.append("바이오/임상주는 뉴스·임상 이벤트 민감")

        if not any(safe_number(value) > 0 for value in factor_scores.values()):
            reasons.append("팩터 점수 대부분 누락")

        severe_count = sum(
            1
            for reason in reasons
            if "누락" in reason or "없음" in reason or "경과" in reason
        )
        level = "low" if severe_count >= 2 else "medium" if reasons else "high"
        return {"level": level, "reasons": reasons or ["주요 가격/재무 데이터 확인됨"]}

    @staticmethod
    def profit_rate(price: float, holding: dict[str, Any] | None = None) -> float:
        holding = holding or {}
        quantity = safe_number(holding.get("quantity", 0))
        avg_price = safe_number(
            holding.get("average_price", holding.get("avg_price", 0))
        )

        if quantity <= 0 or avg_price <= 0 or price <= 0:
            return 0.0

        return round(((price - avg_price) / avg_price) * 100, 2)

    @staticmethod
    def action_summary(
        final_score: float,
        profit_rate: float,
        holding: dict[str, Any] | None,
        news_score: float,
        target_upside: float,
    ) -> str:
        holding = holding or {}
        quantity = safe_number(holding.get("quantity", 0))

        if quantity > 0:
            if news_score <= 35:
                return "뉴스 리스크 확인 전 추가매수 보류"
            if profit_rate <= -20:
                return "손실 확대 구간, 추가매수보다 리스크 재점검"
            if profit_rate <= -10:
                return "보유 관찰, 평단 회복 전 추가매수 신중"
            if profit_rate >= 0 and final_score < 65:
                return "평단 회복 시 일부 비중 축소 검토"
            if final_score >= 72 and target_upside > 15:
                return "보유 유지, 조정 시 분할 추가 관심"
            return "보유 유지"

        if final_score >= 85:
            return "강한 관심, 신규 매수는 분할 접근"
        if final_score >= 72:
            return "조정 시 관심"
        if final_score >= 65:
            return "관심 유지, 추가 확인 필요"
        if final_score >= 55:
            return "관망"
        return "신규 매수 보류"

    @staticmethod
    def score_change(
        previous: dict[str, Any] | None,
        current: dict[str, Any],
    ) -> dict[str, Any]:
        current_final = round(safe_number(current.get("final_score", 0)), 1)
        current_quant = round(safe_number(current.get("quant_score", 0)), 1)
        current_news = round(safe_number(current.get("news_score", 0)), 1)
        current_rating = str(current.get("rating") or "")

        if not previous:
            return {
                "previous_final_score": None,
                "current_final_score": current_final,
                "final_score_diff": None,
                "previous_quant_score": None,
                "current_quant_score": current_quant,
                "quant_score_diff": None,
                "previous_news_score": None,
                "current_news_score": current_news,
                "news_score_diff": None,
                "previous_rating": None,
                "current_rating": current_rating,
                "rating_changed": False,
                "score_change_reason": "이전 분석 결과가 없어 이번 결과를 기준점으로 저장했습니다.",
            }

        previous_final = round(safe_number(previous.get("final_score", 0)), 1)
        previous_quant = round(safe_number(previous.get("quant_score", 0)), 1)
        previous_news = round(safe_number(previous.get("news_score", 0)), 1)
        previous_rating = str(previous.get("rating") or previous.get("grade") or "")
        previous_factors = previous.get("factor_scores") or {}
        current_factors = current.get("factor_scores") or {}
        momentum_diff = round(
            safe_number(current_factors.get("momentum", 0))
            - safe_number(previous_factors.get("momentum", 0)),
            1,
        )
        confidence_changed = (
            previous.get("data_confidence")
            and previous.get("data_confidence") != current.get("data_confidence")
        )
        risk_diff = round(
            safe_number(current.get("risk_adjustment_penalty_total", 0))
            - safe_number(previous.get("risk_adjustment_penalty_total", 0)),
            1,
        )
        profit_diff = round(
            safe_number(current.get("profit_rate", 0))
            - safe_number(previous.get("profit_rate", 0)),
            1,
        )
        final_diff = round(current_final - previous_final, 1)
        quant_diff = round(current_quant - previous_quant, 1)
        news_diff = round(current_news - previous_news, 1)
        reasons = []

        if abs(news_diff) >= 3:
            reasons.append(f"뉴스 점수 {news_diff:+.1f}점")
        if abs(quant_diff) >= 3:
            reasons.append(f"퀀트 점수 {quant_diff:+.1f}점")
        if abs(momentum_diff) >= 3:
            reasons.append(f"모멘텀 {momentum_diff:+.1f}점")
        if confidence_changed:
            reasons.append(
                f"데이터 신뢰도 {previous.get('data_confidence')}→{current.get('data_confidence')}"
            )
        if abs(risk_diff) >= 2:
            reasons.append(f"위험 보정 {risk_diff:+.1f}점")
        if abs(profit_diff) >= 3:
            reasons.append(f"평단 대비 손익 {profit_diff:+.1f}%")

        rating_changed = bool(previous_rating and previous_rating != current_rating)
        if rating_changed:
            reasons.append(f"{previous_rating}에서 {current_rating}로 변경")

        if not reasons:
            reasons.append("주요 점수 변화는 제한적입니다.")

        return {
            "previous_final_score": previous_final,
            "current_final_score": current_final,
            "final_score_diff": final_diff,
            "previous_quant_score": previous_quant,
            "current_quant_score": current_quant,
            "quant_score_diff": quant_diff,
            "previous_news_score": previous_news,
            "current_news_score": current_news,
            "news_score_diff": news_diff,
            "previous_rating": previous_rating or None,
            "current_rating": current_rating,
            "rating_changed": rating_changed,
            "score_change_reason": ", ".join(reasons),
        }

    @staticmethod
    def events_for_stock(
        events: list[dict[str, Any]],
        code: str,
    ) -> list[dict[str, Any]]:
        code = str(code or "").upper()
        normalized = []

        for item in events or []:
            related_code = str(item.get("related_stock_code") or item.get("code") or "").upper()

            if related_code != code:
                continue

            normalized.append({
                "event_title": item.get("event_title") or item.get("title") or "이벤트",
                "event_type": item.get("event_type") or "기타 사용자 입력 이벤트",
                "event_date": item.get("event_date") or item.get("date") or "",
                "importance": item.get("importance") or "medium",
                "memo": item.get("memo") or "",
                "related_stock_code": code,
            })

        return sorted(normalized, key=lambda item: item.get("event_date") or "9999-99-99")

    @staticmethod
    def event_warning(events: list[dict[str, Any]]) -> str:
        today = datetime.now().date()
        upcoming = []

        for item in events or []:
            try:
                event_date = datetime.fromisoformat(
                    str(item.get("event_date", ""))[:10]
                ).date()
            except ValueError:
                continue

            days = (event_date - today).days

            if 0 <= days <= 7:
                upcoming.append((days, item))

        if not upcoming:
            return ""

        upcoming.sort(key=lambda value: value[0])
        days, item = upcoming[0]
        event_type = str(item.get("event_type") or "")

        if "FDA" in event_type.upper() or "임상" in event_type:
            return "FDA/임상 관련 일정이 임박했으므로 변동성 확대 가능성이 있습니다."

        importance = str(item.get("importance") or "medium").lower()
        if importance == "high":
            return f"{days}일 이내 중요 이벤트가 있습니다."

        return f"{days}일 이내 이벤트가 있습니다."

    @staticmethod
    def user_adjusted_action(
        machine_rating: str,
        action_summary: str,
        user_strategy: dict[str, Any] | None,
        profit_rate: float,
    ) -> tuple[str, str]:
        user_strategy = user_strategy or {}
        strategy = str(
            user_strategy.get("strategy")
            or user_strategy.get("name")
            or user_strategy.get("type")
            or ""
        ).strip()

        if not strategy:
            return action_summary, "사용자 전략이 없어 기계적 판단을 그대로 사용했습니다."

        if "장기" in strategy:
            return "보유 유지", "사용자가 장기 보유 전략을 설정했습니다."
        if "손절하지" in strategy:
            return "보유 유지", "사용자가 손절하지 않음 전략을 설정했습니다."
        if "목표가" in strategy:
            return "목표가 도달 시 일부 매도", "사용자가 목표가 도달 시 일부 매도 전략을 설정했습니다."
        if "평단" in strategy:
            if profit_rate >= 0:
                return "평단 회복, 일부 비중 축소 검토", "사용자가 평단 회복 시 일부 비중 축소 전략을 설정했습니다."
            return "평단 회복 전 보유 관찰", "사용자가 평단 회복 시 일부 비중 축소 전략을 설정했습니다."
        if "정기" in strategy or "매달" in strategy:
            return "정기 매수 유지, 과열 구간은 금액 축소", "사용자가 정기 매수 전략을 설정했습니다."
        if "이벤트" in strategy:
            return "이벤트 전 일부 매도 검토", "사용자가 이벤트 전 일부 매도 전략을 설정했습니다."

        return action_summary, f"사용자 전략 '{strategy}'을 참고하되 기계적 등급 {machine_rating}을 함께 확인합니다."

    def _analyze(self, code: str, preset: str):
        try:
            analyzer = StockAnalyzer(self.service)
            return analyzer.analyze(
                code,
                self.year,
                self.report_code,
                preset,
            )
        except Exception:
            return None

    def _metrics(self, code: str, result):
        try:
            return self.service.get_briefing_metrics(code)
        except Exception:
            return {
                "price": safe_number(getattr(result, "price", 0)),
                "change_1d": safe_number(getattr(result, "change_rate", 0)),
                "change_1m": 0,
                "change_3m": 0,
                "currency": getattr(result, "currency", "KRW"),
                "price_date": getattr(result, "price_date", ""),
            }

    @staticmethod
    def quant_average_score(result) -> float:
        if result is None:
            return 0.0

        factor_scores = SharedAnalysisBridge.factor_scores(result)
        stock_type = SharedAnalysisBridge.stock_type(
            result,
            str(getattr(result, "code", "") or ""),
            str(getattr(result, "name", "") or ""),
        )
        score_adjustments = SharedAnalysisBridge.quant_adjustments(
            result,
            factor_scores,
            stock_type,
        )
        return SharedAnalysisBridge.quant_score_from_components(
            factor_scores,
            score_adjustments,
            SharedAnalysisBridge.quant_weights_for_type(stock_type),
        )

    @staticmethod
    def factor_scores(result) -> dict[str, float]:
        if result is None:
            return {name: 0.0 for name in FACTOR_MAX}

        scores: dict[str, float] = {}

        for item in getattr(result, "score_breakdown", []) or []:
            name = str(item.get("name", "")).strip().lower()

            if name in FACTOR_MAX:
                scores[name] = round(
                    max(min(safe_number(item.get("raw_score", 0)), 100), 0),
                    1,
                )

        for name, max_score in FACTOR_MAX.items():
            if name in scores:
                continue

            score = safe_number(getattr(result, name, 0))
            score = max(min(score, max_score), 0)
            scores[name] = round((score / max_score) * 100, 1)

        return scores

    @staticmethod
    def quant_score_from_components(
        factor_scores: dict[str, float],
        adjustments: list[dict[str, Any]] | None = None,
        weights: dict[str, float] | None = None,
    ) -> float:
        weights = weights or QUANT_WEIGHTS
        weighted_score = sum(
            max(min(safe_number(factor_scores.get(name, 0)), 100), 0) * weight
            for name, weight in weights.items()
        )
        adjustment_total = sum(
            safe_number(item.get("points", 0))
            for item in adjustments or []
        )
        adjustment_total = max(min(adjustment_total, 8), -20)
        return round(max(min(weighted_score + adjustment_total, 100), 0), 1)

    @staticmethod
    def quant_adjustments(
        result,
        factor_scores: dict[str, float],
        stock_type: str = "default",
    ) -> list[dict[str, Any]]:
        if result is None:
            return []

        penalty_adjustments: list[dict[str, Any]] = []
        bonus_adjustments: list[dict[str, Any]] = []
        code = str(getattr(result, "code", "") or "").upper()
        name = str(getattr(result, "name", "") or "").lower()
        asset_type = str(getattr(result, "asset_type", "STOCK") or "STOCK").upper()
        net_income = safe_number(getattr(result, "net_income", 0))
        price = safe_number(getattr(result, "price", 0))

        if stock_type == "etf":
            penalty_adjustments.append({
                "type": "asset_type",
                "points": -3,
                "reason": "ETF는 개별기업 재무팩터 해석 주의",
            })

        if net_income < 0 and asset_type != "ETF":
            penalty_adjustments.append({
                "type": "loss",
                "points": -8,
                "reason": "순이익 적자 기업은 품질/안정성 위험을 추가 반영",
            })

        if stock_type == "biotech":
            penalty_adjustments.append({
                "type": "biotech",
                "points": -4,
                "reason": "바이오/제약주는 임상·뉴스 변동성이 커 보수 조정",
            })

        if (
            factor_scores.get("growth", 0) >= 70
            and factor_scores.get("momentum", 0) >= 60
            and factor_scores.get("value", 0) < 40
            and asset_type != "ETF"
        ):
            bonus_adjustments.append({
                "type": "growth_stock",
                "points": 4,
                "reason": "가치점수는 낮지만 성장·모멘텀이 강한 성장주 보정",
            })

        if price > 0 and price < 10 and asset_type != "ETF":
            penalty_adjustments.append({
                "type": "speculative_price",
                "points": -3,
                "reason": "저가 변동성 종목은 투기성 위험을 일부 반영",
            })

        penalty_total = sum(
            safe_number(item.get("points", 0))
            for item in penalty_adjustments
        )

        if penalty_total < -15:
            scale = 15 / abs(penalty_total)
            for item in penalty_adjustments:
                item["original_points"] = item["points"]
                item["points"] = round(safe_number(item["points"]) * scale, 1)
                item["capped"] = True

        return penalty_adjustments + bonus_adjustments

    @staticmethod
    def score_reason(
        quant_score: float,
        news_score: float,
        final_score: float,
        adjustments: list[dict[str, Any]] | None = None,
        stock_type: str = "default",
        stock_type_weights: dict[str, float] | None = None,
        data_confidence: dict[str, Any] | None = None,
    ) -> str:
        reason = (
            f"퀀트 {quant_score:.1f}점, 뉴스 {news_score:.1f}점, "
            f"최종 {final_score:.1f}점 = 퀀트 70% + 뉴스 30%"
        )
        weights = stock_type_weights or QUANT_WEIGHTS
        reason += (
            f" | 유형 {stock_type}"
            f" | 가중치 가치 {weights.get('value', 0) * 100:.0f}%"
            f"/품질 {weights.get('quality', 0) * 100:.0f}%"
            f"/성장 {weights.get('growth', 0) * 100:.0f}%"
            f"/안정 {weights.get('stability', 0) * 100:.0f}%"
            f"/모멘텀 {weights.get('momentum', 0) * 100:.0f}%"
            f"/배당 {weights.get('dividend', 0) * 100:.0f}%"
        )
        if data_confidence:
            confidence_reasons = ", ".join(data_confidence.get("reasons", [])[:3])
            reason += (
                f" | 데이터 신뢰도 {data_confidence.get('level', 'medium')}"
                f"({confidence_reasons})"
            )

        labels = [
            f"{item.get('reason', '')}({safe_number(item.get('points', 0)):+.1f})"
            for item in adjustments or []
            if item.get("reason")
        ]

        if labels:
            reason += " | 보정: " + "; ".join(labels)

        return reason

    @staticmethod
    def action_plan(
        result,
        price: float,
        target_price: float,
        target_upside: float,
        quant_score: float,
        news_score: float,
        final_score: float,
        factor_scores: dict[str, float],
        holding: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        holding = holding or {}
        momentum = safe_number(factor_scores.get("momentum", 0))
        growth = safe_number(factor_scores.get("growth", 0))
        quality = safe_number(factor_scores.get("quality", 0))
        stability = safe_number(factor_scores.get("stability", 0))
        value = safe_number(factor_scores.get("value", 0))
        quantity = safe_number(holding.get("quantity", 0))
        avg_price = safe_number(
            holding.get("average_price", holding.get("avg_price", 0))
        )
        change_1d = safe_number(getattr(result, "change_rate", 0)) if result else 0

        if final_score >= 72:
            buy_reason = "최종 점수가 높고 퀀트/뉴스 흐름이 우호적입니다."
        elif quant_score >= 70 and news_score < 55:
            buy_reason = "퀀트 조건은 양호하지만 뉴스 확인 후 접근이 필요합니다."
        elif news_score >= 70 and quant_score < 55:
            buy_reason = "뉴스 흐름은 좋지만 가격/재무 신호 확인이 필요합니다."
        else:
            buy_reason = "매수보다는 관찰 우선 구간입니다."

        risks = []
        if news_score < 45:
            risks.append("뉴스 점수 약세")
        if stability < 45:
            risks.append("안정성 점수 낮음")
        if momentum < 45:
            risks.append("모멘텀 약세")
        if value < 35 and growth < 60:
            risks.append("밸류에이션 부담")
        if target_price <= 0:
            risks.append("목표가 데이터 부족")
        if abs(change_1d) >= 7:
            risks.append("단기 변동성 확대")
        risk_factors = ", ".join(risks) if risks else "뚜렷한 위험 신호는 제한적입니다."

        stop_base = avg_price if avg_price > 0 else price
        stop_price = stop_base * 0.9 if stop_base > 0 else 0
        if stop_price > 0:
            stop_loss_basis = f"기준가 대비 -10% 부근({stop_price:,.0f}) 이탈 시 재점검"
        else:
            stop_loss_basis = "현재가 확인 후 -10% 기준으로 설정"

        if final_score >= 72 and momentum >= 55:
            add_buy_basis = "20일선 또는 단기 지지 확인 후 분할 추가 매수"
        elif final_score >= 55:
            add_buy_basis = "뉴스와 모멘텀이 개선될 때만 소액 분할"
        else:
            add_buy_basis = "추가 매수보다 리스크 확인 우선"

        if quantity > 0:
            if final_score >= 60:
                hold_reason = "보유 중이면 점수와 목표가를 보며 유지 검토"
            else:
                hold_reason = "보유 중이면 비중 축소 또는 손절 기준 점검"
        else:
            hold_reason = "미보유 종목은 관심종목으로 관찰"

        check_days = 3 if risks or final_score < 55 else 7
        next_check_date = (datetime.now().date() + timedelta(days=check_days)).isoformat()

        return {
            "buy_reason": buy_reason,
            "risk_factors": risk_factors,
            "stop_loss_basis": stop_loss_basis,
            "add_buy_basis": add_buy_basis,
            "hold_reason": hold_reason,
            "next_check_date": next_check_date,
        }

    @staticmethod
    def news_normalized_score(result) -> float:
        if result is None:
            return 0.0

        raw_news = safe_number(getattr(result, "news", 0))
        raw_news = max(min(raw_news, 20), -20)
        return ((raw_news + 20) / 40) * 100

    @staticmethod
    def daily_snapshot(
        result,
        metrics: dict[str, Any],
        news_items: list[dict[str, Any]],
        final_score: float,
        news_score: float,
    ) -> dict[str, str]:
        if final_score >= 85:
            status = "강한 관심"
            judgment = "보유 유지 / 신규 매수는 분할 접근"
        elif final_score >= 72:
            status = "관심"
            judgment = "보유 유지 / 조정 시 분할 추가매수"
        elif final_score >= 65:
            status = "관심 관찰"
            judgment = "관심 유지 / 추가 확인 후 분할 접근"
        elif final_score >= 55:
            status = "관망"
            judgment = "보유 유지 / 추가매수는 조정 시"
        elif final_score >= 40:
            status = "주의"
            judgment = "보유 비중 점검 / 신규 매수 보류"
        else:
            status = "위험"
            judgment = "비중 축소 또는 관망"

        positive = next(
            (
                item
                for item in news_items
                if "호재" in str(item.get("impact_label", ""))
                or safe_number(item.get("impact_score", 0)) >= 4
            ),
            None,
        )
        negative = next(
            (
                item
                for item in news_items
                if "악재" in str(item.get("impact_label", ""))
                or safe_number(item.get("impact_score", 0)) <= -4
            ),
            None,
        )

        if positive and negative:
            core = (
                f"{SharedAnalysisBridge.short_news_title(positive)}는 호재, "
                f"{SharedAnalysisBridge.short_news_title(negative)}는 부담"
            )
        elif positive:
            core = f"{SharedAnalysisBridge.short_news_title(positive)}가 호재"
        elif negative:
            core = f"{SharedAnalysisBridge.short_news_title(negative)}가 부담"
        else:
            change_1d = safe_number(metrics.get("change_1d", 0))
            change_1m = safe_number(metrics.get("change_1m", 0))

            if news_score >= 65:
                core = "뉴스 흐름은 우호적이나 가격 확인 필요"
            elif news_score <= 35:
                core = "뉴스 흐름이 부담으로 작용"
            elif change_1d <= -5:
                core = "단기 하락이 커서 지지 확인 필요"
            elif change_1m >= 8:
                core = "1개월 추세 회복이 핵심"
            else:
                core = "뚜렷한 단기 재료는 제한적이고 가격 흐름 확인 필요"

        return {
            "daily_status": status,
            "daily_core": core,
            "daily_judgment": judgment,
        }

    @staticmethod
    def short_news_title(news: dict[str, Any], limit: int = 28) -> str:
        title = " ".join(str(news.get("title", "")).split())

        if not title:
            return "해당 뉴스"

        if len(title) > limit:
            return title[:limit].rstrip() + "..."

        return title

    @staticmethod
    def final_grade(result, final_score: float) -> str:
        if result is None:
            return "분석 대기"

        speculative = (
            safe_number(getattr(result, "net_income", 0)) <= 0
            or safe_number(getattr(result, "price", 0)) < 10
            or getattr(result, "asset_type", "STOCK") == "ETF"
        )

        if final_score >= 85:
            return "STRONG BUY"
        if final_score >= 72:
            return "BUY"
        if final_score >= 65:
            return "WATCH BUY"
        if final_score >= 55:
            return "HOLD"
        if final_score >= 40:
            return "REDUCE"

        return "SELL"

    @staticmethod
    def analyst_summary(result) -> str:
        if result is None:
            return "-"

        target = safe_number(getattr(result, "analyst_target_mean", 0))
        count = safe_number(getattr(result, "analyst_count", 0))
        recommendation = SharedAnalysisBridge.format_recommendation(
            getattr(result, "analyst_recommendation", "")
        )
        parts = []

        if recommendation:
            parts.append(recommendation)

        if target > 0:
            price = safe_number(getattr(result, "price", 0))
            upside = ((target - price) / price * 100) if price > 0 else 0
            currency = getattr(result, "currency", "KRW")
            parts.append(
                f"목표 {SharedAnalysisBridge.format_price(target, currency)}"
                f"({upside:+.1f}%)"
            )

        if count > 0:
            parts.append(f"{count:.0f}명")

        return ", ".join(parts) if parts else "-"

    @staticmethod
    def target_upside(result) -> float:
        if result is None:
            return 0.0

        target = safe_number(getattr(result, "analyst_target_mean", 0))
        price = safe_number(getattr(result, "price", 0))

        if target <= 0 or price <= 0:
            return 0.0

        return round(((target - price) / price) * 100, 2)

    @staticmethod
    def comment(result, metrics: dict[str, Any]) -> str:
        if result is None:
            return "분석 대기: 실제 분석 실행 후 점수와 해석이 채워집니다."

        one_month = safe_number(metrics.get("change_1m", 0))
        three_month = safe_number(metrics.get("change_3m", 0))
        short_ratio = safe_number(getattr(result, "short_ratio", 0))
        foreign = safe_number(getattr(result, "foreign_net_buy", 0))
        institution = safe_number(getattr(result, "institution_net_buy", 0))
        news_score = SharedAnalysisBridge.news_normalized_score(result)
        parts = []

        if getattr(result, "asset_type", "STOCK") == "ETF":
            parts.append("ETF는 추세와 구성자산 중심 확인")

        if three_month >= 10:
            parts.append("3개월 추세 강세")
        elif three_month <= -10:
            parts.append("3개월 추세 약세")
        elif one_month >= 5:
            parts.append("단기 회복")
        else:
            parts.append("추세 중립")

        if short_ratio >= 5:
            parts.append("공매도 부담 주의")

        if foreign > 0 and institution > 0:
            parts.append("외국인·기관 동반 순매수")
        elif foreign < 0 and institution < 0:
            parts.append("외국인·기관 동반 순매도")
        elif foreign > 0:
            parts.append("외국인 순매수")
        elif institution > 0:
            parts.append("기관 순매수")

        if news_score >= 65:
            parts.append("뉴스 흐름 우호적")
        elif news_score <= 35:
            parts.append("뉴스 리스크 확인 필요")

        return " | ".join(parts)

    @staticmethod
    def format_recommendation(value: str) -> str:
        mapping = {
            "strong_buy": "적극 매수",
            "buy": "매수",
            "hold": "보유",
            "underperform": "비중 축소",
            "sell": "매도",
        }
        text = str(value or "").strip()
        return mapping.get(text.lower(), text)

    @staticmethod
    def format_price(value: float, currency: str = "KRW") -> str:
        value = safe_number(value)

        if currency == "KRW":
            return f"{value:,.0f}원"

        return f"${value:,.2f}"

    @staticmethod
    def freshness_label(price_date: str) -> str:
        age = SharedAnalysisBridge.price_date_age_days(price_date)

        if age < 0:
            return "확인불가"
        if age <= 3:
            return "정상"
        if age <= 10:
            return "주의"

        return "오래됨"

    @staticmethod
    def price_date_age_days(price_date: str) -> int:
        if not price_date:
            return -1

        try:
            parsed = datetime.strptime(price_date[:10], "%Y-%m-%d")
            return max((datetime.now() - parsed).days, 0)
        except Exception:
            return -1
