"""
News Widget

최근 뉴스를 표시하는 위젯
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QGroupBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QLabel,
)


class NewsWidget(QGroupBox):
    """
    최근 뉴스 표시 위젯
    """

    def __init__(self):

        super().__init__("최근 뉴스")

        self.build_ui()

    # --------------------------------------------------

    def build_ui(self):

        layout = QVBoxLayout(self)

        title = QLabel("최근 뉴스")

        title.setStyleSheet("""

            font-size:16px;

            font-weight:bold;

        """)

        layout.addWidget(title)

        self.table = QTableWidget()

        self.table.setColumnCount(5)

        self.table.setHorizontalHeaderLabels(

            [

                "날짜",

                "감성",

                "제목",

                "언론사",

                "URL",

            ]

        )

        self.table.setColumnHidden(4, True)

        self.table.verticalHeader().setVisible(False)

        self.table.setAlternatingRowColors(True)

        self.table.setSelectionBehavior(

            QTableWidget.SelectionBehavior.SelectRows

        )

        self.table.setEditTriggers(

            QTableWidget.EditTrigger.NoEditTriggers

        )

        self.table.setColumnWidth(0, 100)

        self.table.setColumnWidth(1, 70)

        self.table.setColumnWidth(2, 520)

        self.table.setColumnWidth(3, 130)

        layout.addWidget(self.table)

    # --------------------------------------------------

    def clear(self):

        self.table.setRowCount(0)

    # --------------------------------------------------

    def update(self, news_list):

        self.clear()

        if not news_list:

            return

        self.table.setRowCount(len(news_list))

        for row, news in enumerate(news_list):

            date = str(news.get("date", ""))

            sentiment = str(news.get("sentiment", "중립"))

            title = str(news.get("title", ""))

            press = str(news.get("press", ""))

            url = str(news.get("url", ""))

            date_item = QTableWidgetItem(date)

            sentiment_item = QTableWidgetItem(sentiment)

            title_item = QTableWidgetItem(title)

            press_item = QTableWidgetItem(press)

            url_item = QTableWidgetItem(url)

            sentiment_item.setTextAlignment(

                Qt.AlignmentFlag.AlignCenter

            )

            if sentiment == "긍정":

                sentiment_item.setForeground(

                    QColor(0, 150, 0)

                )

            elif sentiment == "부정":

                sentiment_item.setForeground(

                    QColor(200, 0, 0)

                )

            else:

                sentiment_item.setForeground(

                    QColor(120, 120, 120)

                )

            self.table.setItem(row, 0, date_item)

            self.table.setItem(row, 1, sentiment_item)

            self.table.setItem(row, 2, title_item)

            self.table.setItem(row, 3, press_item)

            self.table.setItem(row, 4, url_item)

        self.table.resizeRowsToContents()

    # --------------------------------------------------

    def selected_news(self):

        row = self.table.currentRow()

        if row < 0:

            return None

        return {

            "date": self.table.item(row, 0).text(),

            "sentiment": self.table.item(row, 1).text(),

            "title": self.table.item(row, 2).text(),

            "press": self.table.item(row, 3).text(),

            "url": self.table.item(row, 4).text(),

        }