"""
Yahoo Finance Price Collector

- 실시간 주가 데이터 수집
- 한국 주식 (KRX → .KS / .KQ)
"""

import yfinance as yf


class YahooPriceCollector:
    """
    가격 데이터 수집기
    """

    def _to_ticker(self, stock_code: str):
        """
        KRX 코드 → Yahoo ticker 변환
        """
        # 삼성전자 005930 → 005930.KS
        # 코스닥도 동일하게 KS 사용 (단순화)
        return f"{stock_code}.KS"

    # --------------------------------------------------
    # 현재가
    # --------------------------------------------------
    def get_price(self, stock_code: str):
        try:
            ticker = self._to_ticker(stock_code)
            data = yf.Ticker(ticker)

            info = data.fast_info

            return {
                "price": info.get("last_price"),
                "prev_close": info.get("previous_close"),
                "currency": info.get("currency"),
            }

        except Exception:
            return None

    # --------------------------------------------------
    # 등락률
    # --------------------------------------------------
    def get_change_rate(self, stock_code: str):
        try:
            price_data = self.get_price(stock_code)

            if not price_data:
                return None

            price = price_data["price"]
            prev = price_data["prev_close"]

            if not price or not prev:
                return None

            change = ((price - prev) / prev) * 100

            return round(change, 2)

        except Exception:
            return None
        

    def get_history(self, stock_code: str, period="1y"):
        """
        과거 가격 데이터
        """

        try:
            ticker = self._to_ticker(stock_code)
            data = yf.Ticker(ticker)

            hist = data.history(period=period)

            if hist.empty:
                return None

            return hist[["Close"]]

        except Exception:
            return None