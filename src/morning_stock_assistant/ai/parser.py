"""
AI Response Parser

Morning Stock Assistant Pro
"""

import json
import re


class AIParser:
    """
    GPT 응답을 안전하게 JSON으로 변환한다.
    """

    @staticmethod
    def parse(text: str) -> dict:

        if not text:
            return AIParser.default_result()

        # -----------------------------
        # ```json 제거
        # -----------------------------
        text = re.sub(r"```json", "", text, flags=re.IGNORECASE)
        text = re.sub(r"```", "", text)

        # -----------------------------
        # JSON 부분만 추출
        # -----------------------------
        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end == -1:
            return AIParser.default_result()

        text = text[start:end + 1]

        try:

            result = json.loads(text)

        except json.JSONDecodeError as e:

            print("Parser Error :", e)

            return AIParser.default_result()

        except Exception as e:

            print("Parser Error :", e)

            return AIParser.default_result()

        return AIParser.validate(result)

    # ---------------------------------------------------------

    @staticmethod
    def validate(result: dict) -> dict:

        default = AIParser.default_result()

        # -----------------------------
        # 없는 Key 추가
        # -----------------------------
        for key, value in default.items():

            if key not in result:

                result[key] = value

        # -----------------------------
        # 타입 보정
        # -----------------------------

        if not isinstance(result["investment_points"], list):

            result["investment_points"] = []

        if not isinstance(result["risk_factors"], list):

            result["risk_factors"] = []

        if not isinstance(result["valuation"], dict):

            result["valuation"] = {

                "per": "",

                "pbr": "",

                "roe": "",

            }

        return result

    # ---------------------------------------------------------

    @staticmethod
    def default_result():

        return {

            "score": 0,

            "grade": "분석불가",

            "opinion": "분석 실패",

            "confidence": 0,

            "fair_price": 0,

            "target_price": 0,

            "summary": "AI 분석에 실패했습니다.",

            "investment_points": [],

            "risk_factors": [],

            "valuation": {

                "per": "",

                "pbr": "",

                "roe": "",

            }

        }