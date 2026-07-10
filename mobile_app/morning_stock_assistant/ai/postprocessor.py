"""
AI Post Processor

Morning Stock Assistant Pro
"""


class PostProcessor:

    @staticmethod
    def process(result: dict) -> dict:

        result = result.copy()

        # ------------------------
        # score
        # ------------------------

        score = result.get("score", 0)

        score = max(0, min(100, int(score)))

        result["score"] = score

        # ------------------------
        # confidence
        # ------------------------

        confidence = result.get("confidence", 0)

        confidence = max(0, min(100, int(confidence)))

        result["confidence"] = confidence

        # ------------------------
        # 목표가
        # ------------------------

        if result.get("target_price", 0) < 0:

            result["target_price"] = 0

        # ------------------------
        # 적정가
        # ------------------------

        if result.get("fair_price", 0) < 0:

            result["fair_price"] = 0

        # ------------------------
        # 투자포인트
        # ------------------------

        if not isinstance(result.get("investment_points"), list):

            result["investment_points"] = []

        # ------------------------
        # 리스크
        # ------------------------

        if not isinstance(result.get("risk_factors"), list):

            result["risk_factors"] = []

        return result