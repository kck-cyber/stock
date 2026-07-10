from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict, field
from datetime import datetime
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
        preset: str = "균형형",
        analyze: bool = True,
        progress_callback=None,
        max_workers: int = 4,
    ) -> list[dict[str, Any]]:
        holdings = holdings or {}
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
            score_adjustments = self.quant_adjustments(result, factor_scores)
            quant_score = self.quant_score_from_components(
                factor_scores,
                score_adjustments,
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

            record = BridgeStockRecord(
                code=code,
                name=getattr(result, "name", name) if result else name,
                market="국내" if code.isdigit() else "해외",
                asset_type=getattr(result, "asset_type", "STOCK") if result else "STOCK",
                price=safe_number(metrics.get("price", 0)),
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
                grade=self.final_grade(result, final_score),
                signal=getattr(result, "signal", "-") if result else "분석 대기",
                analyst=self.analyst_summary(result),
                target_price=safe_number(
                    getattr(result, "analyst_target_mean", 0)
                ),
                target_upside=self.target_upside(result),
                comment=self.comment(result, metrics),
                news=self.news_items(
                    getattr(result, "name", name) if result else name
                ),
                finance=self.finance_summary(result),
                factor_scores=factor_scores,
                score_reason=self.score_reason(
                    quant_score,
                    news_score,
                    final_score,
                    score_adjustments,
                ),
                score_adjustments=score_adjustments,
                holding_quantity=safe_number(holding.get("quantity", 0)),
                holding_avg_price=safe_number(holding.get("avg_price", 0)),
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

                record = future.result()

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
        score_adjustments = SharedAnalysisBridge.quant_adjustments(
            result,
            factor_scores,
        )
        return SharedAnalysisBridge.quant_score_from_components(
            factor_scores,
            score_adjustments,
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
    ) -> float:
        weighted_score = sum(
            max(min(safe_number(factor_scores.get(name, 0)), 100), 0) * weight
            for name, weight in QUANT_WEIGHTS.items()
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
    ) -> list[dict[str, Any]]:
        if result is None:
            return []

        adjustments: list[dict[str, Any]] = []
        code = str(getattr(result, "code", "") or "").upper()
        name = str(getattr(result, "name", "") or "").lower()
        asset_type = str(getattr(result, "asset_type", "STOCK") or "STOCK").upper()
        net_income = safe_number(getattr(result, "net_income", 0))
        price = safe_number(getattr(result, "price", 0))
        per = safe_number(getattr(result, "per", 0))
        pbr = safe_number(getattr(result, "pbr", 0))
        roe = safe_number(getattr(result, "roe", 0))
        market_cap = safe_number(getattr(result, "market_cap", 0))

        if asset_type == "ETF" or str(getattr(result, "is_etf", "")).lower() == "true":
            adjustments.append({
                "type": "asset_type",
                "points": -6,
                "reason": "ETF는 개별기업 재무팩터보다 구성자산과 추세가 중요해 보수 조정",
            })

        if net_income < 0 and asset_type != "ETF":
            adjustments.append({
                "type": "loss",
                "points": -8,
                "reason": "순이익 적자 기업은 품질/안정성 위험을 추가 반영",
            })

        if any(keyword in name for keyword in [
            "bio",
            "pharma",
            "therapeutics",
            "바이오",
            "제약",
        ]):
            adjustments.append({
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
            adjustments.append({
                "type": "growth_stock",
                "points": 4,
                "reason": "가치점수는 낮지만 성장·모멘텀이 강한 성장주 보정",
            })

        missing_fundamentals = (
            per <= 0
            and pbr <= 0
            and roe == 0
            and market_cap <= 0
        )

        if code and not code.isdigit() and missing_fundamentals and asset_type != "ETF":
            adjustments.append({
                "type": "overseas_data",
                "points": -4,
                "reason": "해외주식 재무 데이터가 부족해 신뢰도 보수 조정",
            })

        if price > 0 and price < 10 and asset_type != "ETF":
            adjustments.append({
                "type": "speculative_price",
                "points": -3,
                "reason": "저가 변동성 종목은 투기성 위험을 일부 반영",
            })

        return adjustments

    @staticmethod
    def score_reason(
        quant_score: float,
        news_score: float,
        final_score: float,
        adjustments: list[dict[str, Any]] | None = None,
    ) -> str:
        reason = (
            f"퀀트 {quant_score:.1f}점, 뉴스 {news_score:.1f}점, "
            f"최종 {final_score:.1f}점"
        )
        labels = [
            f"{item.get('reason', '')}({safe_number(item.get('points', 0)):+.0f})"
            for item in adjustments or []
            if item.get("reason")
        ]

        if labels:
            reason += " | 보정: " + "; ".join(labels)

        return reason

    @staticmethod
    def news_normalized_score(result) -> float:
        if result is None:
            return 0.0

        raw_news = safe_number(getattr(result, "news", 0))
        raw_news = max(min(raw_news, 20), -20)
        return ((raw_news + 20) / 40) * 100

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
            return "SPEC BUY" if speculative else "BUY"
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
