from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_ALIASES = {
    "엔비디아": ("NVIDIA", "NVDA"),
    "마이크로소프트": ("Microsoft", "MSFT"),
    "애플": ("Apple", "AAPL"),
    "아마존": ("Amazon", "AMZN"),
    "메타": ("Meta", "META"),
    "알파벳": ("Alphabet", "GOOGL"),
    "구글": ("Alphabet", "GOOGL"),
    "테슬라": ("Tesla", "TSLA"),
    "레졸루트": ("Rezolute", "RZLT"),
    "리졸루트": ("Rezolute", "RZLT"),
    "팔란티어": ("Palantir", "PLTR"),
    "브로드컴": ("Broadcom", "AVGO"),
    "코카콜라": ("Coca-Cola", "KO"),
    "오라클": ("Oracle", "ORCL"),
    "엑슨모빌": ("Exxon Mobil", "XOM"),
    "엑슨 모빌": ("Exxon Mobil", "XOM"),
    "tsmc": ("TSMC", "TSM"),
}


@dataclass
class StockResolver:
    app_root: Path
    search_service_factory: Any | None = None

    def resolve(self, name: str = "", code: str = "") -> dict[str, str] | None:
        name = (name or "").strip()
        code = (code or "").strip().upper()

        if code and name:
            return {"name": name, "code": self.normalize_code(code)}

        keyword = code or name

        if not keyword:
            return None

        resolved = self.resolve_keyword(keyword)

        if resolved:
            return resolved

        if code:
            return {"name": name or code, "code": self.normalize_code(code)}

        return None

    def resolve_keyword(self, keyword: str) -> dict[str, str] | None:
        keyword = (keyword or "").strip()

        if not keyword:
            return None

        normalized = keyword.upper()
        local_result = self.resolve_with_local_files(keyword)

        if local_result:
            return local_result

        if normalized.isdigit() or "." in normalized:
            return {"name": normalized, "code": self.normalize_code(normalized)}

        service_result = self.resolve_with_search_service(keyword)

        if service_result:
            return service_result

        if normalized.isascii() and len(normalized) <= 8:
            return {"name": keyword, "code": normalized}

        return None

    def resolve_with_search_service(self, keyword: str) -> dict[str, str] | None:
        if self.search_service_factory is None:
            return None

        try:
            results = self.search_service_factory().search(keyword)
        except Exception:
            return None

        if not results:
            return None

        first = results[0]
        code = (
            first.get("code")
            or first.get("symbol")
            or first.get("ticker")
            or ""
        )
        name = first.get("name") or first.get("company") or code

        if not code:
            return None

        return {"name": name, "code": self.normalize_code(code)}

    def resolve_with_local_files(self, keyword: str) -> dict[str, str] | None:
        lower = keyword.lower()
        krx_path = self.app_root / "cache" / "krx_list.csv"

        if krx_path.exists():
            try:
                with krx_path.open("r", encoding="utf-8-sig", newline="") as file:
                    for row in csv.DictReader(file):
                        code = (row.get("code") or "").strip()
                        name = (row.get("name") or "").strip()

                        if (
                            keyword == code
                            or lower in name.lower()
                            or lower == name.lower()
                        ):
                            return {"name": name or code, "code": code}
            except Exception:
                pass

        us_path = (
            self.app_root
            / "src"
            / "morning_stock_assistant"
            / "collectors"
            / "market"
            / "us_stock_list.json"
        )

        if us_path.exists():
            try:
                data = json.loads(us_path.read_text(encoding="utf-8"))

                for ticker, info in data.items():
                    stock_name = str(info.get("name") or ticker)

                    if (
                        lower == ticker.lower()
                        or lower in stock_name.lower()
                        or lower == stock_name.lower()
                    ):
                        return {"name": stock_name, "code": ticker.upper()}
            except Exception:
                pass

        alias = DEFAULT_ALIASES.get(keyword) or DEFAULT_ALIASES.get(lower)

        if alias:
            alias_name, alias_code = alias
            return {"name": alias_name, "code": alias_code}

        return None

    @staticmethod
    def normalize_code(code: str) -> str:
        code = str(code or "").strip().upper()

        if code.endswith(".KS") or code.endswith(".KQ"):
            return code.split(".")[0]

        return code
