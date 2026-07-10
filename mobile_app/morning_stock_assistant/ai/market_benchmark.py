"""
Market Benchmark (v1)

- 업종 평균 PER / PBR
"""

class MarketBenchmark:

    def __init__(self):

        self.data = {
            "IT": {"per": 18, "pbr": 1.8},
            "CHEM": {"per": 12, "pbr": 1.2},
            "BIO": {"per": 25, "pbr": 3.0},
            "OTHER": {"per": 15, "pbr": 1.5},
        }

    def get(self, industry):
        return self.data.get(industry, self.data["OTHER"])