class TradingEngine:

    def __init__(self, portfolio_engine):

        self.engine = portfolio_engine

        self.cash = 10000000  # 1,000만원 시작
        self.positions = {}

    # -----------------------------------
    # 매수 신호 생성
    # -----------------------------------
    def generate_signals(self, stock_list, year="2024"):

        portfolio = self.engine.build_portfolio(
            stock_list,
            year=year,
            report_code="11011"
        )

        signals = []

        for code, data in portfolio.items():

            signals.append({
                "code": code,
                "action": "BUY",
                "weight": data["weight"],
                "score": data["score"]
            })

        return signals
    
    def execute_trades(self, signals, price_map):

        for s in signals:

            code = s["code"]
            price = price_map.get(code, 0)

            if price <= 0:
                continue

            allocation = self.cash * (s["weight"] / 100)

            qty = allocation // price

            cost = qty * price

            self.cash -= cost

            self.positions[code] = {
                "qty": qty,
                "avg_price": price,
                "value": cost
            }