"""
News Panel

Morning Stock Assistant Pro
"""

import tkinter as tk
import webbrowser


class NewsPanel(tk.Frame):

    def __init__(self, master):

        super().__init__(master)

        self.stock = None

        tk.Label(
            self,
            text="뉴스 / 공시",
            font=("맑은고딕", 11, "bold")
        ).pack(anchor="w")

        self.listbox = tk.Listbox(
            self,
            height=12
        )

        self.listbox.pack(
            fill="both",
            expand=True
        )

        self.listbox.bind(
            "<Double-Button-1>",
            self.open_selected
        )

        button_frame = tk.Frame(self)
        button_frame.pack(fill="x")

        tk.Button(
            button_frame,
            text="네이버 뉴스",
            command=self.open_news
        ).pack(side="left", fill="x", expand=True)

        tk.Button(
            button_frame,
            text="DART 공시",
            command=self.open_dart
        ).pack(side="left", fill="x", expand=True)

        tk.Button(
            button_frame,
            text="TradingView",
            command=self.open_tradingview
        ).pack(side="left", fill="x", expand=True)

    # --------------------------------------------------

    def clear(self):

        self.stock = None

        self.listbox.delete(0, tk.END)

    # --------------------------------------------------

    def show(self, stock):

        self.stock = stock

        self.listbox.delete(0, tk.END)

        self.listbox.insert(
            tk.END,
            f"네이버 뉴스 - {stock['name']}"
        )

        self.listbox.insert(
            tk.END,
            f"DART 공시 - {stock['name']}"
        )

        self.listbox.insert(
            tk.END,
            f"TradingView - {stock['code']}"
        )

    # --------------------------------------------------

    def open_selected(self, event=None):

        if not self.stock:
            return

        sel = self.listbox.curselection()

        if not sel:
            return

        index = sel[0]

        if index == 0:
            self.open_news()

        elif index == 1:
            self.open_dart()

        else:
            self.open_tradingview()

    # --------------------------------------------------

    def open_news(self):

        if not self.stock:
            return

        keyword = self.stock["name"]

        url = (
            "https://search.naver.com/search.naver?"
            f"where=news&query={keyword}"
        )

        webbrowser.open(url)

    # --------------------------------------------------

    def open_dart(self):

        if not self.stock:
            return

        keyword = self.stock["name"]

        url = (
            "https://dart.fss.or.kr/dsab001/main.do?"
            f"autoSearch=true&textCrpNm={keyword}"
        )

        webbrowser.open(url)

    # --------------------------------------------------

    def open_tradingview(self):

        if not self.stock:
            return

        code = self.stock["code"]

        if code.isdigit():
            symbol = f"KRX:{code}"
        else:
            symbol = code.upper()

        url = f"https://www.tradingview.com/symbols/{symbol}/"

        webbrowser.open(url)