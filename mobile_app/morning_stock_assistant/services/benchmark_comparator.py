class BenchmarkComparator:

    def compare(self, strategy_results, market_results):

        comparison = []

        for i in range(len(strategy_results)):

            year = strategy_results[i]["year"]

            strategy_ret = strategy_results[i]["return"]
            market_ret = market_results[i]["return"]

            comparison.append({
                "year": year,
                "strategy": strategy_ret,
                "market": market_ret,
                "alpha": round(strategy_ret - market_ret, 2)
            })

        return comparison