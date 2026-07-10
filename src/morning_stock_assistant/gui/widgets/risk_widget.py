"""
Risk Widget

AI가 분석한 투자 리스크를 표시하는 위젯
"""

from PySide6.QtWidgets import (
    QGroupBox,
    QLabel,
    QTextEdit,
    QVBoxLayout,
)


class RiskWidget(QGroupBox):
    """
    투자 리스크 위젯
    """

    def __init__(self):

        super().__init__("리스크 요인")

        self.build_ui()

    # -------------------------------------------------

    def build_ui(self):

        layout = QVBoxLayout(self)

        title = QLabel("AI 분석 리스크")

        title.setStyleSheet("""

            font-size:16px;

            font-weight:bold;

        """)

        self.risks = QTextEdit()

        self.risks.setReadOnly(True)

        self.risks.setMinimumHeight(220)

        layout.addWidget(title)

        layout.addWidget(self.risks)

    # -------------------------------------------------

    def clear(self):

        self.risks.clear()

    # -------------------------------------------------

    def update(self, analysis: dict):

        if analysis is None:

            self.clear()

            return

        risks = analysis.get("risk_factors")

        if not risks:

            self.risks.setPlainText("-")

            return

        text = ""

        for risk in risks:

            text += f"⚠ {risk}\n\n"

        self.risks.setPlainText(text)