"""
DART Corp Code Manager

종목코드 → DART Corp Code 변환
"""

from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

import requests


class CorpCodeManager:

    DART_URL = "https://opendart.fss.or.kr/api/corpCode.xml"

    def __init__(self, api_key: str, cache_dir: Path):

        self.api_key = api_key

        self.cache_dir = Path(cache_dir)

        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.xml_file = self.cache_dir / "CORPCODE.xml"

        self.mapping = {}

    def update(self):

        params = {

            "crtfc_key": self.api_key

        }

        response = requests.get(self.DART_URL, params=params, timeout=30)

        response.raise_for_status()

        zip_path = self.cache_dir / "corpcode.zip"

        zip_path.write_bytes(response.content)

        with zipfile.ZipFile(zip_path, "r") as z:

            z.extractall(self.cache_dir)

        zip_path.unlink()

        self.load()

    def load(self):

        if not self.xml_file.exists():

            raise FileNotFoundError(self.xml_file)

        tree = ET.parse(self.xml_file)

        root = tree.getroot()

        self.mapping.clear()

        for item in root.findall("list"):

            stock_code = item.findtext("stock_code")

            corp_code = item.findtext("corp_code")

            if stock_code:

                self.mapping[stock_code] = corp_code

    def get(self, stock_code: str):

        if not self.mapping:

            if self.xml_file.exists():

                self.load()

            else:

                self.update()

        return self.mapping.get(stock_code)