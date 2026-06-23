"""
Investment Widget

AI가 분석한 투자 포인트를 표시하는 위젯
"""

from PySide6.QtWidgets import (
    QGroupBox,
    QLabel,
    QTextEdit,
    QVBoxLayout,
)


class InvestmentWidget(QGroupBox):
    """
    투자 포인트 위젯
    """

    def __init__(self):

        super().__init__("투자 포인트")

        self.build_ui()

    # -------------------------------------------------

    def build_ui(self):

        layout = QVBoxLayout(self)

        title = QLabel("AI 추천 투자 포인트")

        title.setStyleSheet("""

            font-size:16px;

            font-weight:bold;

        """)

        self.points = QTextEdit()

        self.points.setReadOnly(True)

        self.points.setMinimumHeight(220)

        layout.addWidget(title)

        layout.addWidget(self.points)

    # -------------------------------------------------

    def clear(self):

        self.points.clear()

    # -------------------------------------------------

    def update(self, analysis: dict):

        if analysis is None:

            self.clear()

            return

        points = analysis.get("investment_points")

        if not points:

            self.points.setPlainText("-")

            return

        text = ""

        for point in points:

            text += f"• {point}\n\n"

        self.points.setPlainText(text)