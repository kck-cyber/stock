from PySide6.QtCore import Signal

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
)


class SearchWidget(QWidget):

    search_requested = Signal(str)

    def __init__(self):

        super().__init__()

        self.build_ui()

    def build_ui(self):

        layout = QHBoxLayout(self)

        self.keyword = QLineEdit()

        self.keyword.setPlaceholderText(
            "종목명 또는 종목코드"
        )

        self.search_button = QPushButton("검색")

        layout.addWidget(self.keyword)

        layout.addWidget(self.search_button)

        self.search_button.clicked.connect(
            self.on_search
        )

        self.keyword.returnPressed.connect(
            self.on_search
        )

    def on_search(self):

        keyword = self.keyword.text().strip()

        if keyword:

            self.search_requested.emit(keyword)

    def clear(self):

        self.keyword.clear()