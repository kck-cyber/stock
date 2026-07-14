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
import matplotlib.dates as mdates
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import messagebox
from tkinter import simpledialog
from tkinter import filedialog

from pathlib import Path
from datetime import datetime, timedelta
from email.message import EmailMessage
import json
import logging
import smtplib
import ssl
import threading
import webbrowser
from types import SimpleNamespace

from tkinter import ttk

from morning_stock_assistant import __version__ as APP_VERSION
from morning_stock_assistant.services.search_service import SearchService
from morning_stock_assistant.shared.alert_engine import AlertEngine, AlertRules
from morning_stock_assistant.shared.analysis_bridge import SharedAnalysisBridge
from morning_stock_assistant.shared.remote_client import RemoteAnalysisClient
from morning_stock_assistant.shared.stock_resolver import StockResolver
from morning_stock_assistant.gui.panels.chart_panel import ChartPanel
from morning_stock_assistant.config import DEFAULT_ANALYSIS_SERVER_URL, REPORT_DIR


logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)


def safe_number(value, default=0):

    if value is None:
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def format_price(price, currency="KRW"):

    if currency == "USD":
        return f"${price:,.2f}"

    return f"{price:,.0f}원"


class MainWindow:
    def __init__(self, stock_service, analyzer):
        self.service = stock_service
        self.analyzer = analyzer
        self.stock_resolver = StockResolver(
            Path.cwd(),
            search_service_factory=self.create_search_service
        )

        # KRX 데이터 로드
        self.krx = self.service.krx

        if self.krx:
            self.krx.load()

        # 관심종목 그룹

        self.root = tk.Tk()
        self.root.title(f"Morning Stock Assistant Pro v{APP_VERSION}")
        self.root.geometry("1320x800")
        self.colors = {
            "bg": "#f5f7fb",
            "panel": "#ffffff",
            "panel_alt": "#eef2f7",
            "text": "#172033",
            "muted": "#64748b",
            "line": "#d8dee9",
            "accent": "#2563eb",
            "accent_dark": "#1d4ed8",
            "good": "#15803d",
            "warn": "#b45309",
            "bad": "#b91c1c",
            "hold": "#0369a1",
        }
        self.apply_theme()

        self.groups = {}

        self.current_group = None
        self.current_stock = None
        self.chart_period_var = tk.StringVar(value="1d")
        self.chart_interval_var = tk.StringVar(value="5s")
        self.chart_label_var = tk.StringVar(value="일일")
        self.chart_summary_var = tk.StringVar(value="종목을 선택하면 차트가 표시됩니다.")
        self.chart_show_ma_var = tk.BooleanVar(value=False)
        self.chart_live_samples = {}
        self.chart_live_job = None
        self.chart_motion_cid = None
        self.chart_event_canvas = None
        self.chart_hover_data = []
        self.chart_hover_annotation = None
        self.chart_hover_line = None
        self.chart_hover_line = None
        self.chart_hover_currency = "KRW"
        self.weight_preset_var = tk.StringVar(value="균형형")
        self.status_var = tk.StringVar(value="준비됨")
        self.portfolio_capital_var = tk.StringVar(value="10000000")
        self.holding_code_var = tk.StringVar(value="")
        self.holding_qty_var = tk.StringVar(value="")
        self.holding_avg_price_var = tk.StringVar(value="")
        self.alert_enabled_var = tk.BooleanVar(value=False)
        self.alert_popup_var = tk.BooleanVar(value=True)
        self.alert_email_var = tk.BooleanVar(value=False)
        self.alert_threshold_var = tk.StringVar(value="75")
        self.scheduled_email_var = tk.BooleanVar(value=False)
        self.scheduled_time_var = tk.StringVar(value="08:30")
        self.auto_refresh_interval_var = tk.StringVar(value="20")
        self.alert_recipient_var = tk.StringVar(value="")
        self.smtp_host_var = tk.StringVar(value="smtp.gmail.com")
        self.smtp_port_var = tk.StringVar(value="587")
        self.smtp_user_var = tk.StringVar(value="")
        self.smtp_password_var = tk.StringVar(value="")
        self.smtp_tls_var = tk.BooleanVar(value=True)
        self.api_base_url_var = tk.StringVar(value=DEFAULT_ANALYSIS_SERVER_URL)
        self.us_price_krw_var = tk.BooleanVar(value=False)
        self.usd_krw_rate = None
        self.usd_krw_rate_time = None

        self.current_news = []
        self.current_result = None
        self.display_stocks = []
        self.holdings = {}
        self.alert_history = set()
        self.compare_analysis_running = False
        self.portfolio_analysis_running = False
        self.stock_analysis_running = False
        self.stock_analysis_code = None
        self.last_scheduled_email_date = None

        self.watchlist_file = (
            Path(__file__).resolve().parents[3]
            / "storage"
            / "watchlist.json"
        )
        self.alert_settings_file = (
            self.watchlist_file.parent
            / "alert_settings.json"
        )
        self.holdings_file = (
            self.watchlist_file.parent
            / "holdings.json"
        )

        self.watchlist_file.parent.mkdir(exist_ok=True)
        self.load_alert_settings()
        self.load_holdings()

        self._build_ui()

        self._rebuild_content_tabs()

        self.load_groups()

        self.start_server_prewarm()
        self.auto_refresh()
        self.check_scheduled_email()

    # --------------------------------------------------
    # UI 구성
    # --------------------------------------------------
    def apply_theme(self):

        colors = self.colors
        self.root.configure(bg=colors["bg"])
        self.root.option_add("*Font", ("맑은 고딕", 10))
        self.root.option_add("*Background", colors["bg"])
        self.root.option_add("*Foreground", colors["text"])
        self.root.option_add("*Entry.Background", colors["panel"])
        self.root.option_add("*Listbox.Background", colors["panel"])
        self.root.option_add("*Text.Background", colors["panel"])

        style = ttk.Style(self.root)

        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "TNotebook",
            background=colors["bg"],
            borderwidth=0
        )
        style.configure(
            "TNotebook.Tab",
            padding=(14, 7),
            background=colors["panel_alt"],
            foreground=colors["muted"],
            width=11,
            borderwidth=1
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", colors["panel"])],
            foreground=[("selected", colors["accent_dark"])],
            padding=[("selected", (14, 7))],
            expand=[("selected", (0, 0, 0, 0))]
        )
        style.configure(
            "Treeview",
            background=colors["panel"],
            fieldbackground=colors["panel"],
            foreground=colors["text"],
            rowheight=26,
            bordercolor=colors["line"],
            borderwidth=1
        )
        style.configure(
            "Treeview.Heading",
            background=colors["panel_alt"],
            foreground=colors["text"],
            font=("맑은 고딕", 10, "bold")
        )
        style.map(
            "Treeview",
            background=[("selected", colors["accent"])],
            foreground=[("selected", "#ffffff")]
        )

    def style_widget_tree(self, widget=None):

        widget = widget or self.root
        colors = self.colors

        for child in widget.winfo_children():
            try:
                if isinstance(child, (tk.Frame, tk.LabelFrame)):
                    child.configure(bg=colors["bg"])
                elif isinstance(child, tk.Label):
                    child.configure(
                        bg=colors["bg"],
                        fg=colors["text"]
                    )
                elif isinstance(child, tk.Button):
                    child.configure(
                        bg=colors["accent"],
                        fg="#ffffff",
                        activebackground=colors["accent_dark"],
                        activeforeground="#ffffff",
                        relief="flat",
                        padx=8,
                        pady=4,
                        cursor="hand2"
                    )
                elif isinstance(child, tk.Listbox):
                    child.configure(
                        bg=colors["panel"],
                        fg=colors["text"],
                        selectbackground=colors["accent"],
                        selectforeground="#ffffff",
                        relief="solid",
                        borderwidth=1,
                        highlightthickness=1,
                        highlightbackground=colors["line"]
                    )
                elif isinstance(child, tk.Text):
                    child.configure(
                        bg=colors["panel"],
                        fg=colors["text"],
                        insertbackground=colors["text"],
                        relief="solid",
                        borderwidth=1,
                        highlightthickness=1,
                        highlightbackground=colors["line"]
                    )
                elif isinstance(child, tk.Entry):
                    child.configure(
                        bg=colors["panel"],
                        fg=colors["text"],
                        insertbackground=colors["text"],
                        relief="solid",
                        borderwidth=1,
                        highlightthickness=1,
                        highlightbackground=colors["line"]
                    )
            except tk.TclError:
                pass

            self.style_widget_tree(child)

    def configure_tree_tags(self, tree):

        colors = self.colors
        tree.tag_configure(
            "buy",
            foreground=colors["good"]
        )
        tree.tag_configure(
            "hold",
            foreground=colors["hold"]
        )
        tree.tag_configure(
            "reduce",
            foreground=colors["warn"]
        )
        tree.tag_configure(
            "sell",
            foreground=colors["bad"]
        )
        tree.tag_configure(
            "good",
            foreground=colors["good"]
        )
        tree.tag_configure(
            "bad",
            foreground=colors["bad"]
        )
        tree.tag_configure(
            "neutral",
            foreground=colors["muted"]
        )

    def signal_tag(self, signal):

        if "매수" in signal:
            return "buy"

        if "보유" in signal:
            return "hold"

        if "비중 축소" in signal:
            return "reduce"

        if "매도" in signal:
            return "sell"

        return ""

    def _build_ui(self):

        # ===========================
        # 메인 프레임
        # ===========================

        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True)

        # 좌측
        left_frame = tk.Frame(main_frame, width=180)
        left_frame.pack(side="left", fill="y", padx=5, pady=5)

        tk.Label(
            left_frame,
            text="관심종목 그룹",
            font=("맑은고딕", 11, "bold")
        ).pack()

        self.group_list = tk.Listbox(
            left_frame,
            height=15,
            width=18
        )

        self.group_list.pack(fill="y", expand=True)

        self.group_list.bind(
            "<<ListboxSelect>>",
            self.on_group_select
        )

        tk.Button(
            left_frame,
            text="+ 그룹",
            command=self.add_group
        ).pack(fill="x")

        tk.Button(
            left_frame,
            text="이름 변경",
            command=self.rename_group
        ).pack(fill="x")

        tk.Button(
            left_frame,
            text="삭제",
            command=self.delete_group
        ).pack(fill="x")

        tk.Button(
            left_frame,
            text="데이터 백업",
            command=self.export_user_data
        ).pack(fill="x", pady=(8, 0))

        tk.Button(
            left_frame,
            text="데이터 불러오기",
            command=self.import_user_data
        ).pack(fill="x")

        # 가운데
        center_frame = tk.Frame(main_frame, width=220)
        center_frame.pack(side="left", fill="y", padx=5, pady=5)

        # 오른쪽
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        self.right_frame = right_frame


        # ----------------------------
        # 종목 검색 입력
        # ----------------------------
        tk.Label(center_frame, text="종목 검색 (이름 입력)").pack()

        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(
            center_frame,
            textvariable=self.search_var
        )

        self.search_entry.pack(fill="x", pady=3)
        self.search_entry.bind("<KeyRelease>", self.on_search)
        self.search_entry.bind("<Return>", self.add_first_search_result)
        self.search_entry.bind("<Down>", self.move_to_search_list)

        # 자동완성 리스트
        self.listbox = tk.Listbox(center_frame, height=6, width=35)
        tk.Label(
            center_frame,
            text="관심종목"
        ).pack(pady=(10, 0))

        self.stock_list = tk.Listbox(
            center_frame,
            height=15,
            exportselection=False
        )

        self.stock_list.pack(fill="both", expand=True)
        tk.Button(
        center_frame,
        text="선택 종목 삭제",
        command=self.delete_stock).pack(fill="x", pady=5)

        tk.Button(center_frame, text="🔄 그룹 새로고침", command=self.refresh_group).pack(fill="x")

        tk.Label(
            center_frame,
            text="가중치 프리셋"
        ).pack(anchor="w", pady=(8, 0))

        self.weight_preset_combo = ttk.Combobox(
            center_frame,
            textvariable=self.weight_preset_var,
            values=self.analyzer.factor.preset_names(),
            state="readonly"
        )
        self.weight_preset_combo.pack(fill="x", pady=(2, 6))
        self.weight_preset_combo.bind(
            "<<ComboboxSelected>>",
            self.on_weight_preset_change
        )

        tk.Checkbutton(
            center_frame,
            text="미국 주식 원화 표시",
            variable=self.us_price_krw_var,
            command=self.on_currency_display_change,
            anchor="w"
        ).pack(fill="x", pady=(0, 2))

        self.usd_krw_label = tk.Label(
            center_frame,
            text="환율: 자동",
            fg=self.colors["muted"]
        )
        self.usd_krw_label.pack(anchor="w")
        
        self.stock_list.bind(
            "<<ListboxSelect>>",
            self.on_stock_select
        )
        self.stock_list.bind(
            "<Delete>",
            self.delete_stock
        )
        self.listbox.pack()
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        tk.Button(
            center_frame,
            text="현재 그룹에 추가",
            command=self.add_stock_to_group
        ).pack(fill="x", pady=5)
        
        self.listbox.bind("<Return>", self.on_select)

        self.notebook = ttk.Notebook(right_frame)

        self.notebook.pack(fill="both", expand=True)

        self.analysis_tab = tk.Frame(self.notebook)

        self.notebook.add(self.analysis_tab, text="분석")

        self.result_text = tk.Text(
            self.analysis_tab,
            wrap="word"
        )

        self.result_text.pack(fill="both", expand=True)

        self.chart_tab = tk.Frame(self.notebook)

        self.notebook.add(
            self.chart_tab,
            text="차트"
        )

        self.figure = Figure(figsize=(6,3), dpi=100)

        self.ax = self.figure.add_subplot(111)

        self.canvas = FigureCanvasTkAgg(
            self.figure,
            master=self.chart_tab
        )

        self.canvas.get_tk_widget().pack(
            fill="both",
            expand=True
        )

        self.chart_tab = tk.Frame(self.notebook)

        self.notebook.add(
            self.chart_tab,
            text="차트"
        )

        tk.Label(
            right_frame,
            text="📰 최신 뉴스",
            font=("맑은고딕",11,"bold")
        ).pack(anchor="w")

        self.news_list = tk.Listbox(
            right_frame,
            height=8
        )

        self.news_list.pack(
            fill="both",
            expand=False
        )

        self.news_tab = tk.Frame(self.notebook)

        self.notebook.add(
            self.news_tab,
            text="뉴스"
        )

        self.finance_tab = tk.Frame(self.notebook)

        self.notebook.add(
            self.finance_tab,
            text="재무"
        )

        self.status_label = tk.Label(
            self.root,
            textvariable=self.status_var,
            anchor="w",
            bg=self.colors["panel_alt"],
            fg=self.colors["muted"],
            padx=8,
            pady=4
        )
        self.status_label.pack(fill="x", padx=5, pady=(0, 3))

    def _rebuild_content_tabs(self):

        for widget in self.right_frame.winfo_children():
            widget.destroy()

        self.notebook = ttk.Notebook(self.right_frame)
        self.notebook.pack(fill="both", expand=True)

        self.dashboard_tab = tk.Frame(self.notebook)
        self.briefing_tab = tk.Frame(self.notebook)
        self.analysis_tab = tk.Frame(self.notebook)
        self.chart_tab = tk.Frame(self.notebook)
        self.news_tab = tk.Frame(self.notebook)
        self.finance_tab = tk.Frame(self.notebook)
        self.scenario_tab = tk.Frame(self.notebook)
        self.compare_tab = tk.Frame(self.notebook)
        self.portfolio_tab = tk.Frame(self.notebook)
        self.alert_tab = tk.Frame(self.notebook)

        self.notebook.add(self.dashboard_tab, text="대시보드")
        self.notebook.add(self.briefing_tab, text="오늘 브리핑")
        self.notebook.add(self.analysis_tab, text="분석")
        self.notebook.add(self.chart_tab, text="차트")
        self.notebook.add(self.news_tab, text="뉴스")
        self.notebook.add(self.finance_tab, text="재무")
        self.notebook.add(self.scenario_tab, text="시나리오")
        self.notebook.add(self.compare_tab, text="비교")
        self.notebook.add(self.portfolio_tab, text="포트폴리오")
        self.notebook.add(self.alert_tab, text="알림")

        self._build_dashboard_tab()
        self._build_briefing_tab()

        analysis_toolbar = tk.Frame(self.analysis_tab)
        analysis_toolbar.pack(fill="x", pady=(0, 4))

        tk.Button(
            analysis_toolbar,
            text="리포트 저장",
            command=self.save_current_report
        ).pack(side="left")

        self.result_text = tk.Text(
            self.analysis_tab,
            wrap="word"
        )
        self.result_text.pack(fill="both", expand=True)

        chart_toolbar = tk.Frame(self.chart_tab)
        chart_toolbar.pack(fill="x", pady=(0, 4))

        for label, period, interval in (
            ("일일", "1d", "5s"),
            ("일주", "5d", "5m"),
            ("한달", "1mo", "30m"),
            ("3개월", "3mo", "1d"),
            ("6개월", "6mo", "1d"),
            ("1년", "1y", "1d"),
        ):
            tk.Button(
                chart_toolbar,
                text=label,
                command=(
                    lambda p=period, i=interval, l=label:
                    self.set_chart_period(p, i, l)
                )
            ).pack(side="left", padx=(0, 3))

        tk.Checkbutton(
            chart_toolbar,
            text="이동평균",
            variable=self.chart_show_ma_var,
            command=self.draw_chart,
            anchor="w"
        ).pack(side="left", padx=(8, 0))

        tk.Label(
            self.chart_tab,
            textvariable=self.chart_summary_var,
            anchor="w",
            fg=self.colors["muted"],
            font=("맑은고딕", 10, "bold")
        ).pack(fill="x", pady=(0, 2))

        self.figure = Figure(figsize=(6, 3.4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(
            self.figure,
            master=self.chart_tab
        )
        self.canvas.get_tk_widget().pack(
            fill="both",
            expand=True
        )
        self.setup_chart_interaction()

        tk.Label(
            self.news_tab,
            text="최신 뉴스",
            font=("맑은고딕", 11, "bold")
        ).pack(anchor="w")

        self.news_columns = ("date", "impact", "score", "event", "title")
        self.news_list = ttk.Treeview(
            self.news_tab,
            columns=self.news_columns,
            show="headings"
        )
        self.configure_tree_tags(self.news_list)
        news_headings = {
            "date": "날짜",
            "impact": "호재/악재",
            "score": "점수",
            "event": "유형",
            "title": "뉴스 제목",
        }
        news_widths = {
            "date": 125,
            "impact": 90,
            "score": 55,
            "event": 100,
            "title": 520,
        }

        for column in self.news_columns:
            self.news_list.heading(column, text=news_headings[column])
            self.news_list.column(
                column,
                width=news_widths[column],
                anchor="center" if column != "title" else "w",
                stretch=(column == "title")
            )

        news_y_scroll = ttk.Scrollbar(
            self.news_tab,
            orient="vertical",
            command=self.news_list.yview
        )
        news_x_scroll = ttk.Scrollbar(
            self.news_tab,
            orient="horizontal",
            command=self.news_list.xview
        )
        self.news_list.configure(
            yscrollcommand=news_y_scroll.set,
            xscrollcommand=news_x_scroll.set
        )
        self.news_list.pack(side="left", fill="both", expand=True)
        news_y_scroll.pack(side="right", fill="y")
        news_x_scroll.pack(side="bottom", fill="x")
        self.news_list.bind("<Double-Button-1>", self.open_selected_news)
        self.bind_horizontal_tree_drag(self.news_list)

        self.finance_text = tk.Text(
            self.finance_tab,
            wrap="word"
        )
        self.finance_text.pack(fill="both", expand=True)

        self.scenario_text = tk.Text(
            self.scenario_tab,
            wrap="word"
        )
        self.scenario_text.pack(fill="both", expand=True)

        compare_toolbar = tk.Frame(self.compare_tab)
        compare_toolbar.pack(fill="x", pady=(0, 4))

        tk.Button(
            compare_toolbar,
            text="비교표 새로고침",
            command=self.refresh_comparison_table
        ).pack(side="left")

        self.compare_columns = (
            "name",
            "code",
            "asset_type",
            "score",
            "quant_news_avg",
            "signal",
            "price",
            "change",
            "per",
            "pbr",
            "pcr",
            "psr",
            "roe",
            "roic",
            "fcf_yield",
            "debt",
            "growth",
            "short_ratio",
            "foreign_net_buy",
            "institution_net_buy",
        )
        self.compare_tree = ttk.Treeview(
            self.compare_tab,
            columns=self.compare_columns,
            show="headings"
        )
        self.configure_tree_tags(self.compare_tree)

        headings = {
            "name": "종목명",
            "code": "코드",
            "asset_type": "구분",
            "score": "점수",
            "quant_news_avg": "평균",
            "signal": "판정",
            "price": "현재가",
            "change": "등락률",
            "per": "PER",
            "pbr": "PBR",
            "pcr": "PCR",
            "psr": "PSR",
            "roe": "ROE",
            "roic": "ROIC",
            "fcf_yield": "FCF Y",
            "debt": "부채비율",
            "growth": "성장",
            "short_ratio": "공매도",
            "foreign_net_buy": "외국인",
            "institution_net_buy": "기관",
        }
        widths = {
            "name": 130,
            "code": 80,
            "asset_type": 65,
            "score": 70,
            "quant_news_avg": 70,
            "signal": 110,
            "price": 95,
            "change": 75,
            "per": 70,
            "pbr": 70,
            "pcr": 70,
            "psr": 70,
            "roe": 70,
            "roic": 70,
            "fcf_yield": 75,
            "debt": 80,
            "growth": 70,
            "short_ratio": 75,
            "foreign_net_buy": 110,
            "institution_net_buy": 110,
        }

        for column in self.compare_columns:
            self.compare_tree.heading(column, text=headings[column])
            self.compare_tree.column(
                column,
                width=widths[column],
                anchor="center",
                stretch=False
            )

        y_scroll = ttk.Scrollbar(
            self.compare_tab,
            orient="vertical",
            command=self.compare_tree.yview
        )
        x_scroll = ttk.Scrollbar(
            self.compare_tab,
            orient="horizontal",
            command=self.compare_tree.xview
        )
        self.compare_tree.configure(
            yscrollcommand=y_scroll.set,
            xscrollcommand=x_scroll.set
        )
        self.compare_tree.pack(
            side="left",
            fill="both",
            expand=True
        )
        y_scroll.pack(side="right", fill="y")
        x_scroll.pack(side="bottom", fill="x")
        self.compare_tree.bind(
            "<Double-Button-1>",
            self.on_compare_select
        )
        self.bind_horizontal_tree_drag(self.compare_tree)

        portfolio_toolbar = tk.Frame(self.portfolio_tab)
        portfolio_toolbar.pack(fill="x", pady=(0, 4))

        tk.Label(
            portfolio_toolbar,
            text="투자금"
        ).pack(side="left")

        tk.Entry(
            portfolio_toolbar,
            textvariable=self.portfolio_capital_var,
            width=14
        ).pack(side="left", padx=(4, 8))

        tk.Button(
            portfolio_toolbar,
            text="포트폴리오 생성",
            command=self.refresh_portfolio_table
        ).pack(side="left")

        holding_toolbar = tk.Frame(self.portfolio_tab)
        holding_toolbar.pack(fill="x", pady=(0, 4))

        tk.Label(holding_toolbar, text="코드").pack(side="left")
        tk.Entry(
            holding_toolbar,
            textvariable=self.holding_code_var,
            width=10
        ).pack(side="left", padx=(4, 8))

        tk.Label(holding_toolbar, text="보유수량").pack(side="left")
        tk.Entry(
            holding_toolbar,
            textvariable=self.holding_qty_var,
            width=10
        ).pack(side="left", padx=(4, 8))

        tk.Label(holding_toolbar, text="평균가").pack(side="left")
        tk.Entry(
            holding_toolbar,
            textvariable=self.holding_avg_price_var,
            width=12
        ).pack(side="left", padx=(4, 8))

        tk.Button(
            holding_toolbar,
            text="보유 저장",
            command=self.save_holding
        ).pack(side="left", padx=(0, 4))

        tk.Button(
            holding_toolbar,
            text="보유 삭제",
            command=self.delete_holding
        ).pack(side="left")

        self.portfolio_summary_var = tk.StringVar(
            value="관심종목 그룹을 선택한 뒤 포트폴리오를 생성하세요."
        )
        tk.Label(
            self.portfolio_tab,
            textvariable=self.portfolio_summary_var,
            anchor="w",
            justify="left"
        ).pack(fill="x", pady=(0, 4))
        tk.Label(
            self.portfolio_tab,
            text="평균가 오른쪽: 손익률, 평가금액, 비중차이, 보유피드백, 핵심근거",
            anchor="w",
            fg=self.colors["muted"]
        ).pack(fill="x", pady=(0, 4))

        self.portfolio_columns = (
            "name",
            "code",
            "score",
            "signal",
            "weight",
            "amount",
            "price",
            "shares",
            "holding_qty",
            "avg_price",
            "pnl",
            "market_value",
            "gap",
            "feedback",
            "reason",
        )
        self.portfolio_tree = ttk.Treeview(
            self.portfolio_tab,
            columns=self.portfolio_columns,
            show="headings"
        )
        self.configure_tree_tags(self.portfolio_tree)
        portfolio_headings = {
            "name": "종목명",
            "code": "코드",
            "score": "점수",
            "signal": "판정",
            "weight": "추천비중",
            "amount": "배분금",
            "price": "현재가",
            "shares": "예상수량",
            "holding_qty": "보유수량",
            "avg_price": "평균가",
            "pnl": "손익률",
            "market_value": "평가금액",
            "gap": "비중차이",
            "feedback": "보유피드백",
            "reason": "핵심근거",
        }
        portfolio_widths = {
            "name": 130,
            "code": 80,
            "score": 70,
            "signal": 105,
            "weight": 75,
            "amount": 110,
            "price": 95,
            "shares": 80,
            "holding_qty": 80,
            "avg_price": 95,
            "pnl": 75,
            "market_value": 110,
            "gap": 80,
            "feedback": 150,
            "reason": 220,
        }

        for column in self.portfolio_columns:
            self.portfolio_tree.heading(
                column,
                text=portfolio_headings[column]
            )
            self.portfolio_tree.column(
                column,
                width=portfolio_widths[column],
                anchor="center",
                stretch=False
            )

        portfolio_y_scroll = ttk.Scrollbar(
            self.portfolio_tab,
            orient="vertical",
            command=self.portfolio_tree.yview
        )
        portfolio_x_scroll = ttk.Scrollbar(
            self.portfolio_tab,
            orient="horizontal",
            command=self.portfolio_tree.xview
        )
        self.portfolio_tree.configure(
            yscrollcommand=portfolio_y_scroll.set,
            xscrollcommand=portfolio_x_scroll.set
        )
        self.portfolio_tree.pack(
            side="left",
            fill="both",
            expand=True
        )
        portfolio_y_scroll.pack(side="right", fill="y")
        portfolio_x_scroll.pack(side="bottom", fill="x")
        self.portfolio_tree.bind(
            "<<TreeviewSelect>>",
            self.on_portfolio_select
        )
        self.bind_horizontal_tree_drag(self.portfolio_tree)

        self._build_alert_tab()
        self.style_widget_tree()

    def _build_pc_side_menu(self):

        tk.Label(
            self.pc_side_menu,
            text="화면 메뉴",
            bg=self.colors["panel_alt"],
            fg=self.colors["text"],
            font=("맑은 고딕", 11, "bold")
        ).pack(fill="x", pady=(0, 8))

        menu_items = [
            ("대시보드", self.dashboard_tab),
            ("보유 종목", self.portfolio_tab),
            ("종목 분석", self.detail_tab),
            ("뉴스", self.news_tab),
            ("이벤트", self.event_tab),
            ("전략/메모", self.strategy_tab),
            ("설정", self.alert_tab),
        ]

        for label, tab in menu_items:
            tk.Button(
                self.pc_side_menu,
                text=label,
                anchor="w",
                command=lambda target=tab: self.select_pc_tab(target)
            ).pack(fill="x", pady=2)

    def select_pc_tab(self, tab):

        try:
            self.notebook.select(tab)
        except tk.TclError:
            pass

        if tab is self.detail_tab:
            self.refresh_detail_tab()
        elif tab is self.event_tab:
            self.refresh_event_tab()
        elif tab is self.strategy_tab:
            self.refresh_strategy_tab()
        elif tab is self.dashboard_tab:
            self.refresh_dashboard()

    def _build_pc_right_summary(self):

        tk.Label(
            self.pc_right_summary,
            text="요약 패널",
            bg=self.colors["panel"],
            fg=self.colors["text"],
            font=("맑은 고딕", 11, "bold")
        ).pack(anchor="w")

        self.pc_summary_vars = {}

        for key, label in (
            ("value", "총 평가금액"),
            ("pnl", "총 손익"),
            ("risk", "포트폴리오 위험도"),
            ("attention", "관심 필요"),
            ("upside", "상승 후보"),
            ("danger", "위험 증가"),
            ("events", "중요 이벤트"),
        ):
            frame = tk.Frame(self.pc_right_summary, bg=self.colors["panel"])
            frame.pack(fill="x", pady=(8, 0))
            tk.Label(
                frame,
                text=label,
                bg=self.colors["panel"],
                fg=self.colors["muted"],
                anchor="w"
            ).pack(fill="x")
            var = tk.StringVar(value="-")
            tk.Label(
                frame,
                textvariable=var,
                bg=self.colors["panel"],
                fg=self.colors["text"],
                font=("맑은 고딕", 12, "bold"),
                anchor="w"
            ).pack(fill="x")
            self.pc_summary_vars[key] = var

        self.pc_summary_message = tk.Text(
            self.pc_right_summary,
            height=8,
            wrap="word",
            relief="solid",
            borderwidth=1
        )
        self.pc_summary_message.pack(fill="both", expand=True, pady=(10, 0))
        self.pc_summary_message.insert(
            tk.END,
            "종목을 분석하면 요약과 위험 신호가 표시됩니다."
        )
        self.pc_summary_message.configure(state="disabled")

    def _build_detail_tab(self):

        self.detail_summary_var = tk.StringVar(
            value="종목을 선택하면 상세 요약이 표시됩니다."
        )
        tk.Label(
            self.detail_tab,
            textvariable=self.detail_summary_var,
            anchor="w",
            justify="left",
            font=("맑은 고딕", 10, "bold")
        ).pack(fill="x", pady=(0, 6))

        self.detail_notebook = ttk.Notebook(self.detail_tab)
        self.detail_notebook.pack(fill="both", expand=True)

        self.detail_summary_tab = tk.Frame(self.detail_notebook)
        self.detail_chart_tab = tk.Frame(self.detail_notebook)
        self.detail_score_tab = tk.Frame(self.detail_notebook)
        self.detail_news_tab = tk.Frame(self.detail_notebook)
        self.detail_strategy_tab = tk.Frame(self.detail_notebook)
        self.detail_event_tab = tk.Frame(self.detail_notebook)
        self.detail_history_tab = tk.Frame(self.detail_notebook)

        for tab, title in (
            (self.detail_summary_tab, "요약"),
            (self.detail_chart_tab, "차트"),
            (self.detail_score_tab, "점수"),
            (self.detail_news_tab, "뉴스"),
            (self.detail_strategy_tab, "전략"),
            (self.detail_event_tab, "이벤트"),
            (self.detail_history_tab, "기록"),
        ):
            self.detail_notebook.add(tab, text=title)

        self.detail_summary_text = tk.Text(self.detail_summary_tab, wrap="word")
        self.detail_summary_text.pack(fill="both", expand=True)

        self.detail_score_text = tk.Text(self.detail_score_tab, wrap="word")
        self.detail_score_text.pack(fill="both", expand=True)

        self.detail_news_tree = ttk.Treeview(
            self.detail_news_tab,
            columns=("date", "impact", "title"),
            show="headings"
        )
        for column, title, width in (
            ("date", "날짜", 120),
            ("impact", "호재/악재", 90),
            ("title", "뉴스 제목", 520),
        ):
            self.detail_news_tree.heading(column, text=title)
            self.detail_news_tree.column(
                column,
                width=width,
                anchor="w" if column == "title" else "center"
            )
        self.detail_news_tree.pack(fill="both", expand=True)

        self.detail_strategy_text = tk.Text(self.detail_strategy_tab, wrap="word")
        self.detail_strategy_text.pack(fill="both", expand=True)

        self.detail_event_text = tk.Text(self.detail_event_tab, wrap="word")
        self.detail_event_text.pack(fill="both", expand=True)

        self.detail_history_text = tk.Text(self.detail_history_tab, wrap="word")
        self.detail_history_text.pack(fill="both", expand=True)

        tk.Label(
            self.detail_chart_tab,
            text="차트는 상단 메뉴의 차트 화면과 동일한 데이터를 사용합니다. 종목 선택 후 차트 탭을 확인하세요.",
            anchor="w",
            justify="left"
        ).pack(fill="x", pady=6)

    def _build_event_tab(self):

        tk.Label(
            self.event_tab,
            text="이벤트 캘린더",
            font=("맑은 고딕", 11, "bold")
        ).pack(anchor="w", pady=(0, 6))
        self.event_text = tk.Text(self.event_tab, wrap="word")
        self.event_text.pack(fill="both", expand=True)
        self.refresh_event_tab()

    def _build_strategy_tab(self):

        tk.Label(
            self.strategy_tab,
            text="전략 / 메모",
            font=("맑은 고딕", 11, "bold")
        ).pack(anchor="w", pady=(0, 6))
        self.strategy_text = tk.Text(self.strategy_tab, wrap="word")
        self.strategy_text.pack(fill="both", expand=True)
        self.refresh_strategy_tab()

    def bind_horizontal_tree_drag(self, tree):

        drag_state = {
            "x": 0,
            "view": 0.0,
            "dragging": False,
        }

        def on_press(event):
            drag_state["x"] = event.x
            drag_state["view"] = tree.xview()[0]
            drag_state["dragging"] = False

        def on_drag(event):
            delta = event.x - drag_state["x"]

            if abs(delta) < 6:
                return

            drag_state["dragging"] = True
            width = max(tree.winfo_width(), 1)
            move = delta / width
            tree.xview_moveto(max(0.0, min(1.0, drag_state["view"] - move)))
            return "break"

        def on_release(event):
            if drag_state["dragging"]:
                drag_state["dragging"] = False
                return "break"

        tree.bind("<ButtonPress-1>", on_press, add="+")
        tree.bind("<B1-Motion>", on_drag, add="+")
        tree.bind("<ButtonRelease-1>", on_release, add="+")

    def _build_dashboard_tab(self):

        colors = self.colors

        top_frame = tk.Frame(self.dashboard_tab, bg=colors["bg"])
        top_frame.pack(fill="x", padx=4, pady=(0, 8))

        self.dashboard_cards = {}
        card_defs = [
            ("group", "그룹", "-"),
            ("count", "관심종목", "0"),
            ("best", "최고 점수", "-"),
            ("holding", "보유 평가", "-"),
            ("alert", "알림", "-"),
        ]

        for key, title, value in card_defs:
            card = tk.Frame(
                top_frame,
                bg=colors["panel"],
                highlightbackground=colors["line"],
                highlightthickness=1,
                padx=12,
                pady=10
            )
            card.pack(
                side="left",
                fill="x",
                expand=True,
                padx=(0, 8)
            )

            tk.Label(
                card,
                text=title,
                bg=colors["panel"],
                fg=colors["muted"],
                font=("맑은 고딕", 9)
            ).pack(anchor="w")

            value_label = tk.Label(
                card,
                text=value,
                bg=colors["panel"],
                fg=colors["text"],
                font=("맑은 고딕", 14, "bold")
            )
            value_label.pack(anchor="w", pady=(4, 0))
            self.dashboard_cards[key] = value_label

        action_frame = tk.Frame(self.dashboard_tab, bg=colors["bg"])
        action_frame.pack(fill="x", padx=4, pady=(0, 8))

        tk.Button(
            action_frame,
            text="대시보드 새로고침",
            command=self.refresh_dashboard
        ).pack(side="left", padx=(0, 4))

        tk.Button(
            action_frame,
            text="그룹 분석",
            command=self.refresh_group
        ).pack(side="left")

        self.dashboard_columns = (
            "name",
            "code",
            "score",
            "signal",
            "price",
            "change",
            "holding",
            "feedback",
        )
        self.dashboard_tree = ttk.Treeview(
            self.dashboard_tab,
            columns=self.dashboard_columns,
            show="headings"
        )

        headings = {
            "name": "종목명",
            "code": "코드",
            "score": "점수",
            "signal": "판정",
            "price": "현재가",
            "change": "등락률",
            "holding": "보유",
            "feedback": "피드백",
        }
        widths = {
            "name": 140,
            "code": 85,
            "score": 70,
            "signal": 110,
            "price": 95,
            "change": 75,
            "holding": 95,
            "feedback": 170,
        }

        for column in self.dashboard_columns:
            self.dashboard_tree.heading(column, text=headings[column])
            self.dashboard_tree.column(
                column,
                width=widths[column],
                anchor="center",
                stretch=False
            )

        self.configure_tree_tags(self.dashboard_tree)
        self.dashboard_tree.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self.dashboard_tree.bind(
            "<Double-Button-1>",
            self.on_dashboard_select
        )

    def _build_briefing_tab(self):

        toolbar = tk.Frame(self.briefing_tab)
        toolbar.pack(fill="x", pady=(0, 4))

        tk.Button(
            toolbar,
            text="브리핑 새로고침",
            command=self.refresh_briefing_table
        ).pack(side="left", padx=(0, 4))

        tk.Button(
            toolbar,
            text="그룹 분석 후 새로고침",
            command=self.refresh_group
        ).pack(side="left")

        tk.Button(
            toolbar,
            text="브리핑 저장",
            command=self.save_ai_quant_briefing
        ).pack(side="left", padx=(4, 0))

        self.briefing_report_text = tk.Text(
            self.briefing_tab,
            height=13,
            wrap="word"
        )
        self.briefing_report_text.pack(fill="x", pady=(0, 4))

        self.briefing_columns = (
            "name",
            "code",
            "asset_type",
            "price",
            "price_date",
            "freshness",
            "change_1d",
            "change_1m",
            "change_3m",
            "score",
            "news_score",
            "avg_score",
            "analyst",
            "short_ratio",
            "foreign_net_buy",
            "institution_net_buy",
            "briefing",
        )
        self.briefing_tree = ttk.Treeview(
            self.briefing_tab,
            columns=self.briefing_columns,
            show="headings"
        )
        self.configure_tree_tags(self.briefing_tree)

        headings = {
            "name": "종목",
            "code": "코드",
            "asset_type": "구분",
            "price": "최신가",
            "price_date": "기준일",
            "freshness": "신선도",
            "change_1d": "1일",
            "change_1m": "1개월",
            "change_3m": "3개월",
            "score": "퀀트",
            "news_score": "뉴스",
            "avg_score": "평균",
            "analyst": "애널리스트",
            "short_ratio": "공매도",
            "foreign_net_buy": "외국인",
            "institution_net_buy": "기관",
            "briefing": "AI/뉴스 해석",
        }
        widths = {
            "name": 140,
            "code": 80,
            "asset_type": 65,
            "price": 100,
            "price_date": 90,
            "freshness": 80,
            "change_1d": 70,
            "change_1m": 70,
            "change_3m": 70,
            "score": 70,
            "news_score": 70,
            "avg_score": 70,
            "analyst": 120,
            "short_ratio": 75,
            "foreign_net_buy": 110,
            "institution_net_buy": 110,
            "briefing": 360,
        }

        for column in self.briefing_columns:
            self.briefing_tree.heading(column, text=headings[column])
            self.briefing_tree.column(
                column,
                width=widths[column],
                anchor="center" if column != "briefing" else "w",
                stretch=(column == "briefing")
            )

        y_scroll = ttk.Scrollbar(
            self.briefing_tab,
            orient="vertical",
            command=self.briefing_tree.yview
        )
        x_scroll = ttk.Scrollbar(
            self.briefing_tab,
            orient="horizontal",
            command=self.briefing_tree.xview
        )
        self.briefing_tree.configure(
            yscrollcommand=y_scroll.set,
            xscrollcommand=x_scroll.set
        )
        self.briefing_tree.pack(side="left", fill="both", expand=True)
        y_scroll.pack(side="right", fill="y")
        x_scroll.pack(side="bottom", fill="x")
        self.briefing_tree.bind(
            "<Double-Button-1>",
            self.on_briefing_select
        )
        self.bind_horizontal_tree_drag(self.briefing_tree)

    def _build_alert_tab(self):

        alert_frame = tk.Frame(self.alert_tab)
        alert_frame.pack(fill="x", padx=4, pady=4)

        tk.Checkbutton(
            alert_frame,
            text="조건 알림 사용",
            variable=self.alert_enabled_var
        ).grid(row=0, column=0, sticky="w")

        tk.Checkbutton(
            alert_frame,
            text="화면 알림",
            variable=self.alert_popup_var
        ).grid(row=0, column=1, sticky="w")

        tk.Checkbutton(
            alert_frame,
            text="이메일 알림",
            variable=self.alert_email_var
        ).grid(row=0, column=2, sticky="w")

        tk.Label(alert_frame, text="알림 기준 점수").grid(
            row=1,
            column=0,
            sticky="w",
            pady=(8, 0)
        )
        tk.Entry(
            alert_frame,
            textvariable=self.alert_threshold_var,
            width=10
        ).grid(row=1, column=1, sticky="w", pady=(8, 0))

        tk.Checkbutton(
            alert_frame,
            text="예약 메일",
            variable=self.scheduled_email_var
        ).grid(row=1, column=2, sticky="w", pady=(8, 0))

        tk.Entry(
            alert_frame,
            textvariable=self.scheduled_time_var,
            width=8
        ).grid(row=1, column=3, sticky="w", pady=(8, 0))

        tk.Label(alert_frame, text="받는 메일").grid(
            row=2,
            column=0,
            sticky="w",
            pady=(8, 0)
        )
        tk.Entry(
            alert_frame,
            textvariable=self.alert_recipient_var,
            width=34
        ).grid(
            row=2,
            column=1,
            columnspan=3,
            sticky="we",
            pady=(8, 0)
        )

        tk.Label(alert_frame, text="SMTP 서버").grid(
            row=3,
            column=0,
            sticky="w",
            pady=(8, 0)
        )
        tk.Entry(
            alert_frame,
            textvariable=self.smtp_host_var,
            width=24
        ).grid(row=3, column=1, sticky="w", pady=(8, 0))

        tk.Label(alert_frame, text="포트").grid(
            row=3,
            column=2,
            sticky="w",
            pady=(8, 0)
        )
        tk.Entry(
            alert_frame,
            textvariable=self.smtp_port_var,
            width=8
        ).grid(row=3, column=3, sticky="w", pady=(8, 0))

        tk.Label(alert_frame, text="보내는 계정").grid(
            row=4,
            column=0,
            sticky="w",
            pady=(8, 0)
        )
        tk.Entry(
            alert_frame,
            textvariable=self.smtp_user_var,
            width=34
        ).grid(
            row=4,
            column=1,
            columnspan=3,
            sticky="we",
            pady=(8, 0)
        )

        tk.Label(alert_frame, text="비밀번호").grid(
            row=5,
            column=0,
            sticky="w",
            pady=(8, 0)
        )
        tk.Entry(
            alert_frame,
            textvariable=self.smtp_password_var,
            show="*",
            width=34
        ).grid(
            row=5,
            column=1,
            columnspan=3,
            sticky="we",
            pady=(8, 0)
        )

        tk.Checkbutton(
            alert_frame,
            text="TLS 사용",
            variable=self.smtp_tls_var
        ).grid(row=6, column=0, sticky="w", pady=(8, 0))

        tk.Label(alert_frame, text="분석 서버 URL").grid(
            row=7,
            column=0,
            sticky="w",
            pady=(8, 0)
        )
        tk.Entry(
            alert_frame,
            textvariable=self.api_base_url_var,
            width=48
        ).grid(
            row=7,
            column=1,
            columnspan=3,
            sticky="we",
            pady=(8, 0)
        )
        tk.Label(
            alert_frame,
            text="입력하면 분석 시 서버를 먼저 사용하고 실패하면 로컬 분석으로 전환합니다.",
            fg=self.colors["muted"]
        ).grid(
            row=8,
            column=0,
            columnspan=4,
            sticky="w",
            pady=(2, 0)
        )

        tk.Label(alert_frame, text="자동 새로고침(분)").grid(
            row=9,
            column=0,
            sticky="w",
            pady=(8, 0)
        )
        tk.Entry(
            alert_frame,
            textvariable=self.auto_refresh_interval_var,
            width=8
        ).grid(row=9, column=1, sticky="w", pady=(8, 0))
        tk.Label(
            alert_frame,
            text="기본값 20분, 1분 이상 입력",
            fg=self.colors["muted"]
        ).grid(
            row=9,
            column=2,
            columnspan=2,
            sticky="w",
            pady=(8, 0)
        )

        button_frame = tk.Frame(self.alert_tab)
        button_frame.pack(fill="x", padx=4, pady=(8, 4))

        tk.Button(
            button_frame,
            text="설정 저장",
            command=self.save_alert_settings
        ).pack(side="left", padx=(0, 4))

        tk.Button(
            button_frame,
            text="테스트 메일",
            command=self.send_test_email
        ).pack(side="left", padx=(0, 4))

        tk.Button(
            button_frame,
            text="현재 리포트 메일 전송",
            command=self.send_current_report_email
        ).pack(side="left")

        self.alert_log = tk.Text(
            self.alert_tab,
            height=8,
            wrap="word"
        )
        self.alert_log.pack(fill="both", expand=True, padx=4, pady=(0, 4))

    # --------------------------------------------------
    # 검색 (자동완성)
    # --------------------------------------------------
    def create_search_service(self):

        if not self.krx:
            raise RuntimeError("KRX collector is not available")

        return SearchService(self.krx)

    def add_search_result(self, name, code, seen):

        code = StockResolver.normalize_code(code)

        if not code or code in seen:
            return False

        self.listbox.insert(tk.END, f"{name or code} ({code})")
        seen.add(code)
        return True

    def on_search(self, event):
        keyword = self.search_var.get().strip()

        self.listbox.delete(0, tk.END)

        if not keyword:
            return

        seen = set()
        count = 0

        resolved = self.stock_resolver.resolve_keyword(keyword)

        if resolved and self.add_search_result(
            resolved.get("name", ""),
            resolved.get("code", ""),
            seen
        ):
            count += 1

        if not self.krx:
            return

        # -----------------------------
        # 한국 종목
        # -----------------------------
        for stock in self.krx.search(keyword, limit=10):

            if self.add_search_result(
                stock.get("name", ""),
                stock.get("code", ""),
                seen
            ):
                count += 1

            if count >= 10:
                break

        # -----------------------------
        # 미국 종목
        # -----------------------------
        if count < 10:

            from morning_stock_assistant.collectors.market.us_market import USMarket

            us = USMarket()

            for stock in us.search(keyword):

                if self.add_search_result(
                    stock.get("name", ""),
                    stock.get("code", ""),
                    seen
                ):
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

        if self.current_group is None:
            messagebox.showwarning(
                "알림",
                "먼저 그룹을 선택하세요."
            )
            return

        value = self.listbox.get(selection[0])

        name = value.split("(")[0].strip()
        code = value.split("(")[-1].replace(")", "").strip()

        stocks = self.groups[self.current_group]

        for item in stocks:
            if item["code"] == code:
                return

        stocks.append({
            "name": name,
            "code": code
        })

        self.stock_list.insert(tk.END, name)

        self.save_groups()

        self.search_var.set("")
        self.listbox.delete(0, tk.END)

    # --------------------------------------------------
    # 분석 실행
    # --------------------------------------------------
    def get_weight_preset(self):

        return self.weight_preset_var.get() or "균형형"

    def on_weight_preset_change(self, event=None):

        preset = self.get_weight_preset()
        self.analyzer.factor.set_preset(preset)

        self.refresh_stock_list()
        self.refresh_portfolio_table(auto_analyze=False)
        self.refresh_briefing_table()

        if self.current_stock:
            self.analyze_stock()

    def analyze_stock(self):

        if not self.current_stock:
            return

        if self.stock_analysis_running:
            self.status_var.set(
                f"{self.stock_analysis_code or '종목'} 분석 중입니다..."
            )
            return

        stock_code = self.current_stock
        stock_name = stock_code

        if self.current_group:
            for stock in self.groups.get(self.current_group, []):
                if stock.get("code") == stock_code:
                    stock_name = stock.get("name", stock_code)
                    break

        self.stock_analysis_running = True
        self.stock_analysis_code = stock_code
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(
            tk.END,
            "분석 중입니다...\n"
        )

        if hasattr(self, "finance_text"):
            self.finance_text.delete("1.0", tk.END)
        if hasattr(self, "scenario_text"):
            self.scenario_text.delete("1.0", tk.END)

        if hasattr(self, "news_list"):
            for item in self.news_list.get_children():
                self.news_list.delete(item)

        preset = self.get_weight_preset()

        thread = threading.Thread(
            target=self.run_analysis,
            args=(preset, stock_code, stock_name),
            daemon=True
        )

        thread.start()

    def run_analysis(self, preset, stock_code, stock_name):

        result = None

        if self.remote_client().enabled:
            try:
                self.show_server_connecting("서버")

                result = self.analyze_one_remote(
                    stock_code,
                    stock_name,
                    preset
                )
                self.root.after(
                    0,
                    lambda: self.status_var.set("서버 분석 완료")
                )
            except Exception as e:
                print("서버 분석 오류, 로컬 분석으로 전환:", e)
                self.root.after(
                    0,
                    lambda: self.status_var.set("서버 실패, 로컬 분석 중...")
                )

        if result is not None:
            self.root.after(
                0,
                lambda: self.analysis_finished(result)
            )
            return

        try:
            result = self.analyzer.analyze(
                stock_code,
                "2025",
                "11011",
                preset
            )
        except Exception as e:
            print("분석 오류:", e)
            result = None

        self.root.after(
            0,
            lambda: self.analysis_finished(result)
        )

    def analysis_finished(self, result):

        self.stock_analysis_running = False
        self.stock_analysis_code = None

        if result is None:

            self.status_var.set("분석 실패")

            messagebox.showerror(
                "오류",
                "종목 분석에 실패했습니다."
            )

            return

        self.current_result = result
        self.show_result(result)
        self.refresh_stock_list()
        self.refresh_portfolio_table(auto_analyze=False)
        self.refresh_briefing_table()
        self.refresh_dashboard()
        self.refresh_detail_tab()
        self.handle_analysis_alert(result)

        self.status_var.set(
            f"{result.name} 분석 완료"
        )

        try:
            self.draw_chart()

        except Exception as e:

            print("차트 오류:", e)

        try:
            self.load_news()

        except Exception as e:

            print("뉴스 오류:", e)


    # --------------------------------------------------
    # 결과 출력
    # --------------------------------------------------
    def show_result(self, result):
        self.result_text.delete("1.0", tk.END)

        quant_score = self.quant_average_score(result)
        news_score = self.news_normalized_score(result)
        final_formula_score = round((quant_score * 0.7) + (news_score * 0.3), 1)

        def money(value):
            return self.format_display_price(
                safe_number(value),
                getattr(result, "currency", "KRW")
            )

        def number(value, digits=2):
            value = safe_number(value)
            return f"{value:,.{digits}f}"

        def integer(value):
            return f"{safe_number(value):,.0f}"

        breakdown_lines = []

        for item in getattr(result, "score_breakdown", []):
            weight_percent = item["weight"] * 100
            breakdown_lines.append(
                f"- {item['name']}: 원점수 {item['raw_score']:.1f} "
                f"x {weight_percent:.0f}% = {item['contribution']:.2f}점"
            )

            for reason in item.get("reasons", []):
                breakdown_lines.append(f"  · {reason}")

        if not breakdown_lines:
            breakdown_lines.append("- 점수 산출 근거가 없습니다.")

        analysis_text = "\n".join([
            "==============================",
            f"{result.name} ({result.code})",
            "==============================",
            f"상태: {self.daily_status(result, final_formula_score)}",
            f"오늘 핵심: {self.daily_core(result)}",
            f"점수: {final_formula_score:.0f}점",
            f"판단: {self.daily_judgment(result, final_formula_score)}",
            "",
            "[판정]",
            f"가중치 프리셋 : {getattr(result, 'preset', '균형형')}",
            f"투자의견 : {result.signal}",
            f"종합점수 : {number(result.score)}",
            f"퀀트 점수 : {number(quant_score)}",
            f"뉴스 점수 : {number(news_score)}",
            f"최종 점수 : {number(final_formula_score)}",
            "최종 점수 산식 : 퀀트 점수 70% + 뉴스 점수 30%",
            "",
            "[매매 기준]",
            *self.investment_plan_lines(result, quant_score, news_score, final_formula_score),
            "",
            "[현재가]",
            f"현재가 : {money(result.price)}",
            f"등락률 : {number(result.change_rate)}%",
            f"PER/PBR : {number(result.per)} / {number(result.pbr)}",
            f"PCR/PSR : {number(getattr(result, 'pcr', 0))} / "
            f"{number(getattr(result, 'psr', 0))}",
            "",
            "[팩터 점수]",
            f"가치 점수     : {number(self.factor_score_value(result, 'value'), 1)}",
            f"품질 점수     : {number(self.factor_score_value(result, 'quality'), 1)}",
            f"성장 점수     : {number(self.factor_score_value(result, 'growth'), 1)}",
            f"안정성 점수   : {number(self.factor_score_value(result, 'stability'), 1)}",
            f"모멘텀 점수   : {number(self.factor_score_value(result, 'momentum'), 1)}",
            f"뉴스 점수     : {number(news_score, 1)} "
            f"(환산 {number(news_score, 1)})",
            "",
            "[코멘트]",
            "[점수 산출 근거]",
            *breakdown_lines,
            "",
            result.comment or "-",
        ])

        self.result_text.insert(tk.END, analysis_text)
        self.show_finance_result(result)
        self.show_scenario_result(result)
        return

        text = "\n".join([
            "==============================",
            f"{result.name} ({result.code})",
            "==============================",
            "",
            "[판정]",
            f"투자의견 : {result.signal}",
            f"종합점수 : {number(result.score)}",
            "",
            "[현재가]",
            f"현재가   : {money(result.price)}",
            f"등락률   : {number(result.change_rate)}%",
            f"PER      : {number(result.per)}",
            f"PBR      : {number(result.pbr)}",
            f"EPS      : {number(getattr(result, 'eps', 0))}",
            f"BPS      : {number(getattr(result, 'bps', 0))}",
            "",
            "[팩터 점수]",
            f"Value     : {number(result.value, 1)}",
            f"Quality   : {number(result.quality, 1)}",
            f"Growth    : {number(result.growth, 1)}",
            f"Stability : {number(result.stability, 1)}",
            f"Dividend  : {number(result.dividend, 1)}",
            f"Momentum  : {number(result.momentum, 1)}",
            f"News      : {number(result.news, 1)}",
            "",
            "[재무]",
            f"매출액       : {integer(getattr(result, 'sales', 0))}",
            f"영업이익     : {integer(getattr(result, 'operating_profit', 0))}",
            f"순이익       : {integer(result.net_income)}",
            f"자산총계     : {integer(getattr(result, 'assets', 0))}",
            f"부채총계     : {integer(getattr(result, 'liabilities', 0))}",
            f"자본총계     : {integer(getattr(result, 'equity', 0))}",
            "",
            "[수익성 / 안정성]",
            f"ROE        : {number(result.roe)}%",
            f"ROIC       : {number(getattr(result, 'roic', 0))}%",
            f"ROA        : {number(getattr(result, 'roa', 0))}%",
            f"영업이익률  : {number(getattr(result, 'operating_margin', 0))}%",
            f"순이익률    : {number(getattr(result, 'net_margin', 0))}%",
            f"부채비율    : {number(result.debt_ratio)}%",
            f"유동비율    : {number(getattr(result, 'current_ratio', 0))}%",
            f"FCF Yield  : {number(getattr(result, 'fcf_yield', 0))}%",
            "",
            "[성장 / 배당]",
            f"매출성장률   : {number(getattr(result, 'sales_growth', 0))}%",
            f"영업이익성장률: {number(getattr(result, 'op_growth', 0))}%",
            f"EPS성장률    : {number(getattr(result, 'eps_growth', 0))}%",
            f"3년 매출 CAGR : {number(getattr(result, 'sales_cagr_3y', 0))}%",
            f"3년 영업익 CAGR: {number(getattr(result, 'op_cagr_3y', 0))}%",
            f"3년 순이익 CAGR: {number(getattr(result, 'net_income_cagr_3y', 0))}%",
            f"BPS성장률    : {number(getattr(result, 'bps_growth', 0))}%",
            f"배당수익률   : {number(getattr(result, 'dividend_yield', 0))}%",
            f"잉여현금흐름 : {integer(getattr(result, 'free_cash_flow', 0))}",
            f"영업현금흐름 : {integer(getattr(result, 'operating_cash_flow', 0))}",
            f"CapEx        : {integer(getattr(result, 'capex', 0))}",
            f"현금         : {integer(getattr(result, 'cash', 0))}",
            f"총차입금     : {integer(getattr(result, 'total_debt', 0))}",
            "",
            "[기술적 지표]",
            f"MA20      : {money(getattr(result, 'ma20', 0))}",
            f"MA60      : {money(getattr(result, 'ma60', 0))}",
            f"MA120     : {money(getattr(result, 'ma120', 0))}",
            f"52주 고가 : {money(getattr(result, 'high52', 0))}",
            f"52주 저가 : {money(getattr(result, 'low52', 0))}",
            f"거래량 비율: {number(getattr(result, 'volume_ratio', 0))}x",
            "",
            "[코멘트]",
            result.comment or "-",
        ])

        self.result_text.insert(tk.END, text)

    def show_finance_result(self, result):

        self.finance_text.delete("1.0", tk.END)
        quant_score = self.quant_average_score(result)
        news_score = self.news_normalized_score(result)
        final_formula_score = round((quant_score * 0.7) + (news_score * 0.3), 1)

        def money(value):
            return self.format_display_price(
                safe_number(value),
                getattr(result, "currency", "KRW")
            )

        def number(value, digits=2):
            value = safe_number(value)
            return f"{value:,.{digits}f}"

        def integer(value):
            return f"{safe_number(value):,.0f}"

        finance_text = "\n".join([
            "==============================",
            f"재무 / 지표 - {result.name} ({result.code})",
            "==============================",
            "",
            "[가격 / 밸류에이션]",
            f"현재가       : {money(result.price)}",
            f"가격 기준일  : {getattr(result, 'price_date', '-') or '-'}",
            f"등락률       : {number(result.change_rate)}%",
            f"퀀트 점수    : {number(quant_score)}",
            f"뉴스 점수    : {number(news_score)}",
            f"최종 점수    : {number(final_formula_score)}",
            "최종 산식    : 퀀트 점수 70% + 뉴스 점수 30%",
            *self.investment_plan_lines(result, quant_score, news_score, final_formula_score),
            f"애널리스트  : {self.analyst_summary(result)}",
            f"PER          : {number(result.per)}",
            f"PBR          : {number(result.pbr)}",
            f"PCR          : {number(getattr(result, 'pcr', 0))}",
            f"PSR          : {number(getattr(result, 'psr', 0))}",
            f"EPS          : {number(getattr(result, 'eps', 0))}",
            f"BPS          : {number(getattr(result, 'bps', 0))}",
            f"시가총액     : {integer(getattr(result, 'market_cap', 0))}",
            f"구분         : {getattr(result, 'asset_type', 'STOCK')}",
            f"업종대비 PER : {number(getattr(result, 'relative_per', 0))}",
            f"업종대비 PBR : {number(getattr(result, 'relative_pbr', 0))}",
            "",
            "[수급 / 공매도]",
            f"공매도 비율  : {number(getattr(result, 'short_ratio', 0))}%",
            f"외국인 순매수: {self.format_flow_value(getattr(result, 'foreign_net_buy', None))}",
            f"기관 순매수  : {self.format_flow_value(getattr(result, 'institution_net_buy', None))}",
            f"개인 순매수  : {self.format_flow_value(getattr(result, 'individual_net_buy', None))}",
            f"기관 보유율  : {number(getattr(result, 'institutional_ownership', 0))}%",
            "",
            "[재무제표]",
            f"매출액       : {integer(getattr(result, 'sales', 0))}",
            f"영업이익     : {integer(getattr(result, 'operating_profit', 0))}",
            f"순이익       : {integer(result.net_income)}",
            f"자산총계     : {integer(getattr(result, 'assets', 0))}",
            f"부채총계     : {integer(getattr(result, 'liabilities', 0))}",
            f"자본총계     : {integer(getattr(result, 'equity', 0))}",
            f"잉여현금흐름 : {integer(getattr(result, 'free_cash_flow', 0))}",
            "",
            "[수익성 / 안정성]",
            f"ROE        : {number(result.roe)}%",
            f"ROA        : {number(getattr(result, 'roa', 0))}%",
            f"영업이익률  : {number(getattr(result, 'operating_margin', 0))}%",
            f"순이익률    : {number(getattr(result, 'net_margin', 0))}%",
            f"부채비율    : {number(result.debt_ratio)}%",
            f"유동비율    : {number(getattr(result, 'current_ratio', 0))}%",
            "",
            "[성장 / 배당]",
            f"매출성장률    : {number(getattr(result, 'sales_growth', 0))}%",
            f"영업이익성장률: {number(getattr(result, 'op_growth', 0))}%",
            f"EPS성장률     : {number(getattr(result, 'eps_growth', 0))}%",
            f"BPS성장률     : {number(getattr(result, 'bps_growth', 0))}%",
            f"배당수익률    : {number(getattr(result, 'dividend_yield', 0))}%",
            "",
            "[기술적 지표]",
            f"MA20       : {money(getattr(result, 'ma20', 0))}",
            f"MA60       : {money(getattr(result, 'ma60', 0))}",
            f"MA120      : {money(getattr(result, 'ma120', 0))}",
            f"52주 고가  : {money(getattr(result, 'high52', 0))}",
            f"52주 저가  : {money(getattr(result, 'low52', 0))}",
            f"거래량 비율: {number(getattr(result, 'volume_ratio', 0))}x",
        ])

        self.finance_text.insert(tk.END, finance_text)

    def show_scenario_result(self, result):

        if not hasattr(self, "scenario_text"):
            return

        self.scenario_text.delete("1.0", tk.END)
        quant_score = self.quant_average_score(result)
        news_score = self.news_normalized_score(result)
        final_score = round((quant_score * 0.7) + (news_score * 0.3), 1)
        currency = getattr(result, "currency", "KRW")
        price = safe_number(getattr(result, "price", 0))
        remote_record = getattr(result, "remote_record", None)

        if isinstance(remote_record, dict):
            program_targets = remote_record.get("program_target_prices") or {}
            downside = remote_record.get("downside_scenario") or {}
            scenario_summary = remote_record.get("scenario_summary") or ""
            analyst_target = safe_number(
                remote_record.get("analyst_target_price")
                or remote_record.get("target_price", 0)
            )
            analyst_high = safe_number(remote_record.get("analyst_target_high", 0))
            analyst_low = safe_number(remote_record.get("analyst_target_low", 0))
        else:
            factor_scores = SharedAnalysisBridge.factor_scores(result)
            stock_type = SharedAnalysisBridge.stock_type(
                result,
                str(getattr(result, "code", "") or ""),
                str(getattr(result, "name", "") or ""),
            )
            analyst_target = safe_number(
                getattr(result, "analyst_target_mean", 0)
                or getattr(result, "target_price", 0)
            )
            analyst_high = safe_number(getattr(result, "analyst_target_high", 0))
            analyst_low = safe_number(getattr(result, "analyst_target_low", 0))
            program_targets = SharedAnalysisBridge.program_target_prices(
                result=result,
                price=price,
                final_score=final_score,
                news_score=news_score,
                factor_scores=factor_scores,
                stock_type=stock_type,
                currency=currency,
            )
            downside = SharedAnalysisBridge.downside_scenario(
                result=result,
                price=price,
                final_score=final_score,
                news_score=news_score,
                factor_scores=factor_scores,
                metrics={
                    "change_1d": safe_number(getattr(result, "change_rate", 0)),
                    "change_1m": 0,
                    "change_3m": 0,
                },
                data_confidence="medium",
                currency=currency,
            )
            scenario_summary = SharedAnalysisBridge.scenario_summary(
                analyst_target,
                program_targets,
                downside,
            )

        def money(value):
            value = safe_number(value)
            if value <= 0:
                return "-"
            return self.format_display_price(value, currency, compact=True)

        analyst_upside = (
            ((analyst_target - price) / price) * 100
            if analyst_target > 0 and price > 0
            else 0
        )
        target_lines = [
            "==============================",
            f"시나리오 - {result.name} ({result.code})",
            "==============================",
            "",
            "[요약]",
            scenario_summary or "-",
            "",
            "[애널리스트 목표가]",
            f"평균 목표가 : {money(analyst_target)}"
            + (f" ({analyst_upside:+.1f}%)" if analyst_target > 0 and price > 0 else ""),
            f"상단 목표가 : {money(analyst_high)}",
            f"하단 목표가 : {money(analyst_low)}",
            "설명        : 증권사 또는 데이터 제공처의 애널리스트 목표가입니다. 없으면 '-'로 표시합니다.",
            "",
            "[프로그램 산출 목표가]",
            f"보수 목표가 : {money(program_targets.get('conservative', 0))}",
            f"기준 목표가 : {money(program_targets.get('base', 0))}",
            f"공격 목표가 : {money(program_targets.get('aggressive', 0))}",
            f"산출 기준   : {program_targets.get('method', '-')}",
            f"이유        : {program_targets.get('reason', '-')}",
            f"설명        : {program_targets.get('basis', '-')}",
            "",
            "[하락 시나리오]",
            f"하락 위험도 : {downside.get('risk_level', '-')}",
            f"1차 지지선  : {money(downside.get('support_1', 0))}",
            f"2차 지지선  : {money(downside.get('support_2', 0))}",
            f"손절/점검선 : {money(downside.get('stop_check', 0))}",
            f"산출 기준   : {downside.get('method', '-')}",
            f"요약        : {downside.get('summary', '-')}",
            "",
            "[하락 시나리오 이유]",
        ]
        target_lines.extend(
            f"- {reason}"
            for reason in downside.get("reasons", []) or ["위험 이유 데이터 없음"]
        )
        target_lines.extend([
            "",
            "[주의]",
            "프로그램 산출 목표가와 하락 시나리오는 예측값이 아니라 대응 기준가입니다.",
        ])

        self.scenario_text.insert(tk.END, "\n".join(target_lines))

    def save_current_report(self):

        result = self.current_result

        if result is None:
            messagebox.showinfo(
                "리포트 저장",
                "먼저 종목을 분석한 뒤 저장하세요."
            )
            return

        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        now = datetime.now()
        safe_name = self._safe_report_filename(
            f"{result.name}_{result.code}_{now:%Y%m%d_%H%M}"
        )
        default_path = REPORT_DIR / f"{safe_name}.txt"

        file_path = filedialog.asksaveasfilename(
            title="리포트 저장",
            initialdir=str(REPORT_DIR),
            initialfile=default_path.name,
            defaultextension=".txt",
            filetypes=[
                ("텍스트 파일", "*.txt"),
                ("모든 파일", "*.*"),
            ]
        )

        if not file_path:
            return

        report_text = self.build_report_text(result, now)

        try:
            Path(file_path).write_text(
                report_text,
                encoding="utf-8"
            )
        except Exception as e:
            messagebox.showerror(
                "리포트 저장 실패",
                str(e)
            )
            return

        self.status_var.set(f"리포트 저장 완료: {file_path}")
        messagebox.showinfo(
            "리포트 저장",
            "리포트를 저장했습니다."
        )

    def build_report_text(self, result, created_at):

        analysis = self.result_text.get(
            "1.0",
            tk.END
        ).strip()
        finance = self.finance_text.get(
            "1.0",
            tk.END
        ).strip()
        news_lines = self._build_report_news_lines()

        return "\n".join([
            "Morning Stock Assistant Pro 리포트",
            "=" * 36,
            f"생성일시 : {created_at:%Y-%m-%d %H:%M:%S}",
            f"종목     : {result.name} ({result.code})",
            f"프리셋   : {getattr(result, 'preset', self.get_weight_preset())}",
            "",
            "[분석]",
            analysis or "-",
            "",
            "[재무]",
            finance or "-",
            "",
            "[뉴스]",
            *news_lines,
            "",
            "[주의]",
            "이 리포트는 자동 수집 데이터와 규칙 기반 점수로 만든 참고 자료입니다.",
            "투자 판단과 책임은 사용자에게 있습니다.",
            "",
        ])

    def _build_report_news_lines(self):

        if not self.current_news:
            return ["- 뉴스가 없습니다."]

        lines = []

        for index, item in enumerate(self.current_news, start=1):
            date = item.get("date", "")
            label = item.get("impact_label", "중립")
            score = safe_number(item.get("impact_score"))
            event_type = item.get("event_type", "일반 뉴스")
            title = item.get("title", "")
            url = item.get("url", "")
            prefix = f"{index}. "

            if date:
                prefix += f"{date} | "

            lines.append(
                f"{prefix}[{label} {score:+.0f} / {event_type}] {title}"
            )

            if url:
                lines.append(f"   {url}")

        return lines

    @staticmethod
    def _safe_report_filename(name):

        invalid_chars = '<>:"/\\|?*'

        for char in invalid_chars:
            name = name.replace(char, "_")

        return name.strip() or "report"

    def load_alert_settings(self):

        if not self.alert_settings_file.exists():
            return

        try:
            settings = json.loads(
                self.alert_settings_file.read_text(
                    encoding="utf-8"
                )
            )
        except Exception:
            return

        self.alert_enabled_var.set(
            bool(settings.get("alert_enabled", False))
        )
        self.alert_popup_var.set(
            bool(settings.get("alert_popup", True))
        )
        self.alert_email_var.set(
            bool(settings.get("alert_email", False))
        )
        self.alert_threshold_var.set(
            str(settings.get("alert_threshold", "75"))
        )
        self.scheduled_email_var.set(
            bool(settings.get("scheduled_email", False))
        )
        self.scheduled_time_var.set(
            settings.get("scheduled_time", "08:30")
        )
        self.auto_refresh_interval_var.set(
            str(settings.get("auto_refresh_interval_minutes", "20"))
        )
        self.alert_recipient_var.set(
            settings.get("alert_recipient", "")
        )
        self.smtp_host_var.set(
            settings.get("smtp_host", "smtp.gmail.com")
        )
        self.smtp_port_var.set(
            str(settings.get("smtp_port", "587"))
        )
        self.smtp_user_var.set(
            settings.get("smtp_user", "")
        )
        self.smtp_password_var.set(
            settings.get("smtp_password", "")
        )
        self.smtp_tls_var.set(
            bool(settings.get("smtp_tls", True))
        )
        self.api_base_url_var.set(
            self.normalize_server_url(settings.get("api_base_url", ""))
        )

    def save_alert_settings(self):

        scheduled_time = self.scheduled_time_var.get().strip()

        if scheduled_time:
            try:
                datetime.strptime(scheduled_time, "%H:%M")
            except ValueError:
                messagebox.showerror(
                    "알림 설정",
                    "예약 시간은 HH:MM 형식으로 입력하세요."
                )
                return

        api_base_url = self.normalize_server_url(self.api_base_url_var.get())
        self.api_base_url_var.set(api_base_url)

        try:
            auto_refresh_interval = int(
                float(self.auto_refresh_interval_var.get().strip())
            )
        except ValueError:
            messagebox.showerror(
                "자동 새로고침 설정",
                "자동 새로고침 시간은 숫자로 입력하세요."
            )
            return

        if auto_refresh_interval < 1:
            messagebox.showerror(
                "자동 새로고침 설정",
                "자동 새로고침 시간은 1분 이상이어야 합니다."
            )
            return

        self.auto_refresh_interval_var.set(str(auto_refresh_interval))

        if api_base_url and not api_base_url.startswith(("http://", "https://")):
            messagebox.showerror(
                "서버 설정",
                "분석 서버 URL은 https:// 로 시작해야 합니다."
            )
            return

        settings = {
            "alert_enabled": self.alert_enabled_var.get(),
            "alert_popup": self.alert_popup_var.get(),
            "alert_email": self.alert_email_var.get(),
            "alert_threshold": self.alert_threshold_var.get(),
            "scheduled_email": self.scheduled_email_var.get(),
            "scheduled_time": scheduled_time,
            "auto_refresh_interval_minutes": auto_refresh_interval,
            "alert_recipient": self.alert_recipient_var.get().strip(),
            "smtp_host": self.smtp_host_var.get().strip(),
            "smtp_port": self.smtp_port_var.get().strip(),
            "smtp_user": self.smtp_user_var.get().strip(),
            "smtp_password": self.smtp_password_var.get(),
            "smtp_tls": self.smtp_tls_var.get(),
            "api_base_url": api_base_url,
        }

        try:
            self.alert_settings_file.write_text(
                json.dumps(
                    settings,
                    ensure_ascii=False,
                    indent=4
                ),
                encoding="utf-8"
            )
        except Exception as e:
            messagebox.showerror(
                "알림 설정 저장 실패",
                str(e)
            )
            return

        self.log_alert("알림 설정 저장 완료")
        self.start_server_prewarm()
        messagebox.showinfo(
            "알림 설정",
            "알림 설정을 저장했습니다."
        )

    def get_alert_threshold(self):

        try:
            return float(self.alert_threshold_var.get())
        except ValueError:
            return 75.0

    def remote_client(self):

        return RemoteAnalysisClient(self.api_base_url_var.get().strip())

    def get_auto_refresh_interval_ms(self):

        try:
            minutes = int(float(self.auto_refresh_interval_var.get().strip()))
        except ValueError:
            minutes = 20

        return max(minutes, 1) * 60 * 1000

    def cached_price_summary(self, code):

        cached = self.service._cache_get(
            self.service.price_summary_cache,
            code,
            self.service.price_summary_cache_ttl
        )

        if cached is not None:
            return cached

        preset = self.get_weight_preset()
        result = self.service.analysis_cache.get(
            (
                code,
                "2025",
                "11011",
                preset
            )
        )

        if result is not None:
            return {
                "price": safe_number(getattr(result, "price", 0)),
                "change": safe_number(getattr(result, "change_rate", 0)),
                "currency": getattr(result, "currency", "KRW"),
                "price_date": getattr(result, "price_date", ""),
            }

        return {
            "price": 0,
            "change": 0,
            "currency": "KRW",
            "price_date": "",
        }

    def cached_briefing_metrics(self, code):

        summary = self.cached_price_summary(code)

        return {
            "price": safe_number(summary.get("price", 0)),
            "change_1d": safe_number(summary.get("change", 0)),
            "change_1m": 0,
            "change_3m": 0,
            "currency": summary.get("currency", "KRW"),
            "price_date": summary.get("price_date", ""),
        }

    def normalize_server_url(self, value):

        value = str(value or "").strip().rstrip("/")

        if not value or value == "https://stock-z1su.onrender.com":
            return DEFAULT_ANALYSIS_SERVER_URL

        return value

    def start_server_prewarm(self):

        client = self.remote_client()

        if not client.enabled:
            return

        thread = threading.Thread(
            target=self.server_prewarm_worker,
            args=(client,),
            daemon=True
        )
        thread.start()

    def server_prewarm_worker(self, client):

        try:
            client.health()
            self.root.after(
                0,
                lambda: self.status_var.set("분석 서버 준비 완료")
            )
        except Exception:
            pass

    def show_server_connecting(self, label="서버"):

        self.root.after(
            0,
            lambda: self.status_var.set(
                f"{label} 접속 중... 분석 서버를 준비하는 중입니다."
            )
        )

    def analyze_remote_records(self, stocks, preset):

        missing_stocks = []

        for stock in stocks:
            code = StockResolver.normalize_code(stock.get("code", ""))

            if not code:
                continue

            cache_key = (code, "2025", "11011", preset)

            if self.service.analysis_cache.get(cache_key) is None:
                copied = dict(stock)
                copied["code"] = code
                missing_stocks.append(copied)

        if not missing_stocks:
            return []

        records = self.remote_client().build_records(
            missing_stocks,
            holdings=self.holdings,
            preset=preset,
            analyze=True,
            max_workers=6,
        )

        for record in records:
            result = self.result_from_remote_record(record, preset)
            self.service.analysis_cache[
                (
                    result.code,
                    "2025",
                    "11011",
                    preset
                )
            ] = result

        return records

    def analyze_one_remote(self, code, name, preset):

        normalized_code = StockResolver.normalize_code(code)
        cache_key = (normalized_code, "2025", "11011", preset)
        cached = self.service.analysis_cache.get(cache_key)

        if cached is not None:
            self.root.after(
                0,
                lambda: self.status_var.set("캐시된 분석 결과 사용")
            )
            return cached

        records = self.analyze_remote_records(
            [{"code": normalized_code, "name": name or normalized_code}],
            preset
        )

        for record in records:
            if str(record.get("code", "")).upper() == str(normalized_code).upper():
                return self.result_from_remote_record(record, preset)

        return None

    def result_from_remote_record(self, record, preset):

        finance = record.get("finance") or {}
        factor_scores = record.get("factor_scores") or {}
        news_score = safe_number(record.get("news_score", 50))
        raw_news = ((news_score / 100) * 40) - 20
        score_breakdown = [
            {
                "name": name.title(),
                "raw_score": safe_number(score),
                "original_score": safe_number(score),
                "weight": {
                    "value": 0.20,
                    "quality": 0.25,
                    "growth": 0.20,
                    "stability": 0.15,
                    "momentum": 0.15,
                    "dividend": 0.05,
                }.get(name, 0),
                "contribution": round(
                    safe_number(score)
                    * {
                        "value": 0.20,
                        "quality": 0.25,
                        "growth": 0.20,
                        "stability": 0.15,
                        "momentum": 0.15,
                        "dividend": 0.05,
                    }.get(name, 0),
                    2,
                ),
                "reasons": [],
            }
            for name, score in factor_scores.items()
        ]

        fields = {
            "code": str(record.get("code", "")).upper(),
            "name": record.get("name") or record.get("code", ""),
            "score": safe_number(record.get("final_score", 0)),
            "signal": record.get("signal") or record.get("grade") or "-",
            "value": safe_number(factor_scores.get("value", 0)),
            "quality": safe_number(factor_scores.get("quality", 0)),
            "growth": safe_number(factor_scores.get("growth", 0)),
            "stability": safe_number(factor_scores.get("stability", 0)),
            "dividend": safe_number(factor_scores.get("dividend", 0)),
            "momentum": safe_number(factor_scores.get("momentum", 0)),
            "roe": safe_number(finance.get("roe", 0)),
            "debt_ratio": safe_number(finance.get("debt_ratio", 0)),
            "net_income": safe_number(finance.get("net_income", 0)),
            "price": safe_number(record.get("price", 0)),
            "change_rate": safe_number(record.get("change_1d", 0)),
            "per": safe_number(finance.get("per", 0)),
            "pbr": safe_number(finance.get("pbr", 0)),
            "psr": safe_number(finance.get("psr", 0)),
            "pcr": safe_number(finance.get("pcr", 0)),
            "market_cap": safe_number(finance.get("market_cap", 0)),
            "sales": safe_number(finance.get("sales", 0)),
            "operating_profit": safe_number(finance.get("operating_profit", 0)),
            "assets": safe_number(finance.get("assets", 0)),
            "liabilities": safe_number(finance.get("liabilities", 0)),
            "equity": safe_number(finance.get("equity", 0)),
            "eps": safe_number(finance.get("eps", 0)),
            "bps": safe_number(finance.get("bps", 0)),
            "roa": safe_number(finance.get("roa", 0)),
            "operating_margin": safe_number(finance.get("operating_margin", 0)),
            "net_margin": safe_number(finance.get("net_margin", 0)),
            "dividend_yield": safe_number(finance.get("dividend_yield", 0)),
            "current_ratio": safe_number(finance.get("current_ratio", 0)),
            "free_cash_flow": safe_number(finance.get("free_cash_flow", 0)),
            "operating_cash_flow": safe_number(finance.get("operating_cash_flow", 0)),
            "capex": safe_number(finance.get("capex", 0)),
            "cash": safe_number(finance.get("cash", 0)),
            "total_debt": safe_number(finance.get("total_debt", 0)),
            "roic": safe_number(finance.get("roic", 0)),
            "fcf_yield": safe_number(finance.get("fcf_yield", 0)),
            "sales_growth": safe_number(finance.get("sales_growth", 0)),
            "op_growth": safe_number(finance.get("op_growth", 0)),
            "eps_growth": safe_number(finance.get("eps_growth", 0)),
            "bps_growth": safe_number(finance.get("bps_growth", 0)),
            "relative_per": safe_number(finance.get("relative_per", 0)),
            "relative_pbr": safe_number(finance.get("relative_pbr", 0)),
            "ma20": safe_number(finance.get("ma20", 0)),
            "ma60": safe_number(finance.get("ma60", 0)),
            "ma120": safe_number(finance.get("ma120", 0)),
            "high52": safe_number(finance.get("high52", 0)),
            "low52": safe_number(finance.get("low52", 0)),
            "volume_ratio": safe_number(finance.get("volume_ratio", 0)),
            "short_ratio": safe_number(finance.get("short_ratio", 0)),
            "foreign_net_buy": safe_number(finance.get("foreign_net_buy", 0)),
            "institution_net_buy": safe_number(finance.get("institution_net_buy", 0)),
            "comment": record.get("comment", ""),
            "asset_type": record.get("asset_type", "STOCK"),
            "is_etf": record.get("asset_type") == "ETF",
            "news": raw_news,
            "currency": record.get("currency", "KRW"),
            "price_date": record.get("price_date", ""),
            "analyst_target_mean": safe_number(record.get("target_price", 0)),
            "analyst_target_high": safe_number(record.get("analyst_target_high", 0)),
            "analyst_target_low": safe_number(record.get("analyst_target_low", 0)),
            "analyst_recommendation": record.get("analyst", ""),
            "score_breakdown": score_breakdown,
            "factor_scores": factor_scores,
            "score_reason": record.get("score_reason", ""),
            "score_adjustments": record.get("score_adjustments", []),
            "buy_reason": record.get("buy_reason", ""),
            "risk_factors": record.get("risk_factors", ""),
            "stop_loss_basis": record.get("stop_loss_basis", ""),
            "add_buy_basis": record.get("add_buy_basis", ""),
            "hold_reason": record.get("hold_reason", ""),
            "next_check_date": record.get("next_check_date", ""),
            "daily_status": record.get("daily_status", ""),
            "daily_core": record.get("daily_core", ""),
            "daily_judgment": record.get("daily_judgment", ""),
            "preset": preset,
            "remote_record": record,
            "remote_source": True,
        }

        for key, value in finance.items():
            fields.setdefault(key, safe_number(value))

        return SimpleNamespace(**fields)

    def get_alert_rules(self):

        return AlertRules(
            score=self.get_alert_threshold(),
            change=5,
            upside=30,
            loss=-10,
            bad_news=35,
        )

    def build_alert_record(self, result):

        quant_score = self.quant_average_score(result)
        news_score = self.news_normalized_score(result)
        final_score = round((quant_score * 0.7) + (news_score * 0.3), 1)
        price = safe_number(getattr(result, "price", 0))
        target_price = safe_number(
            getattr(result, "analyst_target_mean", 0)
            or getattr(result, "target_price", 0)
        )
        target_upside = (
            ((target_price - price) / price) * 100
            if price > 0 and target_price > 0
            else 0
        )

        news = []
        remote_record = getattr(result, "remote_record", None)

        if isinstance(remote_record, dict):
            news = remote_record.get("news", [])[:3]

        return {
            "code": result.code,
            "name": result.name,
            "final_score": final_score,
            "change_1d": safe_number(getattr(result, "change_rate", 0)),
            "news_score": news_score,
            "target_price": target_price,
            "target_upside": target_upside,
            "price": price,
            "volume_ratio": safe_number(getattr(result, "volume_ratio", 0)),
            "news": news,
        }

    def handle_analysis_alert(self, result):

        if not self.alert_enabled_var.get():
            return

        alerts = AlertEngine(self.get_alert_rules()).build_alerts(
            [self.build_alert_record(result)],
            holdings=self.holdings,
            alert_history=self.alert_history,
        )

        if not alerts:
            return

        message_lines = [
            f"{result.name} ({result.code})",
            f"판정 {result.signal}",
            "",
        ]

        for alert in alerts[:5]:
            message_lines.append(
                f"- {alert['title']}: {alert['message']}"
            )

        if len(alerts) > 5:
            message_lines.append(f"- 외 {len(alerts) - 5}건")

        message = "\n".join(message_lines)
        self.log_alert(message.replace("\n", " / "))

        if self.alert_popup_var.get():
            messagebox.showinfo(
                "조건 알림",
                message
            )

        if self.alert_email_var.get():
            self.send_report_email_async(
                result,
                subject=(
                    f"[Morning Stock] {alerts[0]['title']} "
                    f"{result.name}"
                )
            )

    def send_test_email(self):

        self.save_alert_settings()
        subject = "[Morning Stock] 테스트 메일"
        body = "\n".join([
            "Morning Stock Assistant Pro 테스트 메일입니다.",
            f"발송시각: {datetime.now():%Y-%m-%d %H:%M:%S}",
        ])
        self.send_email_async(subject, body)

    def send_current_report_email(self):

        if self.current_result is None:
            messagebox.showinfo(
                "메일 전송",
                "먼저 종목을 분석한 뒤 전송하세요."
            )
            return

        self.save_alert_settings()
        self.send_report_email_async(
            self.current_result,
            subject=(
                f"[Morning Stock] {self.current_result.name} "
                f"분석 리포트"
            )
        )

    def check_scheduled_email(self):

        try:
            self.run_scheduled_email_if_due()
        except Exception as e:
            self.log_alert(f"예약 메일 확인 오류: {e}")

        self.root.after(60000, self.check_scheduled_email)

    def run_scheduled_email_if_due(self):

        if not self.scheduled_email_var.get():
            return

        scheduled_time = self.scheduled_time_var.get().strip()

        try:
            target = datetime.strptime(
                scheduled_time,
                "%H:%M"
            ).time()
        except ValueError:
            self.log_alert("예약 시간 형식은 HH:MM으로 입력하세요.")
            return

        now = datetime.now()

        if now.hour != target.hour or now.minute != target.minute:
            return

        today = now.strftime("%Y-%m-%d")

        if self.last_scheduled_email_date == today:
            return

        self.last_scheduled_email_date = today
        self.send_scheduled_summary_email()

    def send_scheduled_summary_email(self):

        if self.current_group is None:
            self.log_alert("예약 메일 생략: 선택된 관심종목 그룹 없음")
            return

        self.save_alert_settings()
        preset = self.get_weight_preset()
        subject = (
            f"[Morning Stock] {self.current_group} "
            f"예약 리포트 {datetime.now():%Y-%m-%d}"
        )
        body = self.build_group_summary_report(
            self.current_group,
            preset
        )
        self.send_email_async(subject, body)

    def build_group_summary_report(self, group_name, preset):

        return self.build_ai_quant_briefing(
            group_name,
            preset,
            analyze_missing=True
        )

    def send_report_email_async(self, result, subject):

        body = self.build_report_text(
            result,
            datetime.now()
        )
        self.send_email_async(subject, body)

    def send_email_async(self, subject, body):

        recipient = self.alert_recipient_var.get().strip()
        smtp_user = self.smtp_user_var.get().strip()

        if not recipient or not smtp_user:
            messagebox.showwarning(
                "메일 설정",
                "받는 메일과 보내는 계정을 입력하세요."
            )
            return

        self.log_alert("메일 전송 준비 중...")

        thread = threading.Thread(
            target=self.send_email_worker,
            args=(subject, body),
            daemon=True
        )
        thread.start()

    def send_email_worker(self, subject, body):

        try:
            self._send_email(subject, body)
        except Exception as e:
            self.root.after(
                0,
                lambda error=e: self.on_email_failed(error)
            )
            return

        self.root.after(
            0,
            self.on_email_sent
        )

    def _send_email(self, subject, body):

        host = self.smtp_host_var.get().strip()
        port = int(self.smtp_port_var.get().strip() or "587")
        smtp_user = self.smtp_user_var.get().strip()
        password = self.smtp_password_var.get()
        recipient = self.alert_recipient_var.get().strip()

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = smtp_user
        message["To"] = recipient
        message.set_content(body)

        if self.smtp_tls_var.get():
            context = ssl.create_default_context()

            with smtplib.SMTP(host, port, timeout=20) as server:
                server.starttls(context=context)
                server.login(smtp_user, password)
                server.send_message(message)
        else:
            with smtplib.SMTP_SSL(host, port, timeout=20) as server:
                server.login(smtp_user, password)
                server.send_message(message)

    def on_email_sent(self):

        self.log_alert("메일 전송 완료")
        self.status_var.set("메일 전송 완료")

    def on_email_failed(self, error):

        self.log_alert(f"메일 전송 실패: {error}")
        messagebox.showerror(
            "메일 전송 실패",
            str(error)
        )

    def log_alert(self, message):

        timestamp = datetime.now().strftime("%H:%M:%S")

        if hasattr(self, "alert_log"):
            self.alert_log.insert(
                tk.END,
                f"[{timestamp}] {message}\n"
            )
            self.alert_log.see(tk.END)

        self.status_var.set(message)

    def set_chart_period(self, period, interval="1d", label=None):

        self.chart_period_var.set(period)
        self.chart_interval_var.set(interval)
        self.chart_label_var.set(label or period)
        self.draw_chart()

    def on_currency_display_change(self):

        rate = self.get_usd_krw_rate() if self.us_price_krw_var.get() else None

        if hasattr(self, "usd_krw_label"):
            if self.us_price_krw_var.get() and rate:
                self.usd_krw_label.config(text=f"환율: 1달러 = {rate:,.2f}원")
            elif self.us_price_krw_var.get():
                self.usd_krw_label.config(text="환율: 가져오기 실패")
            else:
                self.usd_krw_label.config(text="환율: 자동")

        self.refresh_stock_list(refresh_compare=False)

        if self.current_result is not None:
            self.show_result(self.current_result)

        if hasattr(self, "compare_tree"):
            self.refresh_comparison_table(auto_analyze=False)

        if hasattr(self, "portfolio_tree"):
            self.refresh_portfolio_table(auto_analyze=False)

        self.draw_chart()

    def get_usd_krw_rate(self):

        now = datetime.now()

        if (
            self.usd_krw_rate
            and self.usd_krw_rate_time
            and (now - self.usd_krw_rate_time).total_seconds() < 1800
        ):
            return self.usd_krw_rate

        try:
            data = self.service.price.get_price("USDKRW=X")
            rate = safe_number(data.get("price") if data else 0)
        except Exception:
            rate = 0

        if rate > 0:
            self.usd_krw_rate = rate
            self.usd_krw_rate_time = now
            return rate

        return self.usd_krw_rate

    def should_show_usd_as_krw(self, currency):

        return self.us_price_krw_var.get() and currency == "USD"

    def format_display_price(self, price, currency="KRW", compact=False):

        price = safe_number(price)

        if self.should_show_usd_as_krw(currency):
            rate = self.get_usd_krw_rate()

            if rate:
                converted = price * rate

                if compact:
                    return f"{converted:,.0f}원"

                return f"{converted:,.0f}원 (${price:,.2f})"

        return format_price(price, currency)

    def chart_display_series(self, close):

        self.chart_hover_currency = "KRW"

        if close is None or close.empty:
            return close

        if (
            self.current_stock
            and not self.current_stock.isdigit()
            and self.us_price_krw_var.get()
        ):
            rate = self.get_usd_krw_rate()

            if rate:
                self.chart_hover_currency = "KRW"
                return close * rate

            self.chart_hover_currency = "USD"
            return close

        self.chart_hover_currency = "USD" if self.current_stock and not self.current_stock.isdigit() else "KRW"
        return close

    @staticmethod
    def quant_average_score(result):
        return SharedAnalysisBridge.quant_average_score(result)

    @staticmethod
    def factor_score_value(result, name):
        factor_scores = getattr(result, "factor_scores", None)

        if not factor_scores:
            factor_scores = SharedAnalysisBridge.factor_scores(result)

        return safe_number(factor_scores.get(name, 0))

    def investment_plan_lines(
        self,
        result,
        quant_score=None,
        news_score=None,
        final_score=None,
    ):
        quant_score = (
            self.quant_average_score(result)
            if quant_score is None
            else safe_number(quant_score)
        )
        news_score = (
            self.news_normalized_score(result)
            if news_score is None
            else safe_number(news_score)
        )
        final_score = (
            round((quant_score * 0.7) + (news_score * 0.3), 1)
            if final_score is None
            else safe_number(final_score)
        )
        target = safe_number(
            getattr(result, "analyst_target_mean", 0)
            or getattr(result, "target_price", 0)
        )
        price = safe_number(getattr(result, "price", 0))
        target_upside = (
            ((target - price) / price) * 100
            if target > 0 and price > 0
            else safe_number(getattr(result, "target_upside", 0))
        )
        target_text = (
            f"{self.format_display_price(target, getattr(result, 'currency', 'KRW'), compact=True)}"
            f" ({target_upside:+.1f}%)"
            if target > 0
            else "목표가 데이터 없음"
        )

        action_plan = {
            "buy_reason": getattr(result, "buy_reason", ""),
            "risk_factors": getattr(result, "risk_factors", ""),
            "stop_loss_basis": getattr(result, "stop_loss_basis", ""),
            "add_buy_basis": getattr(result, "add_buy_basis", ""),
            "hold_reason": getattr(result, "hold_reason", ""),
            "next_check_date": getattr(result, "next_check_date", ""),
        }

        if not all(action_plan.values()):
            holding = self.holdings.get(str(getattr(result, "code", "")).upper(), {})
            action_plan.update(
                SharedAnalysisBridge.action_plan(
                    result=result,
                    price=price,
                    target_price=target,
                    target_upside=target_upside,
                    quant_score=quant_score,
                    news_score=news_score,
                    final_score=final_score,
                    factor_scores=SharedAnalysisBridge.factor_scores(result),
                    holding=holding,
                )
            )

        return [
            f"매수 이유     : {action_plan['buy_reason']}",
            f"위험 요소     : {action_plan['risk_factors']}",
            f"목표가        : {target_text}",
            f"손절 기준     : {action_plan['stop_loss_basis']}",
            f"추가 매수 기준: {action_plan['add_buy_basis']}",
            f"보유 이유     : {action_plan['hold_reason']}",
            f"다음 확인 날짜: {action_plan['next_check_date']}",
        ]

    def daily_status(self, result, final_score):
        value = getattr(result, "daily_status", "")

        if value:
            return value

        if final_score >= 85:
            return "강한 관심"
        if final_score >= 72:
            return "관심"
        if final_score >= 55:
            return "관망"
        if final_score >= 40:
            return "주의"
        return "위험"

    def daily_core(self, result):
        value = getattr(result, "daily_core", "")

        if value:
            return value

        news = []
        remote_record = getattr(result, "remote_record", None)

        if isinstance(remote_record, dict):
            news = remote_record.get("news", [])[:3]

        snapshot = SharedAnalysisBridge.daily_snapshot(
            result=result,
            metrics={
                "change_1d": safe_number(getattr(result, "change_rate", 0)),
                "change_1m": 0,
            },
            news_items=news,
            final_score=safe_number(getattr(result, "score", 0)),
            news_score=self.news_normalized_score(result),
        )
        return snapshot["daily_core"]

    def daily_judgment(self, result, final_score):
        value = getattr(result, "daily_judgment", "")

        if value:
            return value

        return SharedAnalysisBridge.daily_snapshot(
            result=result,
            metrics={},
            news_items=[],
            final_score=final_score,
            news_score=self.news_normalized_score(result),
        )["daily_judgment"]

    @staticmethod
    def news_normalized_score(result):

        raw_news = safe_number(getattr(result, "news", 0))
        raw_news = max(min(raw_news, 20), -20)
        return ((raw_news + 20) / 40) * 100

    def chart_line_color(self, change):

        return "#ef4444" if change >= 0 else "#2563eb"

    def apply_toss_chart_style(self):

        self.figure.patch.set_facecolor("#ffffff")
        self.ax.set_facecolor("#ffffff")

        for side in ("top", "right", "left", "bottom"):
            self.ax.spines[side].set_visible(False)

        self.ax.grid(
            True,
            axis="y",
            color="#edf1f5",
            linestyle="-",
            linewidth=0.8
        )
        self.ax.grid(False, axis="x")
        self.ax.tick_params(
            axis="both",
            colors="#94a3b8",
            labelsize=8,
            length=0
        )
        self.ax.yaxis.tick_right()
        self.ax.yaxis.set_label_position("right")
        self.ax.set_xlabel("")
        self.ax.set_ylabel("")

    def update_chart_summary(
        self,
        last,
        first,
        high,
        low,
        change,
        period_label
    ):

        currency = self.chart_hover_currency
        price_text = format_price(last, currency)
        diff = last - first
        diff_text = format_price(abs(diff), currency)
        sign = "+" if diff >= 0 else "-"
        self.chart_summary_var.set(
            f"{self.current_stock}  {price_text}  "
            f"{change:+.2f}%  ({sign}{diff_text})  "
            f"{period_label}  고가 {format_price(high, currency)} / "
            f"저가 {format_price(low, currency)}"
        )

    def plot_toss_price_line(self, index, close, line_color):

        self.ax.plot(
            index,
            close,
            color=line_color,
            linewidth=2.6,
            solid_capstyle="round",
            solid_joinstyle="round",
            zorder=3
        )

        try:
            baseline = float(close.iloc[0])
            self.ax.fill_between(
                index,
                close,
                baseline,
                color=line_color,
                alpha=0.08,
                linewidth=0,
                zorder=1
            )
        except Exception:
            pass

        self.ax.scatter(
            [index[-1]],
            [float(close.iloc[-1])],
            color=line_color,
            s=34,
            zorder=4,
            edgecolors="#ffffff",
            linewidths=1.5
        )

    def format_chart_xticks(self, close):

        if close is None or close.empty:
            return

        try:
            span = close.index[-1] - close.index[0]
            days = getattr(span, "days", 0)
        except Exception:
            days = 365

        if days <= 2:
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        elif days <= 120:
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        else:
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter("%y.%m"))

        self.figure.autofmt_xdate(rotation=0, ha="center")

    def setup_chart_interaction(self):

        if (
            self.chart_motion_cid is not None
            and self.chart_event_canvas is self.canvas
        ):
            return

        self.chart_event_canvas = self.canvas
        self.chart_motion_cid = self.canvas.mpl_connect(
            "motion_notify_event",
            self.on_chart_mouse_move
        )

    def prepare_chart_hover(self, close):

        self.chart_hover_data = []
        self.chart_hover_annotation = None

        if close is None or close.empty:
            return

        for index, value in close.dropna().items():
            try:
                self.chart_hover_data.append((
                    mdates.date2num(index),
                    index,
                    float(value)
                ))
            except Exception:
                continue

        if not self.chart_hover_data:
            return

        self.chart_hover_annotation = self.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(12, 14),
            textcoords="offset points",
            bbox={
                "boxstyle": "round,pad=0.35",
                "fc": self.colors["panel"],
                "ec": self.colors["accent"],
                "alpha": 0.95,
            },
            arrowprops={"arrowstyle": "->", "color": self.colors["accent"]},
            color=self.colors["text"],
            fontsize=8,
            visible=False,
        )
        self.chart_hover_line = self.ax.axvline(
            self.chart_hover_data[-1][1],
            color="#cbd5e1",
            linewidth=1.0,
            alpha=0.0,
            zorder=2
        )

    def on_chart_mouse_move(self, event):

        annotation = self.chart_hover_annotation
        hover_line = self.chart_hover_line

        if (
            annotation is None
            or event.inaxes != self.ax
            or event.xdata is None
            or not self.chart_hover_data
        ):
            if annotation is not None and annotation.get_visible():
                annotation.set_visible(False)
                if hover_line is not None:
                    hover_line.set_alpha(0.0)
                self.canvas.draw_idle()
            return

        nearest = min(
            self.chart_hover_data,
            key=lambda item: abs(item[0] - event.xdata)
        )
        x_num, index, price = nearest

        try:
            span = self.chart_hover_data[-1][0] - self.chart_hover_data[0][0]
            date_format = "%H:%M:%S" if span <= 2 else "%Y-%m-%d"
            label_time = index.strftime(date_format)
        except Exception:
            label_time = str(index)

        annotation.xy = (x_num, price)
        annotation.set_text(
            f"{label_time}\n"
            f"{format_price(price, self.chart_hover_currency)}"
        )
        annotation.set_visible(True)
        if hover_line is not None:
            hover_line.set_xdata([index, index])
            hover_line.set_alpha(0.9)
        self.canvas.draw_idle()

    def apply_price_axis_padding(self, close):

        if close is None or close.empty:
            return

        high = float(close.max())
        low = float(close.min())

        if high == low:
            margin = max(abs(high) * 0.001, 1)
        else:
            margin = (high - low) * 0.12

        self.ax.set_ylim(low - margin, high + margin)

    def draw_chart(self):

        if not self.current_stock:
            return

        period = self.chart_period_var.get() or "1y"
        interval = self.chart_interval_var.get() or "1d"

        if interval == "5s":
            self.draw_live_day_chart()
            return

        history = self.get_chart_history(
            self.current_stock,
            period,
            interval
        )

        if history is None:
            return

        history = history.dropna(subset=["Close"])

        if history.empty:
            return

        self.ax.clear()
        self.apply_toss_chart_style()

        close = self.chart_display_series(history["Close"])
        first = float(close.iloc[0])
        last = float(close.iloc[-1])
        change = ((last - first) / first) * 100 if first > 0 else 0
        line_color = self.chart_line_color(change)

        self.plot_toss_price_line(history.index, close, line_color)

        is_intraday = interval != "1d"
        show_ma = self.chart_show_ma_var.get()

        if show_ma and not is_intraday and "MA20" in history.columns:
            self.ax.plot(
                history.index,
                self.chart_display_series(history["MA20"]),
                label="MA20",
                color="#f59e0b",
                linewidth=1.0,
                alpha=0.65
            )

        if show_ma and not is_intraday and period in ("6mo", "1y") and "MA60" in history.columns:
            self.ax.plot(
                history.index,
                self.chart_display_series(history["MA60"]),
                label="MA60",
                color="#6366f1",
                linewidth=1.0,
                alpha=0.6
            )

        if show_ma and not is_intraday and period == "1y" and "MA120" in history.columns:
            self.ax.plot(
                history.index,
                self.chart_display_series(history["MA120"]),
                label="MA120",
                color="#94a3b8",
                linewidth=1.0,
                alpha=0.55
            )

        high = float(close.max())
        low = float(close.min())
        self.ax.axhline(
            last,
            color="#e2e8f0",
            linestyle="--",
            linewidth=0.9,
            zorder=0
        )

        period_label = self.chart_label_var.get() or period
        interval_label = {
            "1d": "1일 단위",
            "1wk": "1주 단위",
            "2wk": "2주 단위",
            "1mo": "1개월 단위",
        }.get(interval, f"{interval} 단위")
        self.ax.text(
            0.01,
            0.97,
            f"{period_label} · {interval_label}",
            transform=self.ax.transAxes,
            ha="left",
            va="top",
            color="#64748b",
            fontsize=9,
            fontweight="bold"
        )
        handles, labels = self.ax.get_legend_handles_labels()
        if show_ma and handles and labels:
            self.ax.legend(
                handles,
                labels,
                loc="upper left",
                bbox_to_anchor=(0.0, 0.90),
                frameon=False,
                fontsize=8
            )
        self.ax.text(
            0.99,
            0.97,
            format_price(last, self.chart_hover_currency),
            transform=self.ax.transAxes,
            ha="right",
            va="top",
            color=line_color,
            fontsize=13,
            fontweight="bold"
        )

        self.apply_price_axis_padding(close)
        self.format_chart_xticks(close)
        self.update_chart_summary(
            last,
            first,
            high,
            low,
            change,
            period_label
        )
        self.prepare_chart_hover(close)
        self.figure.tight_layout(pad=1.4)
        self.canvas.draw()

    def get_chart_history(self, stock_code, period, interval):

        source_interval = interval
        history = self.service.price.get_history(
            stock_code,
            period=period,
            interval=source_interval
        )

        if history is None and source_interval != "1d":
            history = self.service.price.get_history(
                stock_code,
                period=period,
                interval="1d"
            )

        if history is None:
            return None

        if interval == "1d":
            return history

        rule = {
            "1wk": "W",
            "2wk": "2W",
            "1mo": "M",
        }.get(interval)

        if not rule:
            return history

        try:
            resampled = history.resample(rule).agg({
                "Open": "first",
                "High": "max",
                "Low": "min",
                "Close": "last",
                "Volume": "sum",
            }).dropna(subset=["Close"])
            resampled["MA20"] = resampled["Close"].rolling(20).mean()
            resampled["MA60"] = resampled["Close"].rolling(60).mean()
            resampled["MA120"] = resampled["Close"].rolling(120).mean()
            return resampled
        except Exception:
            return history

    def draw_live_day_chart(self):

        code = self.current_stock
        sample = self.get_live_chart_sample(code)

        if sample is None:
            return

        self.draw_chart_series(
            sample,
            label="일일",
            interval_label="5초",
            show_moving_average=False
        )

        if self.chart_live_job is not None:
            try:
                self.root.after_cancel(self.chart_live_job)
            except Exception:
                pass

        self.chart_live_job = self.root.after(
            5000,
            self.refresh_live_chart
        )

    def refresh_live_chart(self):

        self.chart_live_job = None

        if self.chart_interval_var.get() == "5s" and self.current_stock:
            self.draw_chart()

    def get_live_chart_sample(self, code):

        samples = self.chart_live_samples.setdefault(code, [])

        if not samples:
            self.seed_live_chart_samples(code, samples)

        try:
            price_data = self.service.price.get_price(code)
            price = safe_number(
                price_data.get("price")
                if price_data
                else 0
            )
        except Exception:
            price = 0

        if price <= 0:
            return None

        now = datetime.now()
        samples.append((now, price))
        cutoff = now - timedelta(days=1)
        self.chart_live_samples[code] = [
            item
            for item in samples
            if item[0] >= cutoff
        ]

        import pandas as pd

        return pd.Series(
            [item[1] for item in self.chart_live_samples[code]],
            index=[item[0] for item in self.chart_live_samples[code]],
            name="Close"
        )

    def seed_live_chart_samples(self, code, samples):

        try:
            history = self.service.price.get_history(
                code,
                period="1d",
                interval="1m"
            )
        except Exception:
            history = None

        if history is None or history.empty or "Close" not in history:
            return

        close = history["Close"].dropna().tail(390)

        for index, price in close.items():
            try:
                if hasattr(index, "to_pydatetime"):
                    index = index.to_pydatetime()

                if getattr(index, "tzinfo", None) is not None:
                    index = index.replace(tzinfo=None)

                value = safe_number(price)

                if value > 0:
                    samples.append((index, value))
            except Exception:
                continue

    def draw_chart_series(
        self,
        close,
        label,
        interval_label,
        show_moving_average=True
    ):

        if close is None or close.empty:
            return

        close = self.chart_display_series(close)

        self.ax.clear()
        self.apply_toss_chart_style()

        first = float(close.iloc[0])
        last = float(close.iloc[-1])
        change = ((last - first) / first) * 100 if first > 0 else 0
        line_color = self.chart_line_color(change)
        self.plot_toss_price_line(close.index, close, line_color)

        high = float(close.max())
        low = float(close.min())
        self.ax.axhline(
            last,
            color="#e2e8f0",
            linestyle="--",
            linewidth=0.9,
            zorder=0
        )
        self.ax.set_title(
            "",
        )
        self.ax.text(
            0.01,
            0.97,
            f"{label} · {interval_label} 단위",
            transform=self.ax.transAxes,
            ha="left",
            va="top",
            color="#64748b",
            fontsize=9,
            fontweight="bold"
        )
        self.ax.text(
            0.99,
            0.97,
            format_price(last, self.chart_hover_currency),
            transform=self.ax.transAxes,
            ha="right",
            va="top",
            color=line_color,
            fontsize=13,
            fontweight="bold"
        )
        self.apply_price_axis_padding(close)
        self.format_chart_xticks(close)
        self.update_chart_summary(
            last,
            first,
            high,
            low,
            change,
            label
        )
        self.prepare_chart_hover(close)
        self.figure.tight_layout(pad=1.4)
        self.canvas.draw()

    def on_group_select(self, event):

        selection = self.group_list.curselection()

        if not selection:
            return

        self.current_group = self.group_list.get(selection[0])

        self.refresh_stock_list()
        self.refresh_portfolio_table(auto_analyze=False)
        self.refresh_dashboard()
        self.refresh_event_tab()
        self.refresh_strategy_tab()

    def on_stock_select(self, event):

        selection = self.stock_list.curselection()

        if not selection:
            return

        index = selection[0]

        if index >= len(self.display_stocks):
            return

        stock = self.display_stocks[index]

        self.current_stock = stock["code"]

        self.status_var.set(
            f"{stock['name']} 분석 중..."
        )

        self.analyze_stock()

    def load_groups(self):

        if not self.watchlist_file.exists():
            return

        with open(
            self.watchlist_file,
            "r",
            encoding="utf-8"
        ) as f:

            self.groups = json.load(f)

        self.group_list.delete(0, tk.END)

        for name in self.groups:
            self.group_list.insert(tk.END, name)

    def refresh_stock_list(self, refresh_compare=True):

        self.stock_list.delete(0, tk.END)

        self.display_stocks = []

        if self.current_group is None:
            return

        stocks = self.groups.get(self.current_group, [])

        display_items = []

        for stock in stocks:

            result = self.service.analysis_cache.get(
                (
                    stock["code"],
                    "2025",
                    "11011",
                    self.get_weight_preset()
                )
            )
            score = result.score if result else 0

            summary = self.cached_price_summary(stock["code"])
            price = safe_number(summary.get("price"))
            change = safe_number(summary.get("change"))
            currency = summary.get("currency", "KRW")

            if change > 0:
                arrow = "▲"
            elif change < 0:
                arrow = "▼"
            else:
                arrow = "-"

            text = (
                f"{stock['name']} ({stock['code']})   "
                f"{self.format_display_price(price, currency, compact=True)}   "
                f"{arrow}{abs(change):.2f}%   "
                f"⭐ {score:.1f}"
            )

            display_items.append({
                "text": text,
                "score": score,
                "stock": stock
            })

        display_items.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        for item in display_items:

            self.display_stocks.append(
                item["stock"]
            )

            self.stock_list.insert(
                tk.END,
                item["text"]
            )

        if refresh_compare:
            self.refresh_comparison_table()
            self.refresh_briefing_table()

    def refresh_comparison_table(self, auto_analyze=True):

        if not hasattr(self, "compare_tree"):
            return

        for item in self.compare_tree.get_children():
            self.compare_tree.delete(item)

        if self.current_group is None:
            if hasattr(self, "briefing_report_text"):
                self.briefing_report_text.delete("1.0", tk.END)
            return

        preset = self.get_weight_preset()
        stocks = self.groups.get(self.current_group, [])
        rows = []
        missing_stocks = []

        for stock in stocks:
            code = stock["code"]
            name = stock["name"]
            result = self.service.analysis_cache.get(
                (
                    code,
                    "2025",
                    "11011",
                    preset
                )
            )

            if result is None:
                missing_stocks.append(stock)

            summary = self.cached_price_summary(code)
            price = safe_number(summary.get("price"))
            change = safe_number(summary.get("change"))
            currency = summary.get("currency", "KRW")

            score = safe_number(
                getattr(result, "score", 0)
                if result
                else 0
            )
            quant_news_average = (
                (
                    self.quant_average_score(result)
                    + self.news_normalized_score(result)
                ) / 2
                if result
                else 0
            )
            rows.append({
                "code": code,
                "name": name,
                "score": score,
                "values": (
                    name,
                    code,
                    getattr(result, "asset_type", "STOCK") if result else "-",
                    f"{score:.1f}" if result else "분석 대기",
                    f"{quant_news_average:.1f}" if result else "분석 대기",
                    getattr(result, "signal", "-") if result else "분석 대기",
                    self.format_display_price(price, currency, compact=True),
                    f"{change:.2f}%",
                    self._comparison_number(
                        getattr(result, "per", None)
                    ),
                    self._comparison_number(
                        getattr(result, "pbr", None)
                    ),
                    self._comparison_number(
                        getattr(result, "pcr", None)
                    ),
                    self._comparison_number(
                        getattr(result, "psr", None)
                    ),
                    self._comparison_number(
                        getattr(result, "roe", None),
                        suffix="%"
                    ),
                    self._comparison_number(
                        getattr(result, "roic", None),
                        suffix="%"
                    ),
                    self._comparison_number(
                        getattr(result, "fcf_yield", None),
                        suffix="%"
                    ),
                    self._comparison_number(
                        getattr(result, "debt_ratio", None),
                        suffix="%"
                    ),
                    self._comparison_number(
                        getattr(result, "growth", None)
                    ),
                    self._comparison_number(
                        getattr(result, "short_ratio", None),
                        suffix="%"
                    ),
                    self.format_flow_value(
                        getattr(result, "foreign_net_buy", None)
                    ),
                    self.format_flow_value(
                        getattr(result, "institution_net_buy", None)
                    ),
                )
            })

        rows.sort(
            key=lambda item: item["score"],
            reverse=True
        )

        for index, row in enumerate(rows):
            self.compare_tree.insert(
                "",
                tk.END,
                iid=f"{row['code']}:{index}",
                values=row["values"],
                tags=(self.signal_tag(row["values"][5]),)
            )

        if (
            auto_analyze
            and missing_stocks
            and not self.compare_analysis_running
        ):
            self.start_compare_analysis(
                missing_stocks,
                preset
            )

    def start_compare_analysis(self, stocks, preset):

        self.compare_analysis_running = True
        self.status_var.set(
            f"비교표 분석 중... 0/{len(stocks)}"
        )

        thread = threading.Thread(
            target=self.compare_analysis_worker,
            args=(list(stocks), preset),
            daemon=True
        )
        thread.start()

    def compare_analysis_worker(self, stocks, preset):

        total = len(stocks)

        if self.remote_client().enabled:
            try:
                self.show_server_connecting("비교표 서버")
                self.analyze_remote_records(stocks, preset)
                self.root.after(
                    0,
                    self.finish_compare_analysis
                )
                return
            except Exception as e:
                print("비교표 서버 분석 오류, 로컬 분석으로 전환:", e)

        for index, stock in enumerate(stocks, start=1):
            try:
                self.analyzer.analyze(
                    stock["code"],
                    "2025",
                    "11011",
                    preset
                )
            except Exception as e:
                print("비교표 분석 오류:", stock.get("code"), e)

            self.root.after(
                0,
                lambda i=index, t=total:
                self.status_var.set(f"비교표 분석 중... {i}/{t}")
            )

        self.root.after(
            0,
            self.finish_compare_analysis
        )

    def finish_compare_analysis(self):

        self.compare_analysis_running = False
        self.refresh_stock_list(refresh_compare=False)
        self.refresh_comparison_table(auto_analyze=False)
        self.refresh_briefing_table()
        self.status_var.set("비교표 분석 완료")

    def _comparison_number(self, value, suffix=""):

        if value is None:
            return "-"

        return f"{safe_number(value):.2f}{suffix}"

    @staticmethod
    def format_flow_value(value):

        if value is None:
            return "-"

        value = safe_number(value)

        if value == 0:
            return "-"

        if abs(value) >= 100_000_000:
            return f"{value / 100_000_000:+,.1f}억"

        if abs(value) >= 10_000:
            return f"{value / 10_000:+,.0f}만"

        return f"{value:+,.0f}"

    def on_compare_select(self, event=None):

        if not hasattr(self, "compare_tree"):
            return

        selection = self.compare_tree.selection()

        if not selection:
            return

        values = self.compare_tree.item(
            selection[0],
            "values"
        )

        if len(values) < 2:
            return

        code = values[1]

        self.current_stock = code
        self.analyze_stock()

    def refresh_dashboard(self):

        if not hasattr(self, "dashboard_tree"):
            return

        for item in self.dashboard_tree.get_children():
            self.dashboard_tree.delete(item)

        group_name = self.current_group or "-"
        stocks = (
            self.groups.get(self.current_group, [])
            if self.current_group
            else []
        )
        preset = self.get_weight_preset()
        best_result = None
        total_market_value = 0
        rows = []

        for stock in stocks:
            code = stock["code"]
            result = self.service.analysis_cache.get(
                (
                    code,
                    "2025",
                    "11011",
                    preset
                )
            )

            summary = self.cached_price_summary(code)
            price = safe_number(summary.get("price"))
            change = safe_number(summary.get("change"))
            currency = summary.get("currency", "KRW")

            holding = self.holdings.get(code, {})
            quantity = safe_number(holding.get("quantity", 0))
            avg_price = safe_number(holding.get("avg_price", 0))
            market_value = quantity * price
            total_market_value += market_value
            pnl = (
                ((price - avg_price) / avg_price) * 100
                if quantity > 0 and avg_price > 0
                else 0
            )

            if result and (
                best_result is None
                or safe_number(result.score) > safe_number(best_result.score)
            ):
                best_result = result

            signal = getattr(result, "signal", "-") if result else "-"
            score = (
                f"{safe_number(result.score):.1f}"
                if result
                else "-"
            )
            feedback = (
                self._holding_feedback(
                    result,
                    quantity,
                    avg_price,
                    price,
                    pnl,
                    0,
                    0
                )
                if result
                else "분석 대기"
            )
            holding_text = (
                f"{quantity:g}주 {pnl:+.1f}%"
                if quantity > 0
                else "-"
            )

            rows.append({
                "code": code,
                "score": safe_number(getattr(result, "score", 0)),
                "signal": signal,
                "values": (
                    stock["name"],
                    code,
                    score,
                    signal,
                    self.format_display_price(price, currency, compact=True),
                    f"{change:+.2f}%",
                    holding_text,
                    feedback,
                )
            })

        rows.sort(
            key=lambda row: row["score"],
            reverse=True
        )

        for index, row in enumerate(rows):
            self.dashboard_tree.insert(
                "",
                tk.END,
                iid=f"dashboard:{row['code']}:{index}",
                values=row["values"],
                tags=(self.signal_tag(row["signal"]),)
            )

        self.dashboard_cards["group"].configure(text=group_name)
        self.dashboard_cards["count"].configure(text=f"{len(stocks)}개")
        self.dashboard_cards["best"].configure(
            text=(
                f"{best_result.name} {best_result.score:.1f}"
                if best_result
                else "-"
            )
        )
        self.dashboard_cards["holding"].configure(
            text=f"{total_market_value:,.0f}원"
        )
        self.dashboard_cards["alert"].configure(
            text=(
                f"예약 {self.scheduled_time_var.get()}"
                if self.scheduled_email_var.get()
                else "수동"
            )
        )

    def update_pc_right_summary(self, card_values, group_name, stock_count, best_result):

        if not hasattr(self, "pc_summary_vars"):
            return

        mapping = {
            "value": card_values.get("total_value", "-"),
            "pnl": card_values.get("total_pnl", "-"),
            "risk": card_values.get("risk", "-"),
            "attention": card_values.get("attention", "-"),
            "upside": card_values.get("upside", "-"),
            "danger": card_values.get("danger", "-"),
            "events": card_values.get("events", "-"),
        }

        for key, value in mapping.items():
            var = self.pc_summary_vars.get(key)

            if var:
                var.set(value)

        lines = [
            f"그룹: {group_name}",
            f"관심종목: {stock_count}개",
            (
                f"최고 점수: {best_result.name} {safe_number(best_result.score):.1f}"
                if best_result
                else "최고 점수: 분석 대기"
            ),
            "",
            "위험 증가 종목과 중요 이벤트는 상세 탭에서 확인하세요.",
        ]
        self.write_text_widget(self.pc_summary_message, "\n".join(lines))

    def refresh_detail_tab(self):

        if not hasattr(self, "detail_summary_text"):
            return

        code = self.current_stock

        if not code:
            self.detail_summary_var.set("종목을 선택하면 상세 요약이 표시됩니다.")
            self.write_text_widget(self.detail_summary_text, "선택된 종목이 없습니다.")
            return

        preset = self.get_weight_preset()
        result = self.service.analysis_cache.get((code, "2025", "11011", preset))
        stock = self.find_stock_by_code(code)
        name = (
            getattr(result, "name", "")
            or (stock or {}).get("name")
            or code
        )
        summary = self.cached_price_summary(code)
        price = safe_number(summary.get("price"))
        currency = summary.get("currency", "KRW")
        holding = self.holdings.get(code, {})
        quantity = safe_number(holding.get("quantity", 0))
        avg_price = safe_number(holding.get("avg_price", 0))
        pnl = (
            ((price - avg_price) / avg_price) * 100
            if quantity > 0 and avg_price > 0
            else 0
        )
        remote_record = (
            getattr(result, "remote_record", None)
            if result
            else {}
        )
        final_score = safe_number(
            remote_record.get("final_score")
            if isinstance(remote_record, dict)
            else getattr(result, "score", 0)
        )
        rating = (
            remote_record.get("rating")
            or remote_record.get("grade")
            if isinstance(remote_record, dict)
            else self.final_grade(result, final_score)
        )
        action_summary = (
            remote_record.get("action_summary")
            if isinstance(remote_record, dict)
            else ""
        ) or "분석 후 행동 요약이 표시됩니다."
        score_diff = (
            remote_record.get("final_score_diff")
            if isinstance(remote_record, dict)
            else None
        )
        score_diff_text = (
            "전회 비교 없음"
            if score_diff is None
            else f"전회 대비 {safe_number(score_diff):+.1f}점"
        )

        self.detail_summary_var.set(
            f"{name} | 현재가 {self.format_display_price(price, currency, compact=True)} | "
            f"등급 {rating} | 점수 {final_score:.1f} | {score_diff_text} | "
            f"평단 대비 {pnl:+.1f}% | {action_summary}"
        )
        self.write_text_widget(
            self.detail_summary_text,
            "\n".join([
                f"종목명: {name} ({code})",
                f"현재가: {self.format_display_price(price, currency)}",
                f"현재 판단: {rating}",
                f"최종 점수: {final_score:.1f}",
                f"점수 변경: {score_diff_text}",
                f"평단 대비 수익률: {pnl:+.1f}%" if quantity > 0 else "평단 대비 수익률: 보유 입력 없음",
                f"핵심 이유: {self.record_text(remote_record, 'score_change_reason')}",
                f"행동 요약: {action_summary}",
            ])
        )
        self.write_text_widget(
            self.detail_score_text,
            self.build_detail_score_text(result, remote_record)
        )
        self.populate_detail_news(remote_record)
        self.write_text_widget(
            self.detail_strategy_text,
            self.build_detail_strategy_text(result, remote_record)
        )
        self.write_text_widget(
            self.detail_event_text,
            self.build_detail_event_text(remote_record)
        )
        self.write_text_widget(
            self.detail_history_text,
            self.build_detail_history_text(remote_record)
        )

    def write_text_widget(self, widget, text):

        if widget is None:
            return

        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, text or "-")
        widget.configure(state="disabled")

    @staticmethod
    def record_text(record, key, default="-"):

        if isinstance(record, dict):
            value = record.get(key)
            return str(value) if value not in (None, "") else default

        return default

    def build_detail_score_text(self, result, record):

        factor_scores = record.get("factor_scores", {}) if isinstance(record, dict) else {}
        risk_reasons = record.get("risk_reasons", []) if isinstance(record, dict) else []
        confidence_reasons = (
            record.get("data_confidence_reasons", [])
            if isinstance(record, dict)
            else []
        )
        quant_score = safe_number(
            record.get("quant_score")
            if isinstance(record, dict)
            else SharedAnalysisBridge.quant_average_score(result)
        )
        news_score = safe_number(
            record.get("news_score")
            if isinstance(record, dict)
            else self.news_normalized_score(result)
        )
        final_score = safe_number(
            record.get("final_score")
            if isinstance(record, dict)
            else ((quant_score * 0.7) + (news_score * 0.3))
        )
        lines = [
            f"최종 점수: {final_score:.1f}",
            f"퀀트 점수: {quant_score:.1f}",
            f"뉴스 점수: {news_score:.1f}",
            f"데이터 신뢰도: {self.record_text(record, 'data_confidence')}",
            f"종목 유형별 모델: {self.record_text(record, 'stock_type')}",
            "",
            "팩터 점수",
        ]
        labels = {
            "value": "가치",
            "quality": "품질",
            "growth": "성장",
            "stability": "안정성",
            "momentum": "모멘텀",
            "dividend": "배당",
        }

        for key, label in labels.items():
            lines.append(f"- {label}: {safe_number(factor_scores.get(key, 0)):.1f}")

        lines.extend([
            "",
            "감점 사유",
            *(f"- {item}" for item in (risk_reasons or ["감점 사유 없음"])),
            "",
            "데이터 신뢰도 이유",
            *(f"- {item}" for item in (confidence_reasons or ["데이터 신뢰도 정보 없음"])),
            "",
            "WATCH BUY: 65점 이상 72점 미만으로, 신규 매수보다 조정 시 관심 구간입니다.",
        ])
        return "\n".join(lines)

    def populate_detail_news(self, record):

        if not hasattr(self, "detail_news_tree"):
            return

        for item in self.detail_news_tree.get_children():
            self.detail_news_tree.delete(item)

        news_items = record.get("news", []) if isinstance(record, dict) else []

        for item in news_items[:20]:
            self.detail_news_tree.insert(
                "",
                tk.END,
                values=(
                    item.get("date", "-"),
                    item.get("impact_label", "중립"),
                    item.get("title", "-"),
                )
            )

    def build_detail_strategy_text(self, result, record):

        strategy = record.get("user_strategy", {}) if isinstance(record, dict) else {}
        lines = [
            f"매수 이유: {self.record_text(record, 'buy_reason')}",
            f"보유 이유: {self.record_text(record, 'hold_reason')}",
            f"목표가: {self.target_text(record) if isinstance(record, dict) else '-'}",
            f"손절 기준: {self.record_text(record, 'stop_loss_basis')}",
            f"추가매수 기준: {self.record_text(record, 'add_buy_basis')}",
            f"사용자 전략: {strategy.get('strategy') or strategy.get('name') or '-'}",
            f"전략 판단: {self.record_text(record, 'user_adjusted_action')}",
            f"메모: {strategy.get('memo') or self.record_text(record, 'user_strategy_reason')}",
        ]
        return "\n".join(lines)

    def build_detail_event_text(self, record):

        events = record.get("events", []) if isinstance(record, dict) else []
        lines = [
            f"중요 이벤트 경고: {self.record_text(record, 'event_warning')}",
            "",
            "이벤트 목록",
        ]

        if not events:
            lines.append("- 등록된 이벤트 없음")

        for item in events:
            lines.append(
                f"- {item.get('event_date', '-')} | {item.get('event_type', '-')} | "
                f"{item.get('event_title', '-')} | {item.get('importance', 'medium')}"
            )

            if item.get("memo"):
                lines.append(f"  메모: {item.get('memo')}")

        return "\n".join(lines)

    def build_detail_history_text(self, record):

        change = record.get("score_change", {}) if isinstance(record, dict) else {}
        history = (
            record.get("analysis_history", [])
            if isinstance(record, dict)
            else []
        )
        lines = [
            f"이전 점수: {change.get('previous_final_score', '-')}",
            f"현재 점수: {change.get('current_final_score', '-')}",
            f"등급 변경: {'예' if change.get('rating_changed') else '아니오'}",
            f"변경 이유: {change.get('score_change_reason', '-')}",
            "",
            "과거 판단 검증",
        ]

        if not history:
            lines.append("- 기록 없음")

        for item in history[:10]:
            lines.append(
                f"- {item.get('analyzed_at', '-')} | "
                f"{item.get('final_score', '-')}점 | {item.get('rating', '-')} | "
                f"7일 {item.get('return_after_7d', None)} | "
                f"30일 {item.get('return_after_30d', None)}"
            )

        return "\n".join(lines)

    def refresh_event_tab(self):

        if not hasattr(self, "event_text"):
            return

        stocks = (
            self.groups.get(self.current_group, [])
            if self.current_group
            else []
        )
        preset = self.get_weight_preset()
        lines = ["이벤트 캘린더", ""]
        event_count = 0

        for stock in stocks:
            code = stock.get("code")
            result = self.service.analysis_cache.get((code, "2025", "11011", preset))
            record = getattr(result, "remote_record", {}) if result else {}
            events = record.get("events", []) if isinstance(record, dict) else []
            warning = record.get("event_warning", "") if isinstance(record, dict) else ""

            if warning:
                lines.append(f"[{stock.get('name', code)}] {warning}")

            for item in events:
                event_count += 1
                lines.append(
                    f"- {stock.get('name', code)} | {item.get('event_date', '-')} | "
                    f"{item.get('event_type', '-')} | {item.get('event_title', '-')}"
                )

        if event_count == 0:
            lines.append("등록된 이벤트가 없습니다. 서버 /api/events 또는 사용자 입력으로 이벤트를 추가할 수 있습니다.")

        self.write_text_widget(self.event_text, "\n".join(lines))

    def refresh_strategy_tab(self):

        if not hasattr(self, "strategy_text"):
            return

        stocks = (
            self.groups.get(self.current_group, [])
            if self.current_group
            else []
        )
        preset = self.get_weight_preset()
        lines = ["전략 / 메모", ""]

        for stock in stocks:
            code = stock.get("code")
            result = self.service.analysis_cache.get((code, "2025", "11011", preset))
            record = getattr(result, "remote_record", {}) if result else {}
            strategy = record.get("user_strategy", {}) if isinstance(record, dict) else {}
            lines.extend([
                f"[{stock.get('name', code)} / {code}]",
                f"- 사용자 전략: {strategy.get('strategy') or strategy.get('name') or '-'}",
                f"- 전략 판단: {self.record_text(record, 'user_adjusted_action')}",
                f"- 행동 요약: {self.record_text(record, 'action_summary')}",
                f"- 메모: {strategy.get('memo') or self.record_text(record, 'user_strategy_reason')}",
                "",
            ])

        if not stocks:
            lines.append("관심종목 그룹을 선택하세요.")

        self.write_text_widget(self.strategy_text, "\n".join(lines))

    def find_stock_by_code(self, code):

        for stocks in self.groups.values():
            for stock in stocks:
                if str(stock.get("code", "")).upper() == str(code or "").upper():
                    return stock

        return None

    def target_text(self, record):

        if not isinstance(record, dict):
            return ""

        target = safe_number(record.get("target_price", 0))
        upside = safe_number(record.get("target_upside", 0))
        currency = record.get("currency", "KRW")

        if target <= 0:
            return ""

        return (
            f"{self.format_display_price(target, currency, compact=True)}"
            f" ({upside:+.1f}%)"
        )

    def refresh_briefing_table(self):

        if not hasattr(self, "briefing_tree"):
            return

        for item in self.briefing_tree.get_children():
            self.briefing_tree.delete(item)

        if self.current_group is None:
            return

        preset = self.get_weight_preset()
        stocks = self.groups.get(self.current_group, [])
        missing_stocks = []
        rows = []

        for stock in stocks:
            code = stock["code"]
            result = self.service.analysis_cache.get(
                (
                    code,
                    "2025",
                    "11011",
                    preset
                )
            )

            if result is None:
                missing_stocks.append(stock)

            metrics = self.cached_briefing_metrics(code)

            quant_score = (
                self.quant_average_score(result)
                if result
                else 0
            )
            news_score = (
                self.news_normalized_score(result)
                if result
                else 0
            )
            avg_score = (
                (quant_score + news_score) / 2
                if result
                else 0
            )
            briefing = self.make_briefing_comment(
                result,
                metrics
            )

            rows.append({
                "code": code,
                "score": avg_score,
                "signal": getattr(result, "signal", "-") if result else "-",
                "values": (
                    stock["name"],
                    code,
                    getattr(result, "asset_type", "STOCK") if result else "-",
                    self.format_display_price(
                        metrics.get("price", 0),
                        metrics.get("currency", "KRW"),
                        compact=True
                    ),
                    self.display_price_date(result, metrics),
                    self.data_freshness_label(result, metrics),
                    self.format_percent(metrics.get("change_1d", 0)),
                    self.format_percent(metrics.get("change_1m", 0)),
                    self.format_percent(metrics.get("change_3m", 0)),
                    f"{quant_score:.1f}" if result else "분석 대기",
                    f"{news_score:.1f}" if result else "분석 대기",
                    f"{avg_score:.1f}" if result else "분석 대기",
                    self.analyst_summary(result),
                    self._comparison_number(
                        getattr(result, "short_ratio", None),
                        suffix="%"
                    ),
                    self.format_flow_value(
                        getattr(result, "foreign_net_buy", None)
                    ),
                    self.format_flow_value(
                        getattr(result, "institution_net_buy", None)
                    ),
                    briefing,
                )
            })

        rows.sort(
            key=lambda row: row["score"],
            reverse=True
        )

        for index, row in enumerate(rows):
            self.briefing_tree.insert(
                "",
                tk.END,
                iid=f"briefing:{row['code']}:{index}",
                values=row["values"],
                tags=(self.signal_tag(row["signal"]),)
            )

        if (
            missing_stocks
            and not self.compare_analysis_running
        ):
            self.start_compare_analysis(
                missing_stocks,
                preset
            )

        if hasattr(self, "briefing_report_text"):
            self.briefing_report_text.delete("1.0", tk.END)
            self.briefing_report_text.insert(
                tk.END,
                self.build_ai_quant_briefing(
                    self.current_group,
                    preset,
                    analyze_missing=False,
                    use_cached=True
                )
            )

    def save_ai_quant_briefing(self):

        if self.current_group is None:
            messagebox.showinfo(
                "브리핑 저장",
                "먼저 관심종목 그룹을 선택하세요."
            )
            return

        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        now = datetime.now()
        safe_name = self._safe_report_filename(
            f"AI_Quant_Briefing_{self.current_group}_{now:%Y%m%d_%H%M}"
        )
        path = filedialog.asksaveasfilename(
            title="AI 퀀트 브리핑 저장",
            initialdir=str(REPORT_DIR),
            initialfile=f"{safe_name}.txt",
            defaultextension=".txt",
            filetypes=[
                ("텍스트 파일", "*.txt"),
                ("모든 파일", "*.*"),
            ]
        )

        if not path:
            return

        text = self.build_ai_quant_briefing(
            self.current_group,
            self.get_weight_preset(),
            analyze_missing=True
        )

        try:
            Path(path).write_text(text, encoding="utf-8")
        except Exception as e:
            messagebox.showerror("브리핑 저장 실패", str(e))
            return

        messagebox.showinfo("브리핑 저장", "AI 퀀트 브리핑을 저장했습니다.")

    def build_ai_quant_briefing(
        self,
        group_name,
        preset,
        analyze_missing=True,
        use_cached=False
    ):

        now = datetime.now()
        records = self.build_briefing_records(
            group_name,
            preset,
            analyze_missing=analyze_missing,
            use_cached=use_cached
        )
        domestic = [
            item for item in records
            if item["code"].isdigit()
        ]
        overseas = [
            item for item in records
            if not item["code"].isdigit()
        ]
        grade_map = self.group_records_by_grade(records)
        stale_lines = [
            self.data_transparency_line(item)
            for item in records
            if item.get("freshness_days", 0) > 3
        ]

        lines = [
            f"AI 퀀트 브리핑 - {now:%Y.%m.%d}",
            "=" * 44,
            f"그룹: {group_name}",
            f"프리셋: {preset}",
            f"생성시각: {now:%Y-%m-%d %H:%M:%S}",
            "",
            "[국내 종목]",
            *self.format_briefing_section(domestic),
            "",
            "[국내 핵심 뉴스]",
            *self.format_news_section(domestic),
            "",
            "[해외 종목]",
            *self.format_briefing_section(overseas),
            "",
            "[해외 핵심 뉴스]",
            *self.format_news_section(overseas),
            "",
            "[최종 등급표]",
            *self.format_grade_table(grade_map),
            "",
            "[데이터 투명성 안내]",
        ]

        if stale_lines:
            lines.extend(stale_lines)
        else:
            lines.append("- 오래된 가격 데이터 경고 없음")

        lines.extend([
            "",
            "[주의]",
            "이 브리핑은 자동 수집 데이터와 규칙 기반 점수로 만든 참고 자료입니다.",
            "투자 판단과 책임은 사용자에게 있습니다.",
            "",
        ])

        return "\n".join(lines)

    def build_briefing_records(
        self,
        group_name,
        preset,
        analyze_missing=True,
        use_cached=False
    ):

        records = []
        group_stocks = self.groups.get(group_name, [])

        if analyze_missing and self.remote_client().enabled:
            missing = [
                stock
                for stock in group_stocks
                if self.service.analysis_cache.get(
                    (
                        stock["code"],
                        "2025",
                        "11011",
                        preset
                    )
                ) is None
            ]

            if missing:
                try:
                    self.show_server_connecting("브리핑 서버")
                    self.analyze_remote_records(missing, preset)
                except Exception as e:
                    print("브리핑 서버 분석 오류, 로컬 분석으로 전환:", e)

        for stock in group_stocks:
            code = stock["code"]
            result = self.service.analysis_cache.get(
                (
                    code,
                    "2025",
                    "11011",
                    preset
                )
            )

            if result is None and analyze_missing:
                try:
                    result = self.analyzer.analyze(
                        code,
                        "2025",
                        "11011",
                        preset
                    )
                except Exception:
                    result = None

            if use_cached:
                metrics = self.cached_briefing_metrics(code)
            else:
                try:
                    metrics = self.service.get_briefing_metrics(code)
                except Exception:
                    metrics = {
                        "price": safe_number(getattr(result, "price", 0)),
                        "currency": getattr(result, "currency", "KRW"),
                        "price_date": getattr(result, "price_date", ""),
                        "change_1d": safe_number(
                            getattr(result, "change_rate", 0)
                        ),
                        "change_1m": 0,
                        "change_3m": 0,
                    }

            news = []

            if not use_cached:
                news = self.get_core_news(
                    getattr(result, "name", stock.get("name", code))
                )
            elif result is not None:
                remote_record = getattr(result, "remote_record", None)

                if isinstance(remote_record, dict):
                    news = remote_record.get("news", [])[:3]
            avg_score = (
                (
                    self.quant_average_score(result)
                    + self.news_normalized_score(result)
                ) / 2
                if result
                else 0
            )
            price_date = self.display_price_date(result, metrics)

            records.append({
                "stock": stock,
                "code": code,
                "name": getattr(result, "name", stock.get("name", code)),
                "result": result,
                "metrics": metrics,
                "news": news,
                "avg_score": avg_score,
                "grade": self.final_grade(result, avg_score),
                "price_date": price_date,
                "freshness_label": self.data_freshness_label(
                    result,
                    metrics
                ),
                "freshness_days": self.price_date_age_days(price_date),
            })

        return records

    def format_briefing_section(self, records):

        if not records:
            return ["- 해당 종목 없음"]

        lines = [
            "종목 | 주가 | 기준일 | 1일 | 1개월 | 3개월 | 52주 범위 | 퀀트 | 애널리스트"
        ]

        for item in records:
            result = item["result"]
            metrics = item["metrics"]
            price = self.format_display_price(
                metrics.get("price", 0),
                metrics.get("currency", "KRW"),
                compact=True
            )
            range_52 = "-"

            if result:
                range_52 = (
                    f"{self.format_display_price(result.low52, result.currency, compact=True)}"
                    f"~{self.format_display_price(result.high52, result.currency, compact=True)}"
                    if result.low52 and result.high52
                    else "-"
                )

            lines.append(
                f"{item['name']} ({item['code']}) | "
                f"{price} | {item['price_date'] or '-'} "
                f"{self.stale_marker(item)} | "
                f"{self.format_percent(metrics.get('change_1d', 0))} | "
                f"{self.format_percent(metrics.get('change_1m', 0))} | "
                f"{self.format_percent(metrics.get('change_3m', 0))} | "
                f"{range_52} | {item['grade']} | "
                f"{self.analyst_summary(result)}"
            )

        return lines

    def format_news_section(self, records):

        lines = []

        for item in records:
            news = item.get("news") or []

            if not news:
                lines.append(f"- {item['name']}: 핵심 뉴스 없음")
                continue

            for news_item in news[:3]:
                date = news_item.get("date") or "-"
                label = news_item.get("impact_label") or "중립"
                title = news_item.get("title") or "-"
                lines.append(
                    f"- {item['name']} [{date} / {label}] {title}"
                )

        return lines or ["- 핵심 뉴스 없음"]

    @staticmethod
    def group_records_by_grade(records):

        grade_map = {}

        for item in records:
            grade_map.setdefault(item["grade"], []).append(item["name"])

        return grade_map

    @staticmethod
    def format_grade_table(grade_map):

        order = [
            "STRONG BUY",
            "BUY",
            "WATCH BUY",
            "HOLD",
            "REDUCE",
            "SELL",
            "분석 대기",
        ]
        lines = []

        for grade in order:
            names = grade_map.get(grade)

            if names:
                lines.append(f"- {grade}: {', '.join(names)}")

        return lines or ["- 등급 없음"]

    def final_grade(self, result, avg_score):

        if result is None:
            return "분석 대기"

        if avg_score >= 85:
            return "STRONG BUY"

        if avg_score >= 72:
            return "BUY"

        if avg_score >= 65:
            return "WATCH BUY"

        if avg_score >= 55:
            return "HOLD"

        if avg_score >= 40:
            return "REDUCE"

        return "SELL"

    def get_core_news(self, name):

        try:
            return self.service.news.get_news(name, limit=3)
        except Exception:
            return []

    def data_transparency_line(self, item):

        days = item.get("freshness_days", 0)
        date = item.get("price_date") or "확인 불가"

        return (
            f"- {item['name']} ({item['code']}): 가격 기준일 {date}, "
            f"{days}일 경과. 최신 가격이 아닐 수 있습니다."
        )

    @staticmethod
    def stale_marker(item):

        return "주의" if item.get("freshness_days", 0) > 3 else "확인"

    def display_price_date(self, result, metrics):

        return (
            metrics.get("price_date")
            or getattr(result, "price_date", "")
            or ""
        )

    def data_freshness_label(self, result, metrics):

        age = self.price_date_age_days(
            self.display_price_date(result, metrics)
        )

        if age < 0:
            return "확인불가"

        if age <= 3:
            return "정상"

        if age <= 10:
            return "주의"

        return "오래됨"

    @staticmethod
    def price_date_age_days(price_date):

        if not price_date:
            return -1

        try:
            parsed = datetime.strptime(price_date[:10], "%Y-%m-%d")
            return max((datetime.now() - parsed).days, 0)
        except Exception:
            return -1

    def analyst_summary(self, result):

        if result is None:
            return "-"

        target = safe_number(getattr(result, "analyst_target_mean", 0))
        count = safe_number(getattr(result, "analyst_count", 0))
        recommendation = self.format_analyst_recommendation(
            getattr(result, "analyst_recommendation", "")
        )

        parts = []

        if recommendation:
            parts.append(recommendation)

        if target > 0:
            upside = (
                (target - safe_number(result.price))
                / safe_number(result.price)
                * 100
                if safe_number(result.price) > 0
                else 0
            )
            parts.append(
                f"목표 {self.format_display_price(target, result.currency, compact=True)}"
                f"({upside:+.1f}%)"
            )

        if count > 0:
            parts.append(f"{count:.0f}명")

        return ", ".join(parts) if parts else "-"

    @staticmethod
    def format_analyst_recommendation(value):

        text = str(value or "").strip()

        mapping = {
            "strong_buy": "적극 매수",
            "buy": "매수",
            "hold": "보유",
            "underperform": "비중 축소",
            "sell": "매도",
        }

        return mapping.get(text.lower(), text)

    @staticmethod
    def format_percent(value):

        value = safe_number(value)
        return f"{value:+.2f}%"

    def make_briefing_comment(self, result, metrics):

        if result is None:
            return "분석 대기: 그룹 분석을 실행하면 퀀트/뉴스 해석이 채워집니다."

        one_month = safe_number(metrics.get("change_1m", 0))
        three_month = safe_number(metrics.get("change_3m", 0))
        short_ratio = safe_number(getattr(result, "short_ratio", 0))
        foreign = safe_number(getattr(result, "foreign_net_buy", 0))
        institution = safe_number(getattr(result, "institution_net_buy", 0))
        asset_type = getattr(result, "asset_type", "STOCK")

        parts = []

        if asset_type == "ETF":
            parts.append("ETF는 재무제표보다 추세와 구성자산 흐름 중심으로 해석")

        if three_month >= 10:
            parts.append("3개월 추세 강세")
        elif three_month <= -10:
            parts.append("3개월 추세 약세")
        elif one_month >= 5:
            parts.append("단기 회복")
        else:
            parts.append("추세 중립")

        if short_ratio >= 5:
            parts.append("공매도 부담 주의")

        if foreign > 0 and institution > 0:
            parts.append("외국인·기관 동반 순매수")
        elif foreign < 0 and institution < 0:
            parts.append("외국인·기관 동반 순매도")
        elif foreign > 0:
            parts.append("외국인 순매수")
        elif institution > 0:
            parts.append("기관 순매수")

        news_score = self.news_normalized_score(result)

        if news_score >= 65:
            parts.append("뉴스 흐름 우호적")
        elif news_score <= 35:
            parts.append("뉴스 리스크 확인 필요")

        return " | ".join(parts)

    def on_briefing_select(self, event=None):

        if not hasattr(self, "briefing_tree"):
            return

        selection = self.briefing_tree.selection()

        if not selection:
            return

        values = self.briefing_tree.item(
            selection[0],
            "values"
        )

        if len(values) < 2:
            return

        self.current_stock = values[1]
        self.analyze_stock()

    def on_dashboard_select(self, event=None):

        if not hasattr(self, "dashboard_tree"):
            return

        selection = self.dashboard_tree.selection()

        if not selection:
            return

        values = self.dashboard_tree.item(
            selection[0],
            "values"
        )

        if len(values) < 2:
            return

        self.current_stock = values[1]
        self.analyze_stock()

    def refresh_portfolio_table(self, auto_analyze=True):

        if not hasattr(self, "portfolio_tree"):
            return

        for item in self.portfolio_tree.get_children():
            self.portfolio_tree.delete(item)

        if self.current_group is None:
            self.portfolio_summary_var.set(
                "먼저 관심종목 그룹을 선택하세요."
            )
            return

        preset = self.get_weight_preset()
        stocks = self.groups.get(self.current_group, [])
        missing_stocks = []
        candidates = []

        for stock in stocks:
            code = stock["code"]
            result = self.service.analysis_cache.get(
                (
                    code,
                    "2025",
                    "11011",
                    preset
                )
            )

            if result is None:
                missing_stocks.append(stock)
                continue

            candidates.append(result)

        if (
            auto_analyze
            and missing_stocks
            and not self.portfolio_analysis_running
        ):
            self.start_portfolio_analysis(
                missing_stocks,
                preset
            )

        if not candidates:
            self.portfolio_summary_var.set(
                "분석된 종목이 없습니다. 자동 분석이 끝나면 다시 표시됩니다."
                if missing_stocks
                else "포트폴리오를 만들 종목이 없습니다."
            )
            return

        rows = self.build_portfolio_rows(candidates)

        for index, row in enumerate(rows):
            self.portfolio_tree.insert(
                "",
                tk.END,
                iid=f"{row['code']}:{index}",
                values=row["values"],
                tags=(self.signal_tag(row["values"][3]),)
            )

        invested = sum(row["amount"] for row in rows)
        capital = self.get_portfolio_capital()
        cash = max(capital - invested, 0)
        summary = self.portfolio_exposure_summary(rows)
        self.portfolio_summary_var.set(
            f"{self.current_group} | {preset} | "
            f"편입 {len(rows)}종목 | 투자금 {capital:,.0f}원 | "
            f"예상 현금 {cash:,.0f}원\n{summary}"
        )

    def build_portfolio_rows(self, results):

        capital = self.get_portfolio_capital()
        investable = [
            result
            for result in results
            if safe_number(getattr(result, "score", 0)) >= 45
        ]

        if not investable:
            investable = sorted(
                results,
                key=lambda item: safe_number(item.score),
                reverse=True
            )[:5]

        investable = sorted(
            investable,
            key=lambda item: safe_number(item.score),
            reverse=True
        )[:10]

        score_sum = sum(
            max(safe_number(item.score), 0)
            for item in investable
        )

        target_weights = {}

        for item in investable:
            score = max(safe_number(item.score), 0)
            target_weights[item.code] = (
                score / score_sum
                if score_sum > 0
                else 0
            )

        rows = []
        display_results = sorted(
            results,
            key=lambda item: safe_number(item.score),
            reverse=True
        )

        for result in display_results:
            score = max(safe_number(result.score), 0)
            weight = target_weights.get(result.code, 0)
            amount = capital * weight
            price = safe_number(result.price)
            shares = int(amount // price) if price > 0 else 0
            actual_amount = shares * price if shares > 0 else amount
            holding = self.holdings.get(result.code, {})
            holding_qty = safe_number(holding.get("quantity", 0))
            avg_price = safe_number(holding.get("avg_price", 0))
            market_value = holding_qty * price
            cost = holding_qty * avg_price
            pnl = (
                ((price - avg_price) / avg_price) * 100
                if avg_price > 0 and holding_qty > 0
                else 0
            )
            actual_weight = (
                market_value / capital
                if capital > 0
                else 0
            )
            weight_gap = weight - actual_weight
            reason = self._portfolio_reason(result)
            feedback = self._holding_feedback(
                result,
                holding_qty,
                avg_price,
                price,
                pnl,
                weight,
                actual_weight
            )

            rows.append({
                "code": result.code,
                "amount": actual_amount,
                "name": result.name,
                "score": score,
                "signal": result.signal,
                "market_value": market_value,
                "cost": cost,
                "pnl_rate": pnl if holding_qty > 0 else 0,
                "actual_weight": actual_weight,
                "news_score": self.news_normalized_score(result),
                "market": "국내" if str(result.code).isdigit() else "해외",
                "theme": self.stock_theme(result),
                "values": (
                    result.name,
                    result.code,
                    f"{score:.1f}",
                    result.signal,
                    f"{weight * 100:.1f}%",
                    f"{actual_amount:,.0f}원",
                    self.format_display_price(price, result.currency, compact=True),
                    f"{shares:,}",
                    (
                        f"{holding_qty:,.2f}".rstrip("0").rstrip(".")
                        if holding_qty > 0
                        else "-"
                    ),
                    (
                        self.format_display_price(avg_price, result.currency, compact=True)
                        if holding_qty > 0
                        else "-"
                    ),
                    f"{pnl:+.2f}%" if holding_qty > 0 else "-",
                    f"{market_value:,.0f}원" if holding_qty > 0 else "-",
                    f"{weight_gap * 100:+.1f}%",
                    feedback,
                    reason,
                )
            })

        return rows

    def portfolio_exposure_summary(self, rows):
        held_rows = [row for row in rows if safe_number(row.get("market_value", 0)) > 0]

        if not held_rows:
            return "보유 입력 없음 | 총 평가금액 0원 | 총 손익 0원"

        total_value = sum(safe_number(row.get("market_value", 0)) for row in held_rows)
        total_cost = sum(safe_number(row.get("cost", 0)) for row in held_rows)
        total_pnl = total_value - total_cost
        total_pnl_rate = (total_pnl / total_cost * 100) if total_cost > 0 else 0
        risk_value = sum(
            safe_number(row.get("market_value", 0))
            for row in held_rows
            if (
                safe_number(row.get("score", 0)) < 55
                or safe_number(row.get("news_score", 0)) <= 35
                or safe_number(row.get("pnl_rate", 0)) <= -10
            )
        )
        market_weights = self.weight_summary(held_rows, "market", total_value)
        theme_weights = self.weight_summary(held_rows, "theme", total_value)
        over_weight = [
            f"{row.get('name')} {safe_number(row.get('market_value', 0)) / total_value * 100:.1f}%"
            for row in held_rows
            if total_value > 0
            and safe_number(row.get("market_value", 0)) / total_value >= 0.35
        ]

        lines = [
            f"총 평가금액 {total_value:,.0f}원 | 총 손익 {total_pnl:+,.0f}원 ({total_pnl_rate:+.1f}%)",
            f"위험 종목 비중 {risk_value / total_value * 100:.1f}% | 국내/해외 {market_weights}",
            f"테마 비중 {theme_weights}",
            "한 종목 과다 비중 경고 " + (", ".join(over_weight) if over_weight else "없음"),
        ]
        return "\n".join(lines)

    @staticmethod
    def weight_summary(rows, key, total_value):
        if total_value <= 0:
            return "-"

        buckets = {}

        for row in rows:
            label = row.get(key) or "기타"
            buckets[label] = buckets.get(label, 0) + safe_number(row.get("market_value", 0))

        return " / ".join(
            f"{label} {value / total_value * 100:.1f}%"
            for label, value in sorted(buckets.items(), key=lambda item: item[1], reverse=True)
            if value > 0
        )

    @staticmethod
    def stock_theme(result):
        text = " ".join([
            str(getattr(result, "name", "")),
            str(getattr(result, "code", "")),
            str(getattr(result, "industry", "")),
        ]).lower()

        if any(word in text for word in ["bio", "바이오", "pharma", "therapeutics", "제약"]):
            return "바이오"
        if any(word in text for word in ["ai", "인공지능", "엔비디아", "nvidia", "msft", "meta", "googl", "oracle", "palantir"]):
            return "AI"
        if any(word in text for word in ["반도체", "semiconductor", "hbm", "sk하이닉스", "삼성전자", "tsm", "broadcom", "avgo"]):
            return "반도체"
        if any(word in text for word in ["방산", "defense", "aerospace", "한화에어로", "lig", "k방산"]):
            return "방산"

        return "기타"

    def get_portfolio_capital(self):

        text = self.portfolio_capital_var.get()
        text = text.replace(",", "").replace("원", "").strip()

        try:
            capital = float(text)
        except ValueError:
            capital = 10000000

        return max(capital, 0)

    def _portfolio_reason(self, result):

        strengths = []

        if safe_number(result.value) >= 25:
            strengths.append("가치")

        if safe_number(result.quality) >= 70:
            strengths.append("수익성")

        if safe_number(result.growth) >= 20:
            strengths.append("성장")

        if safe_number(result.momentum) >= 30:
            strengths.append("모멘텀")

        if safe_number(result.news) >= 5:
            strengths.append("뉴스")

        return ", ".join(strengths[:3]) if strengths else "상대 점수 우위"

    def _holding_feedback(
        self,
        result,
        quantity,
        avg_price,
        current_price,
        pnl,
        target_weight,
        actual_weight
    ):

        score = safe_number(result.score)
        gap = target_weight - actual_weight

        if quantity <= 0:
            if target_weight > 0:
                return "신규 편입 후보"
            return "관심 유지"

        if -20 < pnl <= -10 and score >= 45:
            recovery = self.recovery_price_text(current_price, result.currency)
            stop = self.stop_loss_basis_text(avg_price, result.currency)
            target = self.target_price_text(result)
            return (
                f"목표가 {target} / 손절 기준 {stop} / "
                "추가매수 기준 실적 발표 전후 변동성 확인 후 / "
                f"판단 손절보다는 보유 관찰, {recovery} 회복 시 비중 축소 검토"
            )

        if pnl <= -20:
            return (
                f"목표가 {self.target_price_text(result)} / "
                f"손절 기준 {self.stop_loss_basis_text(avg_price, result.currency)} / "
                "추가매수 기준 보류 / 판단 손실 원인 재점검 및 비중 축소 검토"
            )

        if score < 45 or "매도" in result.signal:
            return (
                f"목표가 {self.target_price_text(result)} / "
                f"손절 기준 {self.stop_loss_basis_text(avg_price, result.currency)} / "
                "추가매수 기준 보류 / 판단 보유 축소 검토"
            )

        if "비중 축소" in result.signal:
            return "일부 축소 검토"

        if pnl <= -15 and score < 60:
            return "손실 관리 필요"

        if gap >= 0.05:
            return "비중 부족"

        if gap <= -0.05:
            return "비중 과다"

        if score >= 75:
            return "보유 유지 우호"

        return "보유 유지"

    def target_price_text(self, result):
        target = safe_number(
            getattr(result, "analyst_target_mean", 0)
            or getattr(result, "target_price", 0)
        )

        if target <= 0:
            return "데이터 없음"

        return self.format_display_price(
            target,
            getattr(result, "currency", "KRW"),
            compact=True,
        )

    def stop_loss_basis_text(self, avg_price, currency="KRW"):
        avg_price = safe_number(avg_price)

        if avg_price <= 0:
            return "평단 입력 후 -10%"

        stop_price = avg_price * 0.9

        if currency == "USD":
            return f"${stop_price:,.2f} 이탈"

        rounded = round(stop_price / 1000) * 1000
        return f"{rounded:,.0f}원 이탈"

    def recovery_price_text(self, current_price, currency="KRW"):
        current_price = safe_number(current_price)

        if current_price <= 0:
            return "단기 저항선"

        target = current_price * 1.06

        if currency == "USD":
            return f"${target:,.2f}"

        rounded = round(target / 1000) * 1000
        return f"{rounded:,.0f}원"

    def on_portfolio_select(self, event=None):

        if not hasattr(self, "portfolio_tree"):
            return

        selection = self.portfolio_tree.selection()

        if not selection:
            return

        values = self.portfolio_tree.item(
            selection[0],
            "values"
        )

        if len(values) < 2:
            return

        code = values[1]
        holding = self.holdings.get(code, {})
        self.holding_code_var.set(code)
        self.holding_qty_var.set(
            str(holding.get("quantity", ""))
        )
        self.holding_avg_price_var.set(
            str(holding.get("avg_price", ""))
        )

    def save_holding(self):

        code = self.holding_code_var.get().strip()

        if not code:
            messagebox.showinfo(
                "보유 저장",
                "종목 코드를 입력하거나 포트폴리오 행을 선택하세요."
            )
            return

        try:
            quantity = safe_number(
                self.holding_qty_var.get()
                    .replace(",", "")
                    .strip()
            )
            avg_price = safe_number(
                self.holding_avg_price_var.get()
                    .replace(",", "")
                    .replace("원", "")
                    .replace("$", "")
                    .strip()
            )
        except Exception:
            messagebox.showerror(
                "보유 저장 실패",
                "수량과 평균가를 숫자로 입력하세요."
            )
            return

        if quantity <= 0 or avg_price <= 0:
            messagebox.showerror(
                "보유 저장 실패",
                "수량과 평균가는 0보다 커야 합니다."
            )
            return

        self.holdings[code] = {
            "quantity": quantity,
            "avg_price": avg_price,
        }
        self.save_holdings()
        self.refresh_portfolio_table(auto_analyze=False)
        self.refresh_dashboard()
        self.status_var.set(f"{code} 보유 정보 저장 완료")

    def delete_holding(self):

        code = self.holding_code_var.get().strip()

        if not code:
            return

        self.holdings.pop(code, None)
        self.save_holdings()
        self.holding_qty_var.set("")
        self.holding_avg_price_var.set("")
        self.refresh_portfolio_table(auto_analyze=False)
        self.refresh_dashboard()
        self.status_var.set(f"{code} 보유 정보 삭제 완료")

    def load_holdings(self):

        if not self.holdings_file.exists():
            self.holdings = {}
            return

        try:
            self.holdings = json.loads(
                self.holdings_file.read_text(
                    encoding="utf-8"
                )
            )
        except Exception:
            self.holdings = {}

    def save_holdings(self):

        self.holdings_file.write_text(
            json.dumps(
                self.holdings,
                ensure_ascii=False,
                indent=4
            ),
            encoding="utf-8"
        )

    def start_portfolio_analysis(self, stocks, preset):

        self.portfolio_analysis_running = True
        self.status_var.set(
            f"포트폴리오 분석 중... 0/{len(stocks)}"
        )

        thread = threading.Thread(
            target=self.portfolio_analysis_worker,
            args=(list(stocks), preset),
            daemon=True
        )
        thread.start()

    def portfolio_analysis_worker(self, stocks, preset):

        total = len(stocks)

        if self.remote_client().enabled:
            try:
                self.show_server_connecting("포트폴리오 서버")
                self.analyze_remote_records(stocks, preset)
                self.root.after(
                    0,
                    self.finish_portfolio_analysis
                )
                return
            except Exception as e:
                print("포트폴리오 서버 분석 오류, 로컬 분석으로 전환:", e)

        for index, stock in enumerate(stocks, start=1):
            try:
                self.analyzer.analyze(
                    stock["code"],
                    "2025",
                    "11011",
                    preset
                )
            except Exception as e:
                print("포트폴리오 분석 오류:", stock.get("code"), e)

            self.root.after(
                0,
                lambda i=index, t=total:
                self.status_var.set(f"포트폴리오 분석 중... {i}/{t}")
            )

        self.root.after(
            0,
            self.finish_portfolio_analysis
        )

    def finish_portfolio_analysis(self):

        self.portfolio_analysis_running = False
        self.refresh_stock_list(refresh_compare=False)
        self.refresh_comparison_table(auto_analyze=False)
        self.refresh_portfolio_table(auto_analyze=False)
        self.refresh_briefing_table()
        self.refresh_dashboard()
        self.status_var.set("포트폴리오 분석 완료")

    def move_to_search_list(self, event):

        if self.listbox.size() == 0:
            return

        self.listbox.focus_set()

        self.listbox.selection_clear(0, tk.END)

        self.listbox.selection_set(0)

        self.listbox.activate(0)

    def add_first_search_result(self, event):

        if self.listbox.size() == 0:
            return

        self.listbox.selection_clear(0, tk.END)

        self.listbox.selection_set(0)

        self.on_select(None)

    def save_groups(self):

        with open(
            self.watchlist_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                self.groups,
                f,
                ensure_ascii=False,
                indent=4
            )

    def current_alert_settings(self):

        return {
            "alert_enabled": self.alert_enabled_var.get(),
            "alert_popup": self.alert_popup_var.get(),
            "alert_email": self.alert_email_var.get(),
            "alert_threshold": self.alert_threshold_var.get(),
            "scheduled_email": self.scheduled_email_var.get(),
            "scheduled_time": self.scheduled_time_var.get().strip(),
            "auto_refresh_interval_minutes": self.auto_refresh_interval_var.get().strip(),
            "alert_recipient": self.alert_recipient_var.get().strip(),
            "smtp_host": self.smtp_host_var.get().strip(),
            "smtp_port": self.smtp_port_var.get().strip(),
            "smtp_user": self.smtp_user_var.get().strip(),
            "smtp_password": self.smtp_password_var.get(),
            "smtp_tls": self.smtp_tls_var.get(),
            "api_base_url": self.api_base_url_var.get().strip().rstrip("/"),
        }

    def build_user_data_backup(self):

        return {
            "app": "Morning Stock Assistant Pro",
            "backup_version": 1,
            "app_version": APP_VERSION,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "groups": self.groups,
            "holdings": self.holdings,
            "alert_settings": self.current_alert_settings(),
        }

    def export_user_data(self):

        default_name = (
            "MorningStockAssistant_backup_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        path = filedialog.asksaveasfilename(
            title="데이터 백업",
            defaultextension=".json",
            initialfile=default_name,
            filetypes=[
                ("JSON 백업 파일", "*.json"),
                ("모든 파일", "*.*"),
            ]
        )

        if not path:
            return

        try:
            Path(path).write_text(
                json.dumps(
                    self.build_user_data_backup(),
                    ensure_ascii=False,
                    indent=4
                ),
                encoding="utf-8"
            )
        except Exception as e:
            messagebox.showerror(
                "데이터 백업 실패",
                str(e)
            )
            return

        messagebox.showinfo(
            "데이터 백업",
            "관심종목, 보유정보, 알림 설정을 백업했습니다."
        )

    def import_user_data(self):

        path = filedialog.askopenfilename(
            title="데이터 불러오기",
            filetypes=[
                ("JSON 백업 파일", "*.json"),
                ("모든 파일", "*.*"),
            ]
        )

        if not path:
            return

        try:
            backup = json.loads(
                Path(path).read_text(encoding="utf-8")
            )
        except Exception as e:
            messagebox.showerror(
                "데이터 불러오기 실패",
                f"백업 파일을 읽을 수 없습니다.\n{e}"
            )
            return

        if not isinstance(backup, dict):
            messagebox.showerror(
                "데이터 불러오기 실패",
                "올바른 백업 파일 형식이 아닙니다."
            )
            return

        groups = backup.get("groups")

        if not isinstance(groups, dict):
            messagebox.showerror(
                "데이터 불러오기 실패",
                "관심종목 데이터가 없는 백업 파일입니다."
            )
            return

        answer = messagebox.askyesno(
            "데이터 불러오기",
            "현재 관심종목/보유정보/알림 설정을 백업 파일 내용으로 "
            "교체하시겠습니까?\n\n"
            "교체 전 현재 데이터는 자동 백업됩니다."
        )

        if not answer:
            return

        safety_path = (
            self.watchlist_file.parent
            / (
                "auto_backup_before_import_"
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
        )

        try:
            safety_path.write_text(
                json.dumps(
                    self.build_user_data_backup(),
                    ensure_ascii=False,
                    indent=4
                ),
                encoding="utf-8"
            )

            self.groups = groups
            self.holdings = (
                backup.get("holdings")
                if isinstance(backup.get("holdings"), dict)
                else {}
            )

            self.save_groups()
            self.save_holdings()

            alert_settings = backup.get("alert_settings")

            if isinstance(alert_settings, dict):
                self.alert_settings_file.write_text(
                    json.dumps(
                        alert_settings,
                        ensure_ascii=False,
                        indent=4
                    ),
                    encoding="utf-8"
                )
                self.load_alert_settings()

            previous_group = self.current_group
            self.group_list.delete(0, tk.END)

            for name in self.groups:
                self.group_list.insert(tk.END, name)

            if previous_group in self.groups:
                names = list(self.groups)
                index = names.index(previous_group)
                self.group_list.selection_set(index)
                self.current_group = previous_group
            elif self.groups:
                self.group_list.selection_set(0)
                self.current_group = next(iter(self.groups))
            else:
                self.current_group = None

            self.current_stock = None
            self.current_result = None
            self.refresh_stock_list()
            self.refresh_portfolio_table(auto_analyze=False)
            self.refresh_briefing_table()
            self.refresh_dashboard()

        except Exception as e:
            messagebox.showerror(
                "데이터 불러오기 실패",
                str(e)
            )
            return

        messagebox.showinfo(
            "데이터 불러오기",
            f"데이터를 불러왔습니다.\n\n이전 데이터 자동 백업:\n{safety_path}"
        )

    # --------------------------------------------------
    # 실행
    # --------------------------------------------------
    def run(self):
        self.root.mainloop()

    def add_group(self):

        name = simpledialog.askstring(
            "그룹 추가",
            "그룹 이름을 입력하세요."
        )

        if not name:
            return

        name = name.strip()

        if not name:
            return

        if name in self.groups:
            messagebox.showwarning(
                "중복",
                "이미 존재하는 그룹입니다."
            )
            return

        self.groups[name] = []

        self.group_list.insert(tk.END, name)

        self.save_groups()


    def rename_group(self):

        selection = self.group_list.curselection()

        if not selection:
            return

        old_name = self.group_list.get(selection[0])

        new_name = simpledialog.askstring(
            "이름 변경",
            "새 그룹명을 입력하세요.",
            initialvalue=old_name
        )

        if not new_name:
            return

        new_name = new_name.strip()

        if not new_name:
            return

        if new_name in self.groups:
            messagebox.showwarning(
                "중복",
                "이미 존재하는 그룹입니다."
            )
            return

        self.groups[new_name] = self.groups.pop(old_name)

        self.group_list.delete(selection[0])
        self.group_list.insert(selection[0], new_name)
        self.save_groups()


    def delete_group(self):

        selection = self.group_list.curselection()

        if not selection:
            return

        name = self.group_list.get(selection[0])

        answer = messagebox.askyesno(
            "삭제",
            f"{name} 그룹을 삭제하시겠습니까?"
        )

        if not answer:
            return

        del self.groups[name]

        self.group_list.delete(selection[0])
        self.save_groups()

    def refresh_group(self):

        if self.current_group is None:
            return

        preset = self.get_weight_preset()

        thread = threading.Thread(
            target=self.refresh_group_worker,
            args=(preset,),
            daemon=True
        )

        thread.start()

    def refresh_group_worker(self, preset):

        stocks = self.groups.get(
            self.current_group,
            []
        )

        total = len(stocks)

        for index, stock in enumerate(stocks, start=1):

            self.service.analysis_cache.pop(
                (
                    stock["code"],
                    "2025",
                    "11011",
                    preset
                ),
                None
            )
            self.service.stock_cache.pop(
                (
                    stock["code"],
                    "2025",
                    "11011"
                ),
                None
            )
            self.service.price_summary_cache.pop(
                stock["code"],
                None
            )

            self.analyzer.analyze(
                stock["code"],
                "2025",
                "11011",
                preset
            )

            self.root.after(
                0,
                lambda i=index, t=total:
                self.show_progress(i, t)
            )

        self.root.after(
            0,
            self.refresh_stock_list
        )

    def show_progress(self, current, total):

        self.result_text.delete("1.0", tk.END)

        self.result_text.insert(
            tk.END,
            f"그룹 분석 중...\n\n"
            f"{current}/{total}"
        )

    

    def add_stock_to_group(self):

        if self.current_group is None:
            messagebox.showwarning(
                "알림",
                "먼저 그룹을 선택하세요."
            )
            return

        selection = self.listbox.curselection()

        if not selection:
            return

        value = self.listbox.get(selection[0])

        code = value.split("(")[-1].replace(")", "")
        name = value.split("(")[0].strip()

        stocks = self.groups[self.current_group]

        for stock in stocks:
            if stock["code"] == code:
                messagebox.showinfo(
                    "알림",
                    "이미 등록된 종목입니다."
                )
                return

        stocks.append({
            "code": code,
            "name": name
        })

        self.save_groups()

        self.stock_list.insert(tk.END, name)

    def delete_stock(self, event=None):

        if self.current_group is None:
            return

        selection = self.stock_list.curselection()

        stock = None

        if selection:
            index = selection[0]

            if index < len(self.display_stocks):
                stock = self.display_stocks[index]

        if stock is None and self.current_stock:
            for item in self.groups.get(self.current_group, []):
                if item.get("code") == self.current_stock:
                    stock = item
                    break

        if stock is None:
            messagebox.showinfo(
                "삭제",
                "삭제할 종목을 먼저 선택하세요."
            )
            return

        code = stock.get("code")

        answer = messagebox.askyesno(
            "삭제",
            f"{stock['name']}을(를) 삭제하시겠습니까?"
        )

        if not answer:
            return

        self.groups[self.current_group] = [
            item
            for item in self.groups.get(self.current_group, [])
            if item.get("code") != code
        ]

        if self.current_stock == code:
            self.current_stock = None
            self.current_result = None

        self.save_groups()
        self.refresh_stock_list()
        self.refresh_portfolio_table(auto_analyze=False)
        self.refresh_briefing_table()
        self.refresh_dashboard()

    def auto_refresh(self):

        try:

            if self.current_group is not None:
                self.refresh_stock_list()

        except Exception as e:
            print("자동 새로고침 오류 :", e)

        self.root.after(self.get_auto_refresh_interval_ms(), self.auto_refresh)

    def load_news(self):

        for row_id in self.news_list.get_children():
            self.news_list.delete(row_id)
        self.current_news = []

        remote_record = getattr(self.current_result, "remote_record", None)

        if isinstance(remote_record, dict) and remote_record.get("news"):
            news = []

            for item in remote_record.get("news", []):
                copied = dict(item)

                if "url" not in copied and copied.get("link"):
                    copied["url"] = copied.get("link")

                news.append(copied)

            self.current_news = news
            self.populate_news_list(news)
            return

        stock = self.service.get_stock(
            self.current_stock,
            "2025",
            "11011"
        )

        if not stock:
            return

        news = self.service.news.get_news(stock.name)
        self.current_news = news
        self.populate_news_list(news)

    def populate_news_list(self, news):
        for item in news:

            date = item.get("date", "")
            title = item.get("title", "")
            impact_label = item.get("impact_label", "중립")
            impact_score = safe_number(item.get("impact_score"))
            event_type = item.get("event_type", "일반 뉴스")
            tag = self.news_impact_tag(impact_score)

            self.news_list.insert(
                "",
                tk.END,
                values=(
                    date,
                    impact_label,
                    f"{impact_score:+.0f}",
                    event_type,
                    title,
                ),
                tags=(tag,)
            )

    def open_selected_news(self, event=None):

        selection = self.news_list.selection()

        if not selection:
            return

        children = list(self.news_list.get_children())
        index = children.index(selection[0])

        if index >= len(self.current_news):
            return

        url = self.current_news[index].get("url")

        if url:
            webbrowser.open(url)

    @staticmethod
    def news_impact_tag(score):

        score = safe_number(score)

        if score >= 4:
            return "good"

        if score <= -4:
            return "bad"

        return "neutral"


