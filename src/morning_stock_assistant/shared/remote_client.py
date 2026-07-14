from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class RemoteAnalysisClient:
    def __init__(self, base_url: str, timeout: int = 240):
        self.base_url = str(base_url or "").strip().rstrip("/")
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return self.base_url.startswith(("http://", "https://"))

    def build_records(
        self,
        stocks: list[dict[str, Any]],
        holdings: dict[str, dict[str, Any]] | None = None,
        preset: str = "균형형",
        analyze: bool = True,
        max_workers: int = 6,
    ) -> list[dict[str, Any]]:
        data = self._post_json(
            "/api/records",
            {
                "stocks": stocks,
                "holdings": holdings or {},
                "preset": preset,
                "analyze": analyze,
                "max_workers": max_workers,
            },
        )
        records = data.get("records", [])

        if not isinstance(records, list):
            raise RuntimeError("서버 응답 형식이 올바르지 않습니다.")

        return records

    def chart_values(
        self,
        code: str,
        period: str = "1mo",
        interval: str | None = None,
    ) -> list[float]:
        return self.chart_data(
            code,
            period=period,
            interval=interval,
        ).get("values", [])

    def chart_data(
        self,
        code: str,
        period: str = "1mo",
        interval: str | None = None,
    ) -> dict[str, Any]:
        params = {"period": period}

        if interval:
            params["interval"] = interval

        query = urllib.parse.urlencode(params)
        data = self._get_json(f"/api/chart/{code}?{query}")
        values = data.get("values", [])
        points = data.get("points", [])

        if not isinstance(values, list):
            values = []

        if not isinstance(points, list):
            points = []

        if points:
            point_values = [
                item.get("close")
                for item in points
                if isinstance(item, dict) and item.get("close")
            ]

            if point_values:
                values = point_values

        data["values"] = values
        data["points"] = points
        return data

    def health(self) -> dict[str, Any]:
        return self._get_json("/health")

    def search(self, keyword: str, limit: int = 20) -> list[dict[str, Any]]:
        query = urllib.parse.urlencode({
            "keyword": keyword,
            "limit": limit,
        })
        data = self._get_json(f"/search?{query}")
        results = data.get("results", [])

        if not isinstance(results, list):
            return []

        return results

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._ensure_enabled()
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return self._open_json(request)

    def _get_json(self, path: str) -> dict[str, Any]:
        self._ensure_enabled()
        request = urllib.request.Request(f"{self.base_url}{path}", method="GET")
        return self._open_json(request)

    def _open_json(self, request: urllib.request.Request) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"HTTP {exc.code}: {detail[:180]}") from exc

    def _ensure_enabled(self) -> None:
        if not self.enabled:
            raise RuntimeError("서버 URL이 설정되지 않았습니다.")
