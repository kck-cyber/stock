from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from morning_stock_assistant.shared.analysis_bridge import SharedAnalysisBridge


class FakeKrx:
    def get_market(self, code: str) -> str:
        return "KOSPI"


class FakePrice:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def get_history(self, stock_code: str, period: str = "1mo", interval=None):
        self.calls.append(stock_code)
        index = pd.to_datetime([
            "2026-07-01",
            "2026-07-02",
            "2026-07-03",
            "2026-07-04",
        ])
        return pd.DataFrame(
            {"Close": [85000, 0, None, 86000]},
            index=index,
        )


class ChartApiTest(unittest.TestCase):
    def test_chart_data_uses_kospi_ticker_and_points(self):
        for code in ["005930", "000660", "035420"]:
            with self.subTest(code=code):
                bridge = object.__new__(SharedAnalysisBridge)
                price = FakePrice()
                bridge.service = SimpleNamespace(price=price, krx=FakeKrx())

                data = bridge.chart_data(code, period="1mo", interval="1d")

                self.assertEqual(price.calls, [f"{code}.KS"])
                self.assertEqual(data["code"], code)
                self.assertEqual(data["ticker"], f"{code}.KS")
                self.assertEqual(data["period"], "1mo")
                self.assertEqual(data["interval"], "1d")
                self.assertEqual(data["values"], [85000, 86000])
                self.assertEqual(
                    data["points"],
                    [
                        {"date": "2026-07-01", "close": 85000},
                        {"date": "2026-07-04", "close": 86000},
                    ],
                )
                self.assertIsNone(data["error"])

    def test_chart_api_keeps_values_and_adds_points(self):
        import server.main as server_main

        original_get_bridge = server_main.get_bridge
        server_main.chart_cache.clear()

        class FakeBridge:
            def chart_data(self, request_code, period="1mo", interval=None):
                ticker = f"{request_code.upper()}.KS"
                return {
                    "code": request_code.upper(),
                    "ticker": ticker,
                    "period": period,
                    "interval": interval,
                    "values": [85000, 86000],
                    "points": [
                        {"date": "2026-07-01", "close": 85000},
                        {"date": "2026-07-02", "close": 86000},
                    ],
                    "error": None,
                }

        try:
            server_main.get_bridge = lambda: FakeBridge()
            client = TestClient(server_main.app)

            for code in ["005930", "000660", "035420"]:
                with self.subTest(code=code):
                    response = client.get(
                        f"/api/chart/{code}?period=1mo&interval=1d"
                    )

                    self.assertEqual(response.status_code, 200)
                    data = response.json()
                    self.assertEqual(data["code"], code)
                    self.assertEqual(data["ticker"], f"{code}.KS")
                    self.assertEqual(data["values"], [85000, 86000])
                    self.assertEqual(
                        data["points"][0],
                        {"date": "2026-07-01", "close": 85000},
                    )
        finally:
            server_main.get_bridge = original_get_bridge
            server_main.chart_cache.clear()

    def test_chart_api_uses_cache_for_repeated_request(self):
        import server.main as server_main

        original_get_bridge = server_main.get_bridge
        server_main.chart_cache.clear()
        calls = {"count": 0}

        class FakeBridge:
            def chart_data(self, request_code, period="1mo", interval=None):
                calls["count"] += 1
                return {
                    "code": request_code.upper(),
                    "ticker": f"{request_code.upper()}.KS",
                    "period": period,
                    "interval": interval,
                    "values": [85000, 86000],
                    "points": [
                        {"date": "2026-07-01", "close": 85000},
                        {"date": "2026-07-02", "close": 86000},
                    ],
                    "error": None,
                }

        try:
            server_main.get_bridge = lambda: FakeBridge()
            client = TestClient(server_main.app)

            first = client.get("/api/chart/005930?period=1mo&interval=1d").json()
            second = client.get("/api/chart/005930?period=1mo&interval=1d").json()

            self.assertEqual(calls["count"], 1)
            self.assertFalse(first["cached"])
            self.assertTrue(second["cached"])
            self.assertEqual(second["values"], [85000, 86000])
        finally:
            server_main.get_bridge = original_get_bridge
            server_main.chart_cache.clear()


if __name__ == "__main__":
    unittest.main()
