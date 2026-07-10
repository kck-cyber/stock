"""
Result Panel

Morning Stock Assistant Pro
"""

import tkinter as tk


class ResultPanel(tk.Frame):

    def __init__(self, master):

        super().__init__(master)

        tk.Label(
            self,
            text="AI 분석 결과",
            font=("맑은고딕", 11, "bold")
        ).pack(anchor="w")

        self.text = tk.Text(
            self,
            wrap="word",
            state="disabled"
        )

        self.text.pack(
            fill="both",
            expand=True
        )

    # --------------------------------------------------

    def clear(self):

        self.text.configure(state="normal")
        self.text.delete("1.0", tk.END)
        self.text.configure(state="disabled")

    # --------------------------------------------------

    def show(self, result):

        self.text.configure(state="normal")
        self.text.delete("1.0", tk.END)

        if result is None:

            self.text.insert(
                tk.END,
                "분석 결과가 없습니다."
            )

            self.text.configure(state="disabled")
            return

        lines = [

            f"종목명 : {result.name}",
            f"종목코드 : {result.code}",
            "",
            f"현재가 : {result.price:,}",
            f"등락률 : {result.change_rate:.2f} %",
            "",
            f"PER : {result.per:.2f}",
            f"PBR : {result.pbr:.2f}",
            "",
            f"ROE : {result.roe:.2f} %",
            f"부채비율 : {result.debt_ratio:.2f} %",
            f"순이익 : {result.net_income:,}",
            "",
            "==========================",
            "",
            f"Value Score     : {result.value:.1f}",
            f"Quality Score  : {result.quality:.1f}",

            f"Growth Score   : {result.growth:.1f}",
            f"Stability Score: {result.stability:.1f}",
            f"Dividend Score : {result.dividend:.1f}",

            f"Momentum Score : {result.momentum:.1f}",
            f"News Score     : {result.news:.1f}",

            "",
            "-----------------------------",

            f"TOTAL SCORE : {result.score:.1f}",
            f"SIGNAL      : {result.signal}",

            "",
            f"판정 : {result.signal}",
            "",
            "==========================",
            "",
            result.comment

        ]

        self.text.insert(
            tk.END,
            "\n".join(lines)
        )

        self.text.configure(state="disabled")