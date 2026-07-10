class ValuationEngine:

    def calculate(self, yahoo_data):

        eps = yahoo_data.get("eps")

        per = yahoo_data.get("per")

        current = yahoo_data.get("current_price")

        if not eps or not per:

            return None

        industry_per = 15

        fair_price = eps * industry_per

        target_price = fair_price * 1.1

        return {

            "fair_price": round(fair_price, 2),

            "target_price": round(target_price, 2),

            "current_price": current

        }