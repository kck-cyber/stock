"""
Quant Backtester

- 전략 성과 검증
- 포트폴리오 기반 수익률 계산
"""

import random


class Backtester:
    """
    간단 백테스트 엔진 (v1)
    """

    def __init__(self, stock_service):
        self.service = stock_service

    # --------------------------------------------------
    # 시뮬레이션 백테스트
    # --------------------------------------------------
    def run(self, portfolio, period_years=1):
        """
        포트폴리오 성과 시뮬레이션
        """

        results = []

        total_return = 0
        win_count = 0

        for item in portfolio:

            # ⚠️ 실제 데이터 없으므로 시뮬레이션 모델
            simulated_return = self._simulate_return(item)

            total_return += simulated_return

            if simulated_return > 0:
                win_count += 1

            results.append({
                "code": item["code"],
                "name": item["name"],
                "weight": item["weight"],
                "return": round(simulated_return, 2)
            })

        avg_return = total_return / len(portfolio) if portfolio else 0
        win_rate = (win_count / len(portfolio)) * 100 if portfolio else 0

        return {
            "avg_return": round(avg_return, 2),
            "win_rate": round(win_rate, 2),
            "detail": results
        }

    # --------------------------------------------------
    # 가상 수익률 모델
    # --------------------------------------------------
    def _simulate_return(self, item):
        """
        퀀트 점수 기반 가상 수익률
        """

        base = item["score"] / 100

        noise = random.uniform(-0.15, 0.15)

        return (base * 0.2 + noise) * 100