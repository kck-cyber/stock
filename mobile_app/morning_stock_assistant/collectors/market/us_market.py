"""
미국 주식 종목 목록
"""

import json
import time
from pathlib import Path
from urllib.parse import quote

import requests


class USMarket:
    EXTRA_STOCKS = {
        "RZLT": {
            "name": "Rezolute"
        },
        "SMCI": {"name": "Super Micro Computer"},
        "ARM": {"name": "Arm Holdings"},
        "COIN": {"name": "Coinbase Global"},
        "HOOD": {"name": "Robinhood Markets"},
        "MSTR": {"name": "MicroStrategy"},
        "APP": {"name": "AppLovin"},
        "IONQ": {"name": "IonQ"},
        "QBTS": {"name": "D-Wave Quantum"},
        "RKLB": {"name": "Rocket Lab"},
        "ASTS": {"name": "AST SpaceMobile"},
        "SMR": {"name": "NuScale Power"},
        "OKLO": {"name": "Oklo"},
        "HIMS": {"name": "Hims & Hers Health"},
        "RDDT": {"name": "Reddit"},
        "CRCL": {"name": "Circle Internet Group"},
        "VOO": {"name": "Vanguard S&P 500 ETF"},
        "SPY": {"name": "SPDR S&P 500 ETF Trust"},
        "QQQ": {"name": "Invesco QQQ Trust"},
        "GDX": {"name": "VanEck Gold Miners ETF"},
        "IWM": {"name": "iShares Russell 2000 ETF"},
        "DIA": {"name": "SPDR Dow Jones Industrial Average ETF"},
    }

    KOREAN_ALIASES = {
        "AAPL": ["애플", "아이폰"],
        "MSFT": ["마이크로소프트", "마소"],
        "NVDA": ["엔비디아", "엔비댜", "엔비"],
        "TSLA": ["테슬라"],
        "AMD": ["에이엠디"],
        "META": ["메타", "페이스북", "인스타그램"],
        "AMZN": ["아마존"],
        "GOOGL": ["구글", "알파벳"],
        "GOOG": ["구글", "알파벳"],
        "NFLX": ["넷플릭스"],
        "PLTR": ["팔란티어"],
        "AVGO": ["브로드컴"],
        "ORCL": ["오라클"],
        "CRM": ["세일즈포스"],
        "ADBE": ["어도비"],
        "INTC": ["인텔"],
        "QCOM": ["퀄컴"],
        "MU": ["마이크론"],
        "IBM": ["아이비엠"],
        "SHOP": ["쇼피파이"],
        "UBER": ["우버"],
        "ABNB": ["에어비앤비"],
        "DIS": ["디즈니"],
        "SBUX": ["스타벅스"],
        "MCD": ["맥도날드"],
        "NKE": ["나이키"],
        "COST": ["코스트코"],
        "WMT": ["월마트"],
        "TGT": ["타겟"],
        "KO": ["코카콜라"],
        "PEP": ["펩시"],
        "JPM": ["제이피모건", "JP모건"],
        "BAC": ["뱅크오브아메리카", "뱅오아"],
        "GS": ["골드만삭스"],
        "V": ["비자"],
        "MA": ["마스터카드"],
        "PYPL": ["페이팔"],
        "JNJ": ["존슨앤존슨"],
        "PFE": ["화이자"],
        "MRNA": ["모더나"],
        "LLY": ["일라이릴리"],
        "UNH": ["유나이티드헬스"],
        "XOM": ["엑슨모빌"],
        "CVX": ["셰브론", "쉐브론"],
        "BA": ["보잉"],
        "GE": ["제너럴일렉트릭"],
        "F": ["포드"],
        "GM": ["제너럴모터스"],
        "RIVN": ["리비안"],
        "LCID": ["루시드"],
        "SOFI": ["소파이"],
        "SNOW": ["스노우플레이크"],
        "CRWD": ["크라우드스트라이크"],
        "NOW": ["서비스나우"],
        "SMCI": ["슈퍼마이크로", "슈마컴", "슈퍼마이크로컴퓨터"],
        "ARM": ["암홀딩스", "arm홀딩스"],
        "COIN": ["코인베이스"],
        "HOOD": ["로빈후드"],
        "MSTR": ["마이크로스트래티지", "마이크로스트레티지"],
        "APP": ["앱러빈", "앱로빈", "applovin"],
        "IONQ": ["아이온큐"],
        "QBTS": ["디웨이브", "d-wave", "디웨이브퀀텀"],
        "RKLB": ["로켓랩"],
        "ASTS": ["ast스페이스모바일", "스페이스모바일"],
        "SMR": ["뉴스케일", "뉴스케일파워", "nuscale"],
        "OKLO": ["오클로"],
        "HIMS": ["힘스앤허스", "힘스"],
        "RDDT": ["레딧"],
        "CRCL": ["서클", "circle"],
        "TSM": ["tsmc", "티에스엠씨", "대만반도체"],
        "BABA": ["알리바바"],
        "NIO": ["니오"],
        "RZLT": ["레졸루트", "리졸루트", "rezolute", "resolute"],
        "VOO": ["voo", "뱅가드", "s&p500", "에스앤피500"],
        "SPY": ["spy", "s&p500", "에스앤피500"],
        "QQQ": ["qqq", "나스닥100", "나스닥"],
        "GDX": ["gdx", "금광", "금광주", "골드마이너"],
        "IWM": ["iwm", "러셀2000"],
        "DIA": ["dia", "다우존스"],
    }

    def __init__(self):

        self.data = {}

        path = (
            Path(__file__).parent /
            "us_stock_list.json"
        )

        if path.exists():

            with open(
                path,
                "r",
                encoding="utf-8"
            ) as f:

                self.data = json.load(f)

        for code, info in self.EXTRA_STOCKS.items():
            self.data.setdefault(code, info)

        self.search_cache = {}
        self.search_cache_ttl = 3600

    # ------------------------------------

    def search(self, keyword):

        original_keyword = keyword.strip()
        keyword = original_keyword.lower()

        result = []
        seen = set()

        for code, info in self.data.items():
            aliases = [
                alias.lower()
                for alias in self.KOREAN_ALIASES.get(code, [])
            ]

            if (

                keyword in code.lower()

                or

                keyword in info["name"].lower()

                or

                any(keyword in alias for alias in aliases)

            ):

                result.append({

                    "code": code,

                    "name": info["name"],

                    "market": "US"

                })
                seen.add(code)

        for item in self._search_yahoo(original_keyword):
            code = item["code"]

            if code in seen:
                continue

            seen.add(code)
            result.append(item)

        return result

    def _search_yahoo(self, keyword):

        keyword = keyword.strip()

        if not keyword:
            return []

        cache_key = keyword.lower()
        cached = self.search_cache.get(cache_key)

        if cached:
            created_at, items = cached

            if time.time() - created_at <= self.search_cache_ttl:
                return items

            self.search_cache.pop(cache_key, None)

        try:
            url = (
                "https://query1.finance.yahoo.com/v1/finance/search"
                f"?q={quote(keyword)}&quotesCount=10&newsCount=0"
            )
            response = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=5
            )
            response.raise_for_status()
            payload = response.json()
        except Exception:
            self.search_cache[cache_key] = (time.time(), [])
            return []

        items = []

        for quote_item in payload.get("quotes", []):
            symbol = quote_item.get("symbol", "").strip().upper()
            name = (
                quote_item.get("shortname")
                or quote_item.get("longname")
                or quote_item.get("name")
                or symbol
            )
            quote_type = quote_item.get("quoteType", "")
            exchange = quote_item.get("exchange", "")

            if not symbol or not name:
                continue

            if quote_type not in ("EQUITY", "ETF"):
                continue

            if "." in symbol or "-" in symbol:
                continue

            if exchange not in ("NMS", "NYQ", "ASE", "NCM", "NGM", "PCX", "BTS"):
                continue

            items.append({
                "code": symbol,
                "name": name,
                "market": "US",
            })

        self.search_cache[cache_key] = (time.time(), items)
        return items
