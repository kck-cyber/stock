"""
Stock Panel

Morning Stock Assistant Pro
"""

import tkinter as tk
from tkinter import messagebox

from pathlib import Path

from morning_stock_assistant.shared.stock_resolver import StockResolver


class StockPanel(tk.Frame):

    def __init__(
        self,
        master,
        market_manager,
        watchlist_manager,
        on_stock_select=None,
    ):

        super().__init__(master)

        self.market = market_manager
        self.watchlist = watchlist_manager
        self.on_stock_select = on_stock_select
        self.resolver = StockResolver(Path.cwd())

        self.current_group = None

        # ----------------------------
        # 검색창
        # ----------------------------

        tk.Label(
            self,
            text="종목 검색"
        ).pack(anchor="w")

        self.keyword = tk.StringVar()

        self.search_entry = tk.Entry(
            self,
            textvariable=self.keyword
        )

        self.search_entry.pack(fill="x")
        self.search_entry.bind(
            "<KeyRelease>",
            self.search
        )

        # ----------------------------
        # 검색 결과
        # ----------------------------

        tk.Label(
            self,
            text="검색 결과"
        ).pack(anchor="w", pady=(8, 0))

        self.search_list = tk.Listbox(
            self,
            height=7,
            exportselection=False
        )

        self.search_list.pack(
            fill="both",
            expand=False
        )

        self.search_list.bind(
            "<Double-Button-1>",
            self.add_stock
        )

        # ----------------------------
        # 관심종목
        # ----------------------------

        tk.Label(
            self,
            text="관심종목"
        ).pack(anchor="w", pady=(10, 0))

        self.stock_list = tk.Listbox(
            self,
            exportselection=False
        )

        self.stock_list.pack(
            fill="both",
            expand=True
        )

        self.stock_list.bind(
            "<<ListboxSelect>>",
            self.stock_selected
        )

        tk.Button(
            self,
            text="삭제",
            command=self.remove_stock
        ).pack(fill="x")

    # ------------------------------------------------

    def set_group(self, group):

        self.current_group = group

        self.refresh()

    # ------------------------------------------------

    def refresh(self):

        self.stock_list.delete(0, tk.END)

        if not self.current_group:
            return

        stocks = self.watchlist.get_stocks(
            self.current_group
        )

        for stock in stocks:

            self.stock_list.insert(
                tk.END,
                f"{stock['name']} ({stock['code']})"
            )

    # ------------------------------------------------

    def search(self, event=None):

        keyword = self.keyword.get().strip()

        self.search_list.delete(0, tk.END)

        if not keyword:
            return

        results = []
        seen = set()
        resolved = self.resolver.resolve_keyword(keyword)

        if resolved:
            results.append(resolved)
            seen.add(resolved["code"])

        for stock in self.market.search(keyword):
            code = StockResolver.normalize_code(stock.get("code", ""))

            if code in seen:
                continue

            copied = dict(stock)
            copied["code"] = code
            results.append(copied)
            seen.add(code)

        for stock in results[:30]:

            self.search_list.insert(
                tk.END,
                f"{stock['name']} ({stock['code']})"
            )

    # ------------------------------------------------

    def add_stock(self, event=None):

        if not self.current_group:
            return

        sel = self.search_list.curselection()

        if not sel:
            return

        text = self.search_list.get(sel[0])

        code = text.split("(")[-1].replace(")", "")
        name = text.split("(")[0].strip()

        ok = self.watchlist.add_stock(
            self.current_group,
            {
                "code": code,
                "name": name
            }
        )

        if not ok:

            messagebox.showwarning(
                "중복",
                "이미 등록된 종목입니다."
            )

            return

        self.refresh()

    # ------------------------------------------------

    def remove_stock(self):

        if not self.current_group:
            return

        sel = self.stock_list.curselection()

        if not sel:
            return

        stock = self.watchlist.get_stocks(
            self.current_group
        )[sel[0]]

        self.watchlist.remove_stock(
            self.current_group,
            stock["code"]
        )

        self.refresh()

    # ------------------------------------------------

    def stock_selected(self, event=None):

        sel = self.stock_list.curselection()

        if not sel:
            return

        stock = self.watchlist.get_stocks(
            self.current_group
        )[sel[0]]

        if self.on_stock_select:

            self.on_stock_select(stock)
