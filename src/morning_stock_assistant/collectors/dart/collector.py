"""
DART Collector

OpenDART API Collector
"""

from pathlib import Path
import requests

from .corp_code import CorpCodeManager


class DartCollector:
    """
    OpenDART API 기반 재무/기업정보 수집기
    """

    BASE_URL = "https://opendart.fss.or.kr/api"

    def __init__(self, api_key: str, cache_dir: Path):
        self.api_key = api_key
        self.corp = CorpCodeManager(api_key, cache_dir)

    # --------------------------------------------------
    # 종목코드 → CorpCode
    # --------------------------------------------------
    def get_corp_code(self, stock_code: str):
        """
        stock_code → DART corp_code 변환
        """
        if not self.corp.mapping:
            self.corp.update()

        return self.corp.get(stock_code)

    # --------------------------------------------------
    # 회사 기본 정보
    # --------------------------------------------------
    def get_company_info(self, stock_code: str):
        """
        회사 기본 정보 조회
        """
        corp_code = self.get_corp_code(stock_code)
        if corp_code is None:
            return None

        url = f"{self.BASE_URL}/company.json"
        params = {
            "crtfc_key": self.api_key,
            "corp_code": corp_code,
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

    # --------------------------------------------------
    # 재무제표 raw 데이터
    # --------------------------------------------------
    def get_financial_raw(
        self,
        stock_code: str,
        business_year: str,
        report_code: str,
    ):
        """
        OpenDART 원본 재무제표 데이터
        """
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
            response = requests.get(url, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "000":
                return None

            return data

        except Exception:
            return None

    # --------------------------------------------------
    # 재무제표 가공 데이터
    # --------------------------------------------------
    def get_financial_statement(
        self,
        stock_code: str,
        business_year: str,
        report_code: str,
    ):
        """
        재무제표 핵심 지표 추출 (가공)
        """

        data = self.get_financial_raw(stock_code, business_year, report_code)
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
        }

        for row in data.get("list", []):
            account = row.get("account_nm", "")
            amount = row.get("thstrm_amount", "0")

            try:
                value = int(str(amount).replace(",", ""))
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

        # ROE
        if financial["equity"] > 0:
            financial["roe"] = round(
                financial["net_income"] / financial["equity"] * 100,
                2,
            )

            financial["debt_ratio"] = round(
                financial["liabilities"] / financial["equity"] * 100,
                2,
            )

        return financial