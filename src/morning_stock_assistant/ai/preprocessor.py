"""
AI Data Preprocessor

Morning Stock Assistant Pro
"""


class DataPreprocessor:

    @staticmethod
    def preprocess_company(data: dict) -> dict:

        result = data.copy()

        # ------------------------
        # 현재가
        # ------------------------

        if result.get("current_price"):

            result["current_price"] = f"{result['current_price']:,}원"

        # ------------------------
        # 시가총액
        # ------------------------

        if result.get("market_cap"):

            cap = result["market_cap"]

            if cap >= 1_000_000_000:

                result["market_cap"] = f"{cap/1_000_000_000:.2f}B"

            else:

                result["market_cap"] = f"{cap:,}"

        # ------------------------
        # PER
        # ------------------------

        if result.get("per"):

            result["per"] = round(result["per"], 2)

        # ------------------------
        # EPS
        # ------------------------

        if result.get("eps"):

            result["eps"] = round(result["eps"], 2)

        return result