

class PortfolioEngine:

    def __init__(self, stock_service):
        self.service = stock_service

    # ----------------------------------------
    # 포트폴리오 생성
    # ----------------------------------------
    def build_portfolio(self, stock_list, year="2024", report_code="11011"):

        scored = []

        for code in stock_list:

            score = self.service.score_stock(code, year, report_code)

            if score is None:
                continue

            scored.append((code, score))

        # 점수 기준 정렬
        scored.sort(key=lambda x: x[1], reverse=True)

        # TOP N 선정
        top = scored[:10]

        total_score = sum([s for _, s in top])

        portfolio = {}

        for code, score in top:

            weight = score / total_score if total_score > 0 else 0

            stock = self.service.get_stock(code, year, report_code)

            portfolio[code] = {
                "name": stock.name,
                "score": score,
                "weight": round(weight * 100, 2),

                "roe": stock.roe,
                "per": stock.per,
                "pbr": stock.pbr,
                "relative_per": stock.relative_per,
                "relative_pbr": stock.relative_pbr,
            }

        return portfolio