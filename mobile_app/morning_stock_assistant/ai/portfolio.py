"""
Quant Portfolio Engine

- 스크리닝 결과 기반 포트폴리오 구성
- 점수 기반 비중 배분
"""

class PortfolioEngine:
    """
    포트폴리오 생성기
    """

    def build(self, screened_list, top_n=10):
        """
        상위 N개 종목으로 포트폴리오 구성
        """

        # 점수 기준 정렬 (혹시 안 되어있을 경우 대비)
        sorted_list = sorted(
            screened_list,
            key=lambda x: x.score,
            reverse=True
        )

        top_items = sorted_list[:top_n]

        total_score = sum(item.score for item in top_items)

        portfolio = []

        for item in top_items:

            weight = (item.score / total_score) * 100 if total_score > 0 else 0

            portfolio.append({
                "code": item.code,
                "name": item.name,
                "score": item.score,
                "signal": item.signal,
                "weight": round(weight, 2)
            })

        return portfolio