"""
Naver News Collector

Morning Stock Assistant Pro
"""

from urllib.parse import quote
import feedparser


class NaverNewsCollector:

    def collect(self, keyword: str, limit: int = 5):

        url = (
            "https://news.google.com/rss/search?"
            f"q={quote(keyword)}&hl=ko&gl=KR&ceid=KR:ko"
        )

        feed = feedparser.parse(url)

        news = []

        for item in feed.entries[:limit]:

            news.append({

                "title": item.title,

                "url": item.link,

                "press": "",

                "date": item.published,

            })

        return news