from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


def safe_number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class AlertRules:
    score: float = 75
    change: float = 5
    upside: float = 30
    loss: float = -10
    bad_news: float = 35


class AlertEngine:
    def __init__(self, rules: AlertRules | None = None):
        self.rules = rules or AlertRules()

    def build_alerts(
        self,
        records: list[dict[str, Any]],
        holdings: dict[str, dict[str, Any]] | None = None,
        alert_history: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        holdings = holdings or {}
        alert_history = alert_history if alert_history is not None else set()
        now = f"{datetime.now():%H:%M}"
        new_alerts = []

        for record in records:
            code = str(record.get("code", ""))
            name = str(record.get("name") or code)
            final_score = safe_number(record.get("final_score", 0))
            change_1d = safe_number(record.get("change_1d", 0))
            news_score = safe_number(record.get("news_score", 0))
            target_upside = safe_number(record.get("target_upside", 0))
            price = safe_number(record.get("price", 0))
            holding = holdings.get(code, {})
            quantity = safe_number(holding.get("quantity", 0))
            avg_price = safe_number(holding.get("avg_price", 0))

            candidates = []

            if final_score >= self.rules.score:
                candidates.append((
                    "good",
                    "점수 알림",
                    f"{name} 평균 점수 {final_score:.1f}점",
                ))

            if abs(change_1d) >= self.rules.change:
                direction = "상승" if change_1d > 0 else "하락"
                level = "good" if change_1d > 0 else "danger"
                candidates.append((
                    level,
                    "가격 변동",
                    f"{name} 전일 대비 {change_1d:+.2f}% {direction}",
                ))

            if target_upside >= self.rules.upside:
                candidates.append((
                    "watch",
                    "목표가 여력",
                    f"{name} 목표가 대비 +{target_upside:.1f}% 여력",
                ))

            if news_score and news_score <= self.rules.bad_news:
                candidates.append((
                    "danger",
                    "뉴스 경고",
                    f"{name} 뉴스 점수 {news_score:.1f}점",
                ))

            candidates.extend(self.news_alert_candidates(record, name))

            if quantity > 0 and avg_price > 0 and price > 0:
                pnl = ((price - avg_price) / avg_price) * 100

                if pnl <= self.rules.loss:
                    candidates.append((
                        "danger",
                        "보유 손익 경고",
                        f"{name} 평균가 대비 {pnl:.1f}%",
                    ))

            for level, title, message in candidates:
                key = f"{code}:{title}:{message}"

                if key in alert_history:
                    continue

                alert_history.add(key)
                new_alerts.append({
                    "code": code,
                    "name": name,
                    "level": level,
                    "title": title,
                    "message": message,
                    "time": now,
                })

        return new_alerts

    def news_alert_candidates(
        self,
        record: dict[str, Any],
        stock_name: str,
    ) -> list[tuple[str, str, str]]:
        candidates = []

        for news in record.get("news", [])[:5]:
            label = str(news.get("impact_label") or "중립")
            impact_score = safe_number(news.get("impact_score", 0))
            title = str(news.get("title") or "").strip()
            date = str(news.get("date") or "").strip()

            if not title:
                continue

            if "악재" in label or impact_score <= -4:
                level = "danger"
                alert_title = f"뉴스 악재 | {stock_name}"
            elif "호재" in label or impact_score >= 4:
                level = "good"
                alert_title = f"뉴스 호재 | {stock_name}"
            else:
                continue

            summary = self.ai_news_summary(title, label, impact_score, date)
            candidates.append((level, alert_title, summary))

        return candidates

    @classmethod
    def ai_news_summary(
        cls,
        title: str,
        label: str,
        impact_score: float,
        date: str,
    ) -> str:
        cleaned = " ".join(str(title).split())

        if len(cleaned) > 46:
            cleaned = cleaned[:46].rstrip() + "..."

        prefix = f"{label} {impact_score:+.0f}점"

        if date:
            prefix = f"{prefix} | {date}"

        reason = cls.news_reason(title, label, impact_score)
        return f"{prefix} | AI 요약: {reason} ({cleaned})"

    @staticmethod
    def news_reason(title: str, label: str, impact_score: float) -> str:
        text = str(title).lower()
        positive = "호재" in str(label) or impact_score >= 4
        negative = "악재" in str(label) or impact_score <= -4

        keyword_reasons = [
            (["실적", "매출", "영업이익", "순이익", "earnings", "revenue"], "실적 기대와 수익성 변화가 핵심입니다"),
            (["수주", "계약", "공급", "order", "contract"], "수주와 공급 계약이 매출 가시성을 높일 수 있습니다"),
            (["ai", "인공지능", "데이터센터", "반도체", "hbm"], "AI 수요와 기술 투자 흐름이 주가 재료입니다"),
            (["목표가", "상향", "upgrade"], "애널리스트 기대치가 개선된 신호입니다"),
            (["하향", "downgrade"], "애널리스트 기대치가 낮아진 신호입니다"),
            (["규제", "소송", "조사", "제재", "antitrust", "lawsuit"], "규제와 법적 리스크 확인이 필요합니다"),
            (["투자", "증설", "capex"], "투자 확대가 성장 기대와 비용 부담을 함께 만듭니다"),
        ]

        for words, reason in keyword_reasons:
            if any(word.lower() in text for word in words):
                return reason

        if positive:
            return "긍정 재료가 투자심리에 우호적으로 작용할 수 있습니다"

        if negative:
            return "부정 이슈가 단기 변동성을 키울 수 있습니다"

        return "방향성은 중립적이라 가격 반응 확인이 필요합니다"
