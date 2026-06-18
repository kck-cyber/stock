from PySide6.QtWidgets import (
    QMainWindow,
    QLabel,
    QWidget,
    QVBoxLayout,
)


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Morning Stock Assistant Pro v0.2")

        self.resize(1200, 800)

        self.init_ui()

    def init_ui(self):

        central = QWidget()

        layout = QVBoxLayout()

        label = QLabel("Morning Stock Assistant Pro가 정상적으로 시작되었습니다.")

        layout.addWidget(label)

        central.setLayout(layout)

        self.setCentralWidget(central)

        self.statusBar().showMessage("Ready")