"""
Company Information Widget

회사 기본 정보를 표시하는 위젯
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QLabel,
    QVBoxLayout,
)


class CompanyWidget(QGroupBox):
    """
    회사 정보 위젯
    """

    def __init__(self):

        super().__init__("회사 정보")

        self.build_ui()

    def build_ui(self):

        layout = QVBoxLayout(self)

        frame = QFrame()

        grid = QGridLayout(frame)

        grid.setHorizontalSpacing(20)

        grid.setVerticalSpacing(10)

        # ===== 데이터 Label =====

        self.company_name = QLabel("-")

        self.stock_code = QLabel("-")

        self.market = QLabel("-")

        self.current_price = QLabel("-")

        self.market_cap = QLabel("-")

        self.per = QLabel("-")

        self.eps = QLabel("-")

        self.book_value = QLabel("-")

        self.sector = QLabel("-")

        self.industry = QLabel("-")

        # ===== Row 0 =====

        grid.addWidget(QLabel("회사명"), 0, 0)

        grid.addWidget(self.company_name, 0, 1)

        # ===== Row 1 =====

        grid.addWidget(QLabel("종목코드"), 1, 0)

        grid.addWidget(self.stock_code, 1, 1)

        # ===== Row 2 =====

        grid.addWidget(QLabel("시장"), 2, 0)

        grid.addWidget(self.market, 2, 1)

        # ===== Row 3 =====

        grid.addWidget(QLabel("현재가"), 3, 0)

        grid.addWidget(self.current_price, 3, 1)

        # ===== Row 4 =====

        grid.addWidget(QLabel("시가총액"), 4, 0)

        grid.addWidget(self.market_cap, 4, 1)

        # ===== Row 5 =====

        grid.addWidget(QLabel("PER"), 5, 0)

        grid.addWidget(self.per, 5, 1)

        # ===== Row 6 =====

        grid.addWidget(QLabel("EPS"), 6, 0)

        grid.addWidget(self.eps, 6, 1)

        # ===== Row 7 =====

        grid.addWidget(QLabel("BPS"), 7, 0)

        grid.addWidget(self.book_value, 7, 1)

        # ===== Row 8 =====

        grid.addWidget(QLabel("섹터"), 8, 0)

        grid.addWidget(self.sector, 8, 1)

        # ===== Row 9 =====

        grid.addWidget(QLabel("업종"), 9, 0)

        grid.addWidget(self.industry, 9, 1)

        layout.addWidget(frame)

    # ---------------------------------

    def clear(self):
        """
        데이터 초기화
        """

        labels = [

            self.company_name,

            self.stock_code,

            self.market,

            self.current_price,

            self.market_cap,

            self.per,

            self.eps,

            self.book_value,

            self.sector,

            self.industry,

        ]

        for label in labels:

            label.setText("-")

    # ---------------------------------

    def update(self, data: dict):
        """
        회사정보 업데이트
        """

        if data is None:

            self.clear()

            return

        self.company_name.setText(
            str(data.get("company_name", "-"))
        )

        self.stock_code.setText(
            str(data.get("stock_code", "-"))
        )

        self.market.setText(
            str(data.get("market", "-"))
        )

        current = data.get("current_price")

        if current:

            self.current_price.setText(
                f"{current:,.0f}"
            )

        else:

            self.current_price.setText("-")

        market_cap = data.get("market_cap")

        if market_cap:

            self.market_cap.setText(
                str(market_cap)
            )

        else:

            self.market_cap.setText("-")

        self.per.setText(
            str(data.get("per", "-"))
        )

        self.eps.setText(
            str(data.get("eps", "-"))
        )

        self.book_value.setText(
            str(data.get("book_value", "-"))
        )

        self.sector.setText(
            str(data.get("sector", "-"))
        )

        self.industry.setText(
            str(data.get("industry", "-"))
        )