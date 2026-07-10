from datetime import datetime
import email.utils
import feedparser
import requests
import time
from bs4 import BeautifulSoup
from urllib.parse import quote


class NewsCollector:
    EVENT_RULES = (
        ("실적 호조", 12, ("어닝 서프라이즈", "최대 실적", "사상 최대", "실적 개선", "흑자전환", "영업이익 증가", "매출 증가")),
        ("수주/계약", 10, ("수주", "계약", "공급", "납품", "파트너십")),
        ("신제품/승인", 8, ("신제품", "출시", "승인", "허가", "임상 성공")),
        ("목표가 상향", 7, ("목표가 상향", "투자의견 상향", "매수 의견", "매수")),
        ("주주환원", 8, ("자사주", "배당 확대", "배당 증가", "특별배당")),
        ("정책/산업 수혜", 6, ("정책 수혜", "수혜", "지원", "보조금")),
        ("실적 부진", -12, ("어닝 쇼크", "실적 부진", "적자전환", "영업손실", "손실 확대")),
        ("규제/소송", -12, ("소송", "제재", "과징금", "검찰", "압수수색", "규제")),
        ("거래 위험", -15, ("거래정지", "상장폐지", "감자")),
        ("주주가치 희석", -8, ("유상증자", "전환사채", "CB 발행", "신주인수권")),
        ("목표가 하향", -7, ("목표가 하향", "투자의견 하향", "매도 의견", "매도")),
        ("품질/리콜", -9, ("리콜", "결함", "반품")),
    )

    POSITIVE_KEYWORDS = {
        "상한가": 4,
        "급등": 3,
        "강세": 2,
        "상승": 2,
        "반등": 2,
        "호재": 3,
        "수주": 3,
        "계약": 2,
        "공급": 2,
        "실적 개선": 3,
        "어닝 서프라이즈": 4,
        "흑자전환": 4,
        "흑자": 2,
        "영업이익 증가": 3,
        "매출 증가": 2,
        "최대 실적": 4,
        "사상 최대": 4,
        "증가": 1,
        "성장": 2,
        "확대": 1,
        "증설": 2,
        "투자": 1,
        "인수": 1,
        "합병": 1,
        "자사주": 2,
        "배당 확대": 3,
        "목표가 상향": 3,
        "매수": 2,
        "기대": 1,
        "개선": 2,
        "승인": 2,
    }

    NEGATIVE_KEYWORDS = {
        "하한가": -4,
        "급락": -3,
        "약세": -2,
        "하락": -2,
        "악재": -3,
        "적자전환": -4,
        "적자": -3,
        "영업손실": -3,
        "손실": -2,
        "실적 부진": -3,
        "어닝 쇼크": -4,
        "감소": -2,
        "둔화": -2,
        "축소": -1,
        "리콜": -3,
        "소송": -3,
        "압수수색": -4,
        "검찰": -2,
        "과징금": -3,
        "제재": -3,
        "거래정지": -4,
        "상장폐지": -5,
        "유상증자": -2,
        "감자": -4,
        "목표가 하향": -3,
        "매도": -2,
        "우려": -1,
        "불확실": -1,
        "부담": -1,
    }

    def __init__(self):

        self.cache = {}
        self.cache_ttl_seconds = 600

    def get_news(self, keyword, limit=5):

        cache_key = (keyword, limit)
        cached = self.cache.get(cache_key)

        if cached:
            created_at, news = cached

            if time.time() - created_at <= self.cache_ttl_seconds:
                return news

            self.cache.pop(cache_key, None)

        news = self._get_google_news(keyword, limit)

        news = self._attach_sentiment(news)

        if news:
            self.cache[cache_key] = (time.time(), news)
            return news

        news = self._get_naver_news(keyword, limit)
        news = self._attach_sentiment(news)
        self.cache[cache_key] = (time.time(), news)
        return news

    def _get_google_news(self, keyword, limit):

        try:
            url = (
                "https://news.google.com/rss/search?"
                f"q={quote(keyword)}&hl=ko&gl=KR&ceid=KR:ko"
            )

            feed = feedparser.parse(url)
            news = []

            for entry in feed.entries[:limit]:
                published = (
                    entry.get("published")
                    or entry.get("updated")
                    or ""
                )

                news.append({
                    "title": entry.get("title", ""),
                    "url": entry.get("link", ""),
                    "date": self._format_date(published),
                })

            return news

        except Exception as e:
            print("Google news RSS load failed:", e)
            return []

    def _get_naver_news(self, keyword, limit):

        url = (
            f"https://search.naver.com/search.naver?"
            f"where=news&query={quote(keyword)}"
        )

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        try:
            html = requests.get(
                url,
                headers=headers,
                timeout=10
            ).text

            soup = BeautifulSoup(html, "html.parser")
            news = []
            seen = set()

            for item in soup.select("a.news_tit, a.JtKRv"):
                title = item.get("title") or item.get_text(strip=True)
                link = item.get("href")

                if (
                    not title
                    or title in ("네이버뉴스", "언론사 선정")
                    or not link
                    or link in seen
                ):
                    continue

                date = self._find_nearby_date(item)
                seen.add(link)
                news.append({
                    "title": title,
                    "url": link,
                    "date": date,
                })

                if len(news) >= limit:
                    return news

            return news

        except Exception as e:
            print("Naver news load failed:", e)
            return []

    @staticmethod
    def _format_date(value):

        if not value:
            return ""

        try:
            parsed = email.utils.parsedate_to_datetime(value)
            return parsed.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return str(value)

    @staticmethod
    def _find_nearby_date(item):

        parent = item

        for _ in range(4):
            parent = parent.parent

            if not parent:
                break

            text = parent.get_text(" ", strip=True)

            for token in text.split():
                if (
                    "전" in token
                    or "." in token
                    or "-" in token
                ):
                    return token

        return ""

    def _attach_sentiment(self, news):

        for item in news:
            sentiment = self.analyze_sentiment(
                item.get("title", "")
            )
            item["sentiment_score"] = sentiment["score"]
            item["sentiment_label"] = sentiment["label"]
            item["impact_score"] = sentiment["impact_score"]
            item["impact_label"] = sentiment["impact_label"]
            item["event_type"] = sentiment["event_type"]
            item["matched_keywords"] = sentiment["matched_keywords"]

        return news

    def analyze_sentiment(self, text):

        score = 0
        matched_positive = []
        matched_negative = []

        for word, weight in self.POSITIVE_KEYWORDS.items():
            if word in text:
                score += weight
                matched_positive.append(word)

        for word, weight in self.NEGATIVE_KEYWORDS.items():
            if word in text:
                score += weight
                matched_negative.append(word)

        event_type = "일반 뉴스"
        event_score = 0
        matched_event_keywords = []

        for name, weight, keywords in self.EVENT_RULES:
            matched = [word for word in keywords if word in text]

            if not matched:
                continue

            if abs(weight) > abs(event_score):
                event_type = name
                event_score = weight
                matched_event_keywords = matched

        impact_score = event_score + score
        impact_score = max(min(impact_score, 20), -20)

        if impact_score >= 10:
            impact_label = "강한 호재"
        elif impact_score >= 4:
            impact_label = "호재"
        elif impact_score <= -10:
            impact_label = "강한 악재"
        elif impact_score <= -4:
            impact_label = "악재"
        else:
            impact_label = "중립"

        if score >= 5:
            label = "매우 긍정"
        elif score >= 2:
            label = "긍정"
        elif score <= -5:
            label = "매우 부정"
        elif score <= -2:
            label = "부정"
        else:
            label = "중립"

        return {
            "score": max(min(score, 10), -10),
            "label": label,
            "positive": matched_positive,
            "negative": matched_negative,
            "impact_score": impact_score,
            "impact_label": impact_label,
            "event_type": event_type,
            "matched_keywords": (
                matched_event_keywords
                or matched_positive
                or matched_negative
            ),
        }

    def get_news_score(self, stock_name):

        news = self.get_news(stock_name, limit=10)

        if not news:
            return 0

        score = 0

        for index, item in enumerate(news):
            sentiment_score = item.get("impact_score")

            if sentiment_score is None:
                sentiment_score = self.analyze_sentiment(
                    item.get("title", "")
                )["impact_score"]

            recent_weight = 1.0 if index < 3 else 0.7
            score += sentiment_score * recent_weight

        return round(max(min(score, 20), -20), 2)
