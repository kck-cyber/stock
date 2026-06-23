"""
Main Window

Morning Stock Assistant Pro
"""

"""
Main Window (GUI Upgrade)

- 종목명 검색 + 자동완성
- 종목코드 자동 입력
- 분석 기능 유지
"""

import tkinter as tk
from tkinter import messagebox
from morning_stock_assistant.ai.analyzer import StockAnalyzer


class MainWindow:
    def __init__(self, stock_service):
        self.service = stock_service

        # KRX 데이터 로드
        self.krx = self.service.krx
        self.krx.load()

        self.root = tk.Tk()
        self.root.title("Morning Stock Assistant Pro")
        self.root.geometry("650x500")

        self._build_ui()

    # --------------------------------------------------
    # UI 구성
    # --------------------------------------------------
    def _build_ui(self):

        # ----------------------------
        # 종목 검색 입력
        # ----------------------------
        tk.Label(self.root, text="종목 검색 (이름 입력)").pack()

        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(self.root, textvariable=self.search_var)
        self.search_entry.pack()
        self.search_entry.bind("<KeyRelease>", self.on_search)

        # 자동완성 리스트
        self.listbox = tk.Listbox(self.root, height=6)
        self.listbox.pack()
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        # 선택된 종목코드 표시
        tk.Label(self.root, text="종목코드").pack()

        self.code_entry = tk.Entry(self.root)
        self.code_entry.pack()

        # 연도
        tk.Label(self.root, text="연도 (예: 2023)").pack()
        self.year_entry = tk.Entry(self.root)
        self.year_entry.pack()

        # 보고서 코드
        tk.Label(self.root, text="보고서 코드").pack()
        self.report_entry = tk.Entry(self.root)
        self.report_entry.insert(0, "11011")
        self.report_entry.pack()

        # 분석 버튼
        tk.Button(
            self.root,
            text="분석하기",
            command=self.analyze_stock
        ).pack(pady=10)

        # 결과 출력
        self.result_text = tk.Text(self.root, height=12)
        self.result_text.pack(fill="both", expand=True)

    # --------------------------------------------------
    # 검색 (자동완성)
    # --------------------------------------------------
    def on_search(self, event):
        keyword = self.search_var.get().strip()

        self.listbox.delete(0, tk.END)

        if not keyword:
            return

        count = 0

        for code, info in self.krx.data.items():
            name = info.get("name", "")

            if keyword in name:
                self.listbox.insert(tk.END, f"{name} ({code})")
                count += 1

            if count >= 10:
                break

    # --------------------------------------------------
    # 리스트 선택
    # --------------------------------------------------
    def on_select(self, event):
        selection = self.listbox.curselection()
        if not selection:
            return

        value = self.listbox.get(selection[0])

        # "삼성전자 (005930)" → code 추출
        code = value.split("(")[-1].replace(")", "")

        self.code_entry.delete(0, tk.END)
        self.code_entry.insert(0, code)

        # 검색창도 이름으로 정리
        name = value.split("(")[0].strip()
        self.search_var.set(name)

    # --------------------------------------------------
    # 분석 실행
    # --------------------------------------------------
    def analyze_stock(self):
        code = self.code_entry.get().strip()
        year = self.year_entry.get().strip()
        report = self.report_entry.get().strip()

        if not code or not year:
            messagebox.showerror("오류", "종목과 연도를 입력하세요")
            return

        result = self.service.analyze(code, year, report)

        if not result:
            messagebox.showerror("오류", "데이터 없음")
            return

        self.show_result(result)

    # --------------------------------------------------
    # 결과 출력
    # --------------------------------------------------
    def show_result(self, result):
        self.result_text.delete("1.0", tk.END)

        text = f"""
종목명: {result.name}
종목코드: {result.code}

📊 점수: {result.score}
📈 판단: {result.signal}

ROE: {result.roe:.2f}%
부채비율: {result.debt_ratio:.2f}%
순이익: {result.net_income:,}

📌 분석:
{result.comment}
"""

        self.result_text.insert(tk.END, text)

    # --------------------------------------------------
    # 실행
    # --------------------------------------------------
    def run(self):
        self.root.mainloop()





