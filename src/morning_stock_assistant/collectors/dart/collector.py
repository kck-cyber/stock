"""
DART Collector

OpenDART API Collector
"""

from pathlib import Path
import requests

from .corp_code import CorpCodeManager


class DartCollector:

    BASE_URL = "https://opendart.fss.or.kr/api"

    def __init__(self, api_key: str, cache_dir: Path):
        self.api_key = api_key
        self.corp = CorpCodeManager(api_key, cache_dir)

    # --------------------------------------------------
    # 종목코드 → CorpCode
    # --------------------------------------------------
    def get_corp_code(self, stock_code: str):

        if not self.corp.mapping:
            self.corp.update()

        return self.corp.get(stock_code)

    # --------------------------------------------------
    # 회사정보
    # --------------------------------------------------
    def get_company_info(self, stock_code: str):

        corp_code = self.get_corp_code(stock_code)

        if corp_code is None:
            return None

        url = f"{self.BASE_URL}/company.json"

        params = {
            "crtfc_key": self.api_key,
            "corp_code": corp_code,
        }

        try:

            response = requests.get(
                url,
                params=params,
                timeout=10
            )

            response.raise_for_status()

            return response.json()

        except Exception:

            return None

    # --------------------------------------------------
    # 재무 RAW
    # --------------------------------------------------
    def get_financial_raw(
        self,
        stock_code,
        business_year,
        report_code,
    ):

        corp_code = self.get_corp_code(stock_code)

        if corp_code is None:
            return None

        url = f"{self.BASE_URL}/fnlttSinglAcnt.json"

        params = {

            "crtfc_key": self.api_key,

            "corp_code": corp_code,

            "bsns_year": business_year,

            "reprt_code": report_code,

        }

        try:

            response = requests.get(
                url,
                params=params,
                timeout=20
            )

            response.raise_for_status()

            data = response.json()

            if data.get("status") != "000":
                return None

            return data

        except Exception:

            return None

    # --------------------------------------------------
    # 재무 가공
    # --------------------------------------------------
    def get_financial_statement(
        self,
        stock_code,
        business_year,
        report_code,
    ):

        data = self.get_financial_raw(
            stock_code,
            business_year,
            report_code
        )

        if not data:
            return None

        financial = {

            "sales": 0,
            "operating_profit": 0,
            "net_income": 0,

            "assets": 0,
            "liabilities": 0,
            "equity": 0,

            "roe": 0,
            "debt_ratio": 0,

            "eps": 0,
            "bps": 0,

            # ---------- v1.0 ----------

            "sales_growth": 0,
            "op_growth": 0,
            "eps_growth": 0,
            "bps_growth": 0,

            "roa": 0,

            "operating_margin": 0,
            "net_margin": 0,

            "current_ratio": 0,

            "free_cash_flow": 0,
            "operating_cash_flow": 0,
            "capex": 0,
            "cash": 0,
            "total_debt": 0,

            "dividend_yield": 0,

        }

        for row in data.get("list", []):

            account = row.get("account_nm", "")

            amount = row.get("thstrm_amount", "0")

            try:
                value = int(
                    str(amount).replace(",", "")
                )

            except Exception:

                value = 0

            if account == "매출액":

                financial["sales"] = value

            elif account == "영업이익":

                financial["operating_profit"] = value

            elif account == "당기순이익":

                financial["net_income"] = value

            elif account == "자산총계":

                financial["assets"] = value

            elif account == "부채총계":

                financial["liabilities"] = value

            elif account == "자본총계":

                financial["equity"] = value

            elif account in ("영업활동현금흐름", "영업활동으로인한현금흐름"):

                financial["operating_cash_flow"] = value

            elif account in ("투자활동현금흐름", "유형자산의 취득", "유형자산취득"):

                financial["capex"] = abs(value)

            elif account in ("현금및현금성자산", "현금 및 현금성자산"):

                financial["cash"] = value

            elif account in ("차입금", "단기차입금", "장기차입금", "사채"):

                financial["total_debt"] += value

        # --------------------
        # 계산
        # --------------------

        if financial["equity"] > 0:

            financial["roe"] = round(

                financial["net_income"] /
                financial["equity"] * 100,

                2

            )

            financial["debt_ratio"] = round(

                financial["liabilities"] /
                financial["equity"] * 100,

                2

            )

        if financial["assets"] > 0:

            financial["roa"] = round(

                financial["net_income"] /
                financial["assets"] * 100,

                2

            )

        if financial["sales"] > 0:

            financial["operating_margin"] = round(

                financial["operating_profit"] /
                financial["sales"] * 100,

                2

            )

            financial["net_margin"] = round(

                financial["net_income"] /
                financial["sales"] * 100,

                2

            )

        if not financial["free_cash_flow"] and financial["operating_cash_flow"]:
            financial["free_cash_flow"] = (
                financial["operating_cash_flow"] - financial["capex"]
            )

        return financial
