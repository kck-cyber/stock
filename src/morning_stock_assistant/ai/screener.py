"""
Quant Stock Screener

- 전체 종목 필터링
- 조건 기반 퀀트 스크리닝
"""

class StockScreener:
    """
    퀀트 종목 필터
    """

    def __init__(self, stock_service, analyzer):
        self.service = stock_service
        self.analyzer = analyzer

    # --------------------------------------------------
    # 기본 스크리닝
    # --------------------------------------------------
    def screen(self, stock_list, year, report_code,
               min_score=60,
               signal_filter=["BUY", "STRONG BUY"]):

        results = []

        for stock_code in stock_list:

            try:
                analysis = self.analyzer.analyze(
                    stock_code,
                    year,
                    report_code
                )

                if not analysis:
                    continue

                # 조건 필터
                if analysis.score >= min_score and analysis.signal in signal_filter:
                    results.append(analysis)

            except Exception:
                continue

        # 점수 기준 정렬
        results.sort(key=lambda x: x.score, reverse=True)

        return results