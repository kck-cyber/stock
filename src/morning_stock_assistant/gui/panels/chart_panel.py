import tkinter as tk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


class ChartPanel(tk.Frame):

    def __init__(self, master):

        super().__init__(master)

        self.figure = Figure(
            figsize=(6, 4),
            dpi=100
        )

        self.ax = self.figure.add_subplot(111)

        self.canvas = FigureCanvasTkAgg(
            self.figure,
            master=self
        )

        self.canvas.get_tk_widget().pack(
            fill="both",
            expand=True
        )

    def clear(self):

        self.ax.clear()
        self.canvas.draw()

    def show(self, stock):

        self.ax.clear()

        history = stock.price_history

        if history is None or len(history) == 0:

            self.canvas.draw()
            return

        self.ax.plot(
            history.index,
            history["Close"],
            label="Close"
        )

        if "MA20" in history.columns:

            self.ax.plot(
                history.index,
                history["MA20"],
                label="MA20"
            )

        if "MA60" in history.columns:

            self.ax.plot(
                history.index,
                history["MA60"],
                label="MA60"
            )

        if "MA120" in history.columns:

            self.ax.plot(
                history.index,
                history["MA120"],
                label="MA120"
            )

        self.ax.legend()

        self.figure.tight_layout()

        self.canvas.draw()