"""
AI Analysis Widget

AI 분석 결과를 표시하는 위젯
"""

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QLabel,
    QVBoxLayout,
)


class AIWidget(QGroupBox):
    """
    AI 분석 위젯
    """

    def __init__(self):

        super().__init__("AI 분석")

        self.build_ui()

    # ---------------------------------------------

    def build_ui(self):

        layout = QVBoxLayout(self)

        frame = QFrame()

        grid = QGridLayout(frame)

        grid.setHorizontalSpacing(20)

        grid.setVerticalSpacing(10)

        self.score = QLabel("-")

        self.opinion = QLabel("-")

        self.confidence = QLabel("-")

        self.target_price = QLabel("-")

        self.fair_price = QLabel("-")

        self.summary = QLabel("-")

        self.summary.setWordWrap(True)

        # Row 0

        grid.addWidget(QLabel("AI 점수"), 0, 0)

        grid.addWidget(self.score, 0, 1)

        # Row 1

        grid.addWidget(QLabel("투자의견"), 1, 0)

        grid.addWidget(self.opinion, 1, 1)

        # Row 2

        grid.addWidget(QLabel("신뢰도"), 2, 0)

        grid.addWidget(self.confidence, 2, 1)

        # Row 3

        grid.addWidget(QLabel("적정가"), 3, 0)

        grid.addWidget(self.fair_price, 3, 1)

        # Row 4

        grid.addWidget(QLabel("목표가"), 4, 0)

        grid.addWidget(self.target_price, 4, 1)

        # Row 5

        grid.addWidget(QLabel("AI 요약"), 5, 0)

        grid.addWidget(self.summary, 5, 1)

        layout.addWidget(frame)

    # ---------------------------------------------

    def clear(self):

        self.score.setText("-")

        self.opinion.setText("-")

        self.confidence.setText("-")

        self.target_price.setText("-")

        self.fair_price.setText("-")

        self.summary.setText("-")

    # ---------------------------------------------

    def update(self, analysis: dict):

        if analysis is None:

            self.clear()

            return

        score = analysis.get("score")

        opinion = analysis.get("opinion")

        confidence = analysis.get("confidence")

        target = analysis.get("target_price")

        fair = analysis.get("fair_price")

        summary = analysis.get("summary")

        # -------------------------

        if score is not None:

            self.score.setText(f"{score}/100")

            if score >= 80:

                color = "green"

            elif score >= 60:

                color = "orange"

            else:

                color = "red"

            self.score.setStyleSheet(

                f"""

                font-size:18px;

                font-weight:bold;

                color:{color};

                """

            )

        else:

            self.score.setText("-")

        # -------------------------

        if opinion:

            self.opinion.setText(opinion)

        else:

            self.opinion.setText("-")

        # -------------------------

        if confidence is not None:

            self.confidence.setText(f"{confidence}%")

        else:

            self.confidence.setText("-")

        # -------------------------

        if fair:

            self.fair_price.setText(

                f"{fair:,.0f}원"

            )

        else:

            self.fair_price.setText("-")

        # -------------------------

        if target:

            self.target_price.setText(

                f"{target:,.0f}원"

            )

        else:

            self.target_price.setText("-")

        # -------------------------

        if summary:

            self.summary.setText(summary)

        else:

            self.summary.setText("-")