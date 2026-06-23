"""
KRX Collector

- 한국거래소 종목 마스터 데이터 수집
- KOSPI / KOSDAQ 통합 종목 리스트
- stock_code ↔ stock_name 매핑 제공
"""

from pathlib import Path
import pandas as pd
import requests


class KRXCollector:
    """
    KRX 종목 데이터 수집기
    """

    # KRX 상장법인 목록 (엑셀)
    KRX_LIST_URL = "http://kind.krx.co.kr/corpgeneral/corpList.do"

    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.cache_file = self.cache_dir / "krx_list.csv"

        # 구조:
        # {
        #   "005930": {
        #       "name": "삼성전자",
        #       "market": "KOSPI"
        #   }
        # }
        self.data = {}

        self._loaded = False

    # --------------------------------------------------
    # 다운로드
    # --------------------------------------------------
    def download(self):
        """
        KRX 상장법인 목록 다운로드
        """
        try:
            params = {
                "method": "download",
                "searchType": "13",
            }

            response = requests.get(self.KRX_LIST_URL, params=params, timeout=20)
            response.raise_for_status()

            # KRX는 HTML이 아니라 Excel 다운로드 형태
            df = pd.read_html(response.text, header=0)[0]

            # 필요한 컬럼 정리
            df = df.rename(columns={
                "종목코드": "code",
                "회사명": "name",
                "시장구분": "market"
            })

            df["code"] = df["code"].astype(str).str.zfill(6)

            df.to_csv(self.cache_file, index=False, encoding="utf-8-sig")

            return True

        except Exception:
            return False

    # --------------------------------------------------
    # 로드
    # --------------------------------------------------
    def load(self):
        """
        로컬 CSV 로드
        """
        try:
            if not self.cache_file.exists():
                self.download()

            df = pd.read_csv(self.cache_file)

            data = {}

            for _, row in df.iterrows():
                code = str(row["code"]).zfill(6)

                data[code] = {
                    "name": row.get("name"),
                    "market": row.get("market"),
                }

            self.data = data
            self._loaded = True

            return True

        except Exception:
            return False

    # --------------------------------------------------
    # 전체 업데이트
    # --------------------------------------------------
    def update(self):
        """
        최신 KRX 데이터 갱신
        """
        if not self.download():
            return False

        return self.load()

    # --------------------------------------------------
    # 단일 조회
    # --------------------------------------------------
    def get(self, stock_code: str):
        """
        종목 정보 조회
        """
        if not self._loaded or not self.data:
            self.load()

        return self.data.get(stock_code)

    # --------------------------------------------------
    # 종목명 조회
    # --------------------------------------------------
    def get_name(self, stock_code: str):
        item = self.get(stock_code)
        return item["name"] if item else None

    # --------------------------------------------------
    # 시장 조회
    # --------------------------------------------------
    def get_market(self, stock_code: str):
        item = self.get(stock_code)
        return item["market"] if item else None