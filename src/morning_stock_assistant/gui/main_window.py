from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
)

from morning_stock_assistant.services.stock_service import StockService


class MainWindow(QWidget):

    def __init__(self, project_root):

        super().__init__()

        self.project_root = project_root

        self.service = StockService(project_root)

        self.setWindowTitle("Morning Stock Assistant Pro")

        self.resize(700, 500)

        self.build_ui()

    def build_ui(self):

        layout = QVBoxLayout()

        top = QHBoxLayout()

        self.keyword = QLineEdit()

        self.keyword.setPlaceholderText("종목명 또는 종목코드")

        self.search_button = QPushButton("검색")

        self.search_button.clicked.connect(self.search)

        top.addWidget(self.keyword)

        top.addWidget(self.search_button)

        layout.addLayout(top)

        self.result = QLabel()

        self.result.setText("검색 결과가 여기에 표시됩니다.")

        layout.addWidget(self.result)

        self.setLayout(layout)

    def search(self):

        keyword = self.keyword.text().strip()

        if not keyword:

            return

        data = self.service.search(keyword)

        if data is None:

            self.result.setText("종목을 찾을 수 없습니다.")

            return

        text = f"""
회사명 : {data.get("company_name")}

현재가 : {data.get("current_price")}

PER : {data.get("per")}

EPS : {data.get("eps")}

시가총액 : {data.get("market_cap")}

섹터 : {data.get("sector")}

업종 : {data.get("industry")}
"""

        self.result.setText(text)