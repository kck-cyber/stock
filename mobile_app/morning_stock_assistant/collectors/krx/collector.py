"""
KRX Collector

Loads Korean listed stock metadata for search and analysis.
"""

from datetime import datetime
from io import StringIO
from pathlib import Path
import sys
import types

import pandas as pd
import requests


def ensure_pkg_resources_stub():

    if "pkg_resources" in sys.modules:
        return

    module = types.ModuleType("pkg_resources")

    def resource_filename(package, resource):
        import importlib.util

        spec = importlib.util.find_spec(package)

        if spec and spec.submodule_search_locations:
            return str(Path(spec.submodule_search_locations[0]) / resource)

        return resource

    module.resource_filename = resource_filename
    sys.modules["pkg_resources"] = module


class KRXCollector:
    """
    Collector for Korean stock list data.
    """

    KRX_LIST_URL = "http://kind.krx.co.kr/corpgeneral/corpList.do"
    MANUAL_ETFS = {
        "449450": {
            "name": "PLUS K방산",
            "market": "ETF",
        },
    }

    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.cache_file = self.cache_dir / "krx_list.csv"
        self.data = {}
        self._loaded = False

    def download(self):
        """
        Download and cache listed Korean stocks.
        """
        if self._download_from_pykrx():
            return True

        return self._download_from_kind()

    def _download_from_pykrx(self):

        try:
            ensure_pkg_resources_stub()

            from pykrx import stock

            rows = []
            today = datetime.today().strftime("%Y%m%d")

            for market in ("KOSPI", "KOSDAQ", "KONEX"):
                for code in stock.get_market_ticker_list(today, market=market):
                    rows.append({
                        "code": str(code).zfill(6),
                        "name": stock.get_market_ticker_name(code),
                        "market": market,
                    })

            try:
                for code in stock.get_etf_ticker_list(today):
                    rows.append({
                        "code": str(code).zfill(6),
                        "name": stock.get_etf_ticker_name(code),
                        "market": "ETF",
                    })
            except Exception:
                pass

            if not rows:
                return False

            pd.DataFrame(rows).to_csv(
                self.cache_file,
                index=False,
                encoding="utf-8-sig"
            )

            return True

        except Exception as e:
            print("KRX pykrx download failed:", e)
            return False

    def _download_from_kind(self):

        try:
            params = {
                "method": "download",
                "searchType": "13",
            }

            response = requests.get(
                self.KRX_LIST_URL,
                params=params,
                timeout=20
            )
            response.raise_for_status()
            response.encoding = response.apparent_encoding

            df = pd.read_html(StringIO(response.text), header=0)[0]
            df = self._normalize_kind_columns(df)

            if df.empty:
                return False

            df.to_csv(self.cache_file, index=False, encoding="utf-8-sig")
            return True

        except Exception as e:
            print("KRX KIND download failed:", type(e).__name__, e)
            return False

    @staticmethod
    def _normalize_kind_columns(df):

        columns = {
            str(column).replace(" ", ""): column
            for column in df.columns
        }

        code_column = KRXCollector._find_column(columns, ("종목코드", "code"))
        name_column = KRXCollector._find_column(columns, ("회사명", "종목명", "name"))
        market_column = KRXCollector._find_column(columns, ("시장구분", "market"))

        if code_column is None or name_column is None:
            return pd.DataFrame(columns=["code", "name", "market"])

        result = pd.DataFrame({
            "code": df[code_column].astype(str).str.zfill(6),
            "name": df[name_column].astype(str),
            "market": (
                df[market_column].astype(str)
                if market_column is not None
                else ""
            ),
        })

        return result.dropna(subset=["code", "name"])

    @staticmethod
    def _find_column(columns, candidates):

        lowered = {
            key.lower(): value
            for key, value in columns.items()
        }

        for candidate in candidates:
            candidate = candidate.lower()

            for key, value in lowered.items():
                if candidate in key:
                    return value

        return None

    def load(self):
        """
        Load cached stock metadata, downloading it if needed.
        """
        try:
            if not self.cache_file.exists():
                self.download()

            if not self.cache_file.exists():
                return False

            df = pd.read_csv(self.cache_file, dtype={"code": str})

            if (
                "market" in df.columns
                and "ETF" not in set(df["market"].astype(str))
            ):
                if self.download():
                    df = pd.read_csv(self.cache_file, dtype={"code": str})

            data = {}

            for _, row in df.iterrows():
                code = str(row.get("code", "")).zfill(6)
                name = row.get("name", "")

                if not code or not name:
                    continue

                data[code] = {
                    "name": name,
                    "market": row.get("market", ""),
                }

            data.update(self.MANUAL_ETFS)

            self.data = data
            self._loaded = bool(data)

            return self._loaded

        except Exception as e:
            print("KRX load failed:", e)
            return False

    def update(self):
        """
        Refresh cached stock metadata.
        """
        if not self.download():
            return False

        return self.load()

    def get(self, stock_code: str):
        """
        Get one stock by ticker code.
        """
        if not self._loaded or not self.data:
            self.load()

        return self.data.get(str(stock_code).zfill(6))

    def get_name(self, stock_code: str):
        item = self.get(stock_code)
        return item["name"] if item else None

    def get_market(self, stock_code: str):
        item = self.get(stock_code)
        return item["market"] if item else None

    def search(self, keyword, limit=10):

        keyword = keyword.strip()

        if not keyword:
            return []

        if not self._loaded or not self.data:
            self.load()

        keyword_lower = keyword.lower()
        matches = []

        for code, info in self.data.items():
            name = str(info.get("name", ""))

            if keyword_lower in code.lower() or keyword_lower in name.lower():
                matches.append({
                    "code": code,
                    "name": name,
                    "market": info.get("market", ""),
                })

        matches.sort(key=lambda item: self._search_rank(item, keyword_lower))

        return matches[:limit]

    @staticmethod
    def _search_rank(item, keyword_lower):

        code = item["code"].lower()
        name = item["name"].lower()
        market = item.get("market", "")

        if name == keyword_lower or code == keyword_lower:
            match_rank = 0
        elif code.startswith(keyword_lower):
            match_rank = 1
        elif name.startswith(keyword_lower):
            match_rank = 2
        else:
            match_rank = 3

        spac_rank = 1 if "스팩" in name else 0

        if market in ("유가", "KOSPI"):
            market_rank = 0
        elif market in ("코스닥", "KOSDAQ"):
            market_rank = 1
        else:
            market_rank = 2

        return (
            match_rank,
            spac_rank,
            market_rank,
            len(name),
            name,
            code,
        )
