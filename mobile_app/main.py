from __future__ import annotations

import base64
import html
import json
import random
import sys
import time
from datetime import datetime
from pathlib import Path

import flet as ft


APP_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = APP_ROOT / "src"
DEV_STORAGE_DIR = APP_ROOT / "storage"
DEV_WATCHLIST_FILE = DEV_STORAGE_DIR / "watchlist.json"
DEV_HOLDINGS_FILE = DEV_STORAGE_DIR / "holdings.json"
APP_CONFIG_FILE = Path(__file__).resolve().parent / "app_config.json"
DEFAULT_SERVER_URL = "https://stock-z1su.onrender.com"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from morning_stock_assistant.shared.alert_engine import AlertEngine, AlertRules
from morning_stock_assistant.shared.remote_client import RemoteAnalysisClient


def safe_number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def load_json(path: Path, fallback):
    if not path.exists():
        return fallback

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )


class MobileStockApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.storage_dir = self.resolve_storage_dir()
        self.watchlist_file = self.storage_dir / "watchlist.json"
        self.holdings_file = self.storage_dir / "holdings.json"
        self.settings_file = self.storage_dir / "app_settings.json"
        self.backup_dir = self.storage_dir / "backups"
        self.seed_storage_from_dev()
        self.groups = load_json(self.watchlist_file, {})
        self.holdings = load_json(self.holdings_file, {})
        self.app_settings = load_json(self.settings_file, {})
        self.build_config = load_json(APP_CONFIG_FILE, {})
        self.selected_group = next(iter(self.groups), "")
        self.selected_index = 0
        self.briefing_mode = "요약"
        first_stock = self.current_stocks()[0] if self.current_stocks() else {}
        self.selected_chart_code = first_stock.get("code", "")
        self.selected_holding_code = first_stock.get("code", "")
        self.stock_preview = None
        self.stock_search_results = []
        self.chart_period = "1개월"
        self.chart_selected_index = None
        self.chart_selected_price = None
        self.bridge = None
        self.real_records = {}
        self.real_chart_cache = {}
        self.real_data_loaded_at = ""
        self.real_data_error = ""
        self.api_base_url = str(
            self.app_settings.get("api_base_url", DEFAULT_SERVER_URL)
        ).strip()
        self.alerts = []
        self.alert_history = set()
        self.alert_threshold_score = safe_number(
            self.app_settings.get("alert_threshold_score", 75),
            75,
        )
        self.alert_threshold_change = safe_number(
            self.app_settings.get("alert_threshold_change", 5),
            5,
        )
        self.alert_threshold_upside = safe_number(
            self.app_settings.get("alert_threshold_upside", 30),
            30,
        )
        self.alert_threshold_loss = safe_number(
            self.app_settings.get("alert_threshold_loss", -10),
            -10,
        )
        self.alert_threshold_bad_news = safe_number(
            self.app_settings.get("alert_threshold_bad_news", 35),
            35,
        )
        self.analysis_loading = False
        self.analysis_loading_message = ""
        self.analysis_started_at = None
        self.analysis_total = 0
        self.analysis_done = 0
        self.analysis_current = ""
        self.analysis_last_duration = 0
        self.last_progress_update_at = 0.0
        self.global_status_ref = ft.Ref()
        self.home_status_ref = ft.Ref()
        self.settings_status_ref = ft.Ref()
        self.settings_loading_ref = ft.Ref()
        self.progress_bar_ref = ft.Ref()
        self.progress_detail_ref = ft.Ref()
        self.progress_percent_ref = ft.Ref()
        self.progress_overlay_text = ft.Text(
            "",
            size=12,
            color="#2563eb",
            expand=True,
        )
        self.progress_overlay = ft.Container(
            visible=False,
            content=ft.Row(
                [
                    ft.ProgressRing(
                        width=16,
                        height=16,
                        stroke_width=2,
                        color="#2563eb",
                    ),
                    self.progress_overlay_text,
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(14, 10, 14, 10),
            bgcolor="#eff6ff",
            border_radius=8,
            margin=ft.Margin(12, 12, 12, 0),
        )
        self.file_picker = None
        self.auto_refresh_enabled = bool(
            self.app_settings.get("auto_refresh_enabled", True)
        )
        self.auto_refresh_interval_minutes = max(
            1,
            int(safe_number(self.app_settings.get("auto_refresh_interval_minutes", 30), 30)),
        )
        self.auto_refresh_started = False
        self.status_watcher_started = False
        self.last_status_snapshot = None
        self.auto_refresh_last_at = ""
        self.search_code = ft.TextField(
            label="종목 코드",
            hint_text="예: 005930, NVDA",
            dense=True,
            expand=True,
            on_submit=self.search_stock_input,
        )
        self.search_name = ft.TextField(
            label="종목명",
            hint_text="예: 삼성전자, 엔비디아, NVIDIA",
            dense=True,
            expand=True,
            on_submit=self.search_stock_input,
        )
        self.group_name = ft.TextField(
            label="그룹명",
            hint_text="예: 관심종목",
            dense=True,
            expand=True,
        )
        self.holding_quantity = ft.TextField(
            label="수량",
            hint_text="예: 10",
            dense=True,
            keyboard_type=ft.KeyboardType.NUMBER,
            expand=True,
        )
        self.holding_avg_price = ft.TextField(
            label="평균가",
            hint_text="예: 740000 또는 180.36",
            dense=True,
            keyboard_type=ft.KeyboardType.NUMBER,
            expand=True,
        )
        self.alert_score_input = self.number_field(
            "점수 기준",
            self.alert_threshold_score,
        )
        self.alert_change_input = self.number_field(
            "등락률 기준",
            self.alert_threshold_change,
        )
        self.alert_upside_input = self.number_field(
            "목표가 여력",
            self.alert_threshold_upside,
        )
        self.alert_loss_input = self.number_field(
            "보유 손실 기준",
            self.alert_threshold_loss,
        )
        self.alert_bad_news_input = self.number_field(
            "뉴스 경고 기준",
            self.alert_threshold_bad_news,
        )
        self.auto_interval_input = self.number_field(
            "자동 새로고침",
            self.auto_refresh_interval_minutes,
        )
        self.api_base_url_input = ft.TextField(
            label="Render 서버 URL",
            hint_text="https://your-service.onrender.com",
            value=self.api_base_url,
            dense=True,
        )

    def run(self):
        self.page.title = "Morning Stock"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 0
        self.page.bgcolor = "#f7f8fb"
        self.page.window_width = 430
        self.page.window_height = 900
        self.page.navigation_bar = ft.NavigationBar(
            selected_index=self.selected_index,
            on_change=self.on_nav_change,
            destinations=[
                ft.NavigationBarDestination(
                    icon=ft.Icons.HOME_OUTLINED,
                    selected_icon=ft.Icons.HOME,
                    label="홈",
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.STAR_BORDER,
                    selected_icon=ft.Icons.STAR,
                    label="관심",
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.ARTICLE_OUTLINED,
                    selected_icon=ft.Icons.ARTICLE,
                    label="브리핑",
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.SHOW_CHART,
                    label="차트",
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.SETTINGS_OUTLINED,
                    selected_icon=ft.Icons.SETTINGS,
                    label="설정",
                ),
            ],
        )
        if self.progress_overlay not in self.page.overlay:
            self.page.overlay.append(self.progress_overlay)
        if self.file_picker is not None and self.file_picker not in self.page.overlay:
            self.page.overlay.append(self.file_picker)
        self.render()
        self.start_status_watcher()
        self.start_auto_refresh()

    def resolve_storage_dir(self):
        if SRC_DIR.exists() and DEV_STORAGE_DIR.exists():
            return DEV_STORAGE_DIR

        storage_paths = getattr(self.page, "storage_paths", None)
        base_path = None

        for attr in ("app_data", "data", "documents"):
            value = getattr(storage_paths, attr, None) if storage_paths else None

            if value:
                base_path = Path(str(value))
                break

        if base_path is None:
            base_path = Path(__file__).resolve().parent

        return base_path / "storage"

    def seed_storage_from_dev(self):
        if self.storage_dir == DEV_STORAGE_DIR:
            return

        self.storage_dir.mkdir(parents=True, exist_ok=True)

        pairs = [
            (DEV_WATCHLIST_FILE, self.watchlist_file),
            (DEV_HOLDINGS_FILE, self.holdings_file),
        ]

        for source, target in pairs:
            if source.exists() and not target.exists():
                try:
                    target.write_text(
                        source.read_text(encoding="utf-8"),
                        encoding="utf-8",
                    )
                except Exception:
                    pass

    def storage_mode_label(self):
        if self.storage_dir == DEV_STORAGE_DIR:
            return "PC 개발 저장소"

        return "앱 내부 저장소"

    def on_nav_change(self, event):
        self.selected_index = event.control.selected_index
        self.render()

    def render(self):
        views = [
            self.home_view,
            self.watchlist_view,
            self.briefing_view,
            self.chart_view,
            self.settings_view,
        ]
        self.page.navigation_bar.selected_index = self.selected_index
        self.page.clean()
        self.page.add(
            ft.SafeArea(
                ft.Column(
                    [
                        self.global_refresh_status_bar(),
                        ft.Container(
                            content=views[self.selected_index](),
                            padding=ft.Padding(16, 12, 16, 12),
                            expand=True,
                        ),
                    ],
                    spacing=0,
                    expand=True,
                ),
                expand=True,
            )
        )
        self.page.update()

    def global_refresh_status_bar(self):
        if not self.analysis_loading and not self.analysis_loading_message:
            return ft.Container(height=0)

        text, color = self.current_analysis_status()
        bg = "#eff6ff" if self.analysis_loading else "#f0fdf4"

        return ft.Container(
            content=ft.Row(
                [
                    *(
                        [
                            ft.ProgressRing(
                                width=16,
                                height=16,
                                stroke_width=2,
                                color="#2563eb",
                            )
                        ]
                        if self.analysis_loading
                        else [ft.Icon(ft.Icons.CHECK_CIRCLE, color="#16a34a", size=18)]
                    ),
                    ft.Text(text, ref=self.global_status_ref, size=12, color=color, expand=True),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(16, 8, 16, 8),
            bgcolor=bg,
        )

    def header(self, title, subtitle=None):
        controls = [
            ft.Text(
                title,
                size=25,
                weight=ft.FontWeight.BOLD,
                color="#111827",
            )
        ]

        if subtitle:
            controls.append(
                ft.Text(subtitle, size=13, color="#64748b")
            )

        return ft.Column(controls, spacing=4)

    def card(self, content, padding=16, bgcolor="#ffffff"):
        return ft.Container(
            content=content,
            padding=padding,
            bgcolor=bgcolor,
            border_radius=14,
            border=ft.Border(
                left=ft.BorderSide(1, "#eef2f7"),
                top=ft.BorderSide(1, "#eef2f7"),
                right=ft.BorderSide(1, "#eef2f7"),
                bottom=ft.BorderSide(1, "#eef2f7"),
            ),
        )

    def primary_button(self, text, on_click):
        return ft.Container(
            content=ft.Text(text, color="#ffffff", weight=ft.FontWeight.BOLD),
            padding=ft.Padding(16, 10, 16, 10),
            bgcolor="#2563eb",
            border_radius=10,
            ink=True,
            on_click=on_click,
        )

    def secondary_button(self, text, on_click):
        return ft.Container(
            content=ft.Text(text, color="#334155", weight=ft.FontWeight.BOLD),
            padding=ft.Padding(16, 10, 16, 10),
            bgcolor="#ffffff",
            border_radius=10,
            border=ft.Border(
                left=ft.BorderSide(1, "#dbe4ef"),
                top=ft.BorderSide(1, "#dbe4ef"),
                right=ft.BorderSide(1, "#dbe4ef"),
                bottom=ft.BorderSide(1, "#dbe4ef"),
            ),
            ink=True,
            on_click=on_click,
        )

    def number_field(self, label, value):
        return ft.TextField(
            label=label,
            value=f"{safe_number(value):g}",
            dense=True,
            keyboard_type=ft.KeyboardType.NUMBER,
            expand=True,
        )

    def chip_button(self, text, selected, on_click):
        return ft.Container(
            content=ft.Text(
                text,
                color="#ffffff" if selected else "#334155",
                weight=ft.FontWeight.BOLD if selected else None,
                size=12,
            ),
            padding=ft.Padding(12, 8, 12, 8),
            bgcolor="#111827" if selected else "#eef2f7",
            border_radius=18,
            ink=True,
            on_click=on_click,
        )

    def current_stocks(self):
        return self.groups.get(self.selected_group, [])

    def score_for(self, code):
        record = self.real_record(code)

        if record:
            return safe_number(record.get("quant_score", 0))

        seed = sum(ord(ch) for ch in code)
        random.seed(seed)
        return round(48 + random.random() * 42, 1)

    def news_score_for(self, code):
        record = self.real_record(code)

        if record:
            return safe_number(record.get("news_score", 0))

        seed = sum(ord(ch) for ch in f"news:{code}")
        rng = random.Random(seed)
        return round(44 + rng.random() * 44, 1)

    def final_score_for(self, code):
        record = self.real_record(code)

        if record:
            return safe_number(record.get("final_score", 0))

        quant = self.score_for(code)
        news = self.news_score_for(code)
        return round((quant * 0.7) + (news * 0.3), 1)

    def real_record(self, code):
        return self.real_records.get(str(code or "").upper())

    def grade_for(self, score):
        if score >= 85:
            return "STRONG BUY"
        if score >= 72:
            return "BUY"
        if score >= 55:
            return "HOLD"
        if score >= 40:
            return "REDUCE"
        return "SELL"

    def stock_detail_text(self, record):
        if not record:
            return ""

        price = self.format_price(
            record.get("code", ""),
            safe_number(record.get("price", 0)),
            record.get("currency", "KRW"),
        )
        date = record.get("price_date") or "-"
        freshness = record.get("freshness_label") or "확인불가"
        change = safe_number(record.get("change_1d", 0))

        return f"{price} | {change:+.2f}% | {date} {freshness}"

    def data_quality_text(self, record):
        if not record:
            return "실제 데이터 없음"

        price_date = record.get("price_date") or "-"
        freshness = record.get("freshness_label") or "확인불가"
        freshness_days = safe_number(record.get("freshness_days", -1), -1)
        market = record.get("market") or ("국내" if str(record.get("code", "")).isdigit() else "해외")
        price_source = "Yahoo/KRX 보조" if market == "국내" else "Yahoo Finance"
        finance_source = "네이버/야후/거래소 보조"
        warning = ""

        if freshness_days >= 3:
            warning = " | 오래된 가격 주의"
        elif freshness_days < 0:
            warning = " | 기준일 확인 필요"

        return (
            f"가격 {price_date} {freshness}{warning} | "
            f"가격출처 {price_source} | 재무출처 {finance_source}"
        )

    def news_meta_text(self, news_items):
        if not news_items:
            return "뉴스 기준일 없음 | 출처 없음"

        dates = [
            str(item.get("date") or "").strip()
            for item in news_items
            if str(item.get("date") or "").strip()
        ]
        sources = []

        for item in news_items:
            source = str(item.get("source") or "").strip()

            if source and source not in sources:
                sources.append(source)

        latest = dates[0] if dates else "-"
        source_text = ", ".join(sources[:3]) if sources else "검색 뉴스"
        return f"뉴스 기준일 {latest} | 출처 {source_text}"

    def data_warning_color(self, record):
        if not record:
            return "#94a3b8"

        freshness_days = safe_number(record.get("freshness_days", -1), -1)

        if freshness_days >= 3:
            return "#ef4444"

        if freshness_days < 0:
            return "#f59e0b"

        return "#64748b"

    def target_text(self, record):
        if not record:
            return ""

        target = safe_number(record.get("target_price", 0))

        if target <= 0:
            return ""

        code = record.get("code", "")
        currency = record.get("currency", "KRW")
        upside = safe_number(record.get("target_upside", 0))
        target_price = self.format_price(code, target, currency)

        return f"목표가 {target_price} ({upside:+.1f}%)"

    def group_dropdown(self):
        return ft.Dropdown(
            label="그룹",
            value=self.selected_group if self.selected_group else None,
            options=[
                ft.dropdown.Option(name)
                for name in self.groups
            ],
            on_select=self.on_group_change,
            dense=True,
        )

    def on_group_change(self, event):
        self.selected_group = event.control.value or ""
        self.stock_preview = None
        self.render()

    def home_view(self):
        stocks = self.current_stocks()
        ranked = sorted(
            stocks,
            key=lambda item: self.final_score_for(item.get("code", "")),
            reverse=True,
        )
        best = ranked[0] if ranked else None
        best_score = self.final_score_for(best["code"]) if best else 0
        holdings_krw, holdings_usd = self.estimated_holding_values()

        return ft.Column(
            [
                self.header(
                    "Morning Stock",
                    f"{datetime.now():%Y.%m.%d} 모바일 대시보드",
                ),
                self.home_refresh_panel(),
                self.refresh_progress_panel(),
                self.group_dropdown(),
                ft.Row(
                    [
                        self.metric_card("관심종목", f"{len(stocks)}개"),
                        self.metric_card(
                            "최고 점수",
                            f"{best_score:.1f}" if best else "-",
                        ),
                    ],
                    spacing=10,
                ),
                ft.Row(
                    [
                        self.metric_card("보유 원화", f"{holdings_krw:,.0f}원"),
                        self.metric_card("보유 달러", f"${holdings_usd:,.2f}"),
                    ],
                    spacing=10,
                ),
                self.alert_panel(),
                self.portfolio_feedback_panel(),
                ft.Text("점수 상위", weight=ft.FontWeight.BOLD, size=16),
                ft.Column(
                    [
                        self.stock_tile(item)
                        for item in ranked[:6]
                    ]
                    or [self.empty_state("관심종목을 추가하세요.")],
                    spacing=8,
                ),
                ft.Text("보유종목 요약", weight=ft.FontWeight.BOLD, size=16),
                ft.Column(
                    self.holding_tiles()
                    or [self.empty_state("보유종목 정보가 없습니다.")],
                    spacing=8,
                ),
            ],
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
        )

    def metric_card(self, title, value, wide=False):
        return self.card(
            ft.Column(
                [
                    ft.Text(title, size=12, color="#64748b"),
                    ft.Text(
                        value,
                        size=22 if wide else 20,
                        weight=ft.FontWeight.BOLD,
                        color="#111827",
                    ),
                ],
                spacing=4,
            ),
            padding=14,
        )

    def home_refresh_panel(self):
        if self.analysis_loading:
            status, color = self.current_analysis_status()
            action = ft.ProgressRing(
                width=22,
                height=22,
                stroke_width=3,
                color="#2563eb",
            )
        else:
            status, color = self.current_analysis_status()
            action = self.secondary_button("새로고침", self.load_real_analysis)

        return self.card(
            ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text("실시간 데이터", weight=ft.FontWeight.BOLD),
                            ft.Text(status, ref=self.home_status_ref, size=12, color=color),
                            ft.Text(
                                "자동 새로고침 켜짐"
                                if self.auto_refresh_enabled
                                else "자동 새로고침 꺼짐",
                                size=11,
                                color="#94a3b8",
                            ),
                        ],
                        expand=True,
                        spacing=2,
                    ),
                    action,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=12,
            bgcolor="#f8fafc",
        )

    def refresh_progress_panel(self):
        if not self.analysis_loading and not self.analysis_loading_message:
            if not self.analysis_last_duration:
                return ft.Container(height=0)

            return self.card(
                ft.Row(
                    [
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color="#16a34a"),
                        ft.Text(
                            f"마지막 새로고침 소요 시간 {self.analysis_last_duration}초",
                            size=12,
                            color="#16a34a",
                            expand=True,
                        ),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=12,
                bgcolor="#f0fdf4",
            )

        progress = self.analysis_progress_value()
        percent = int(progress * 100)
        elapsed = self.analysis_elapsed_seconds()
        detail = self.analysis_current or self.analysis_loading_message

        return self.card(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.ProgressRing(
                                width=18,
                                height=18,
                                stroke_width=2,
                                color="#2563eb",
                            ),
                            ft.Text(
                                "새로고침 진행 중",
                                weight=ft.FontWeight.BOLD,
                                color="#111827",
                                expand=True,
                            ),
                            ft.Text(
                                f"{percent}%",
                                ref=self.progress_percent_ref,
                                size=12,
                                color="#2563eb",
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.ProgressBar(
                        value=progress,
                        ref=self.progress_bar_ref,
                        color="#2563eb",
                        bgcolor="#dbeafe",
                    ),
                    ft.Text(
                        f"{detail} | {elapsed}초 경과",
                        ref=self.progress_detail_ref,
                        size=12,
                        color="#64748b",
                    ),
                ],
                spacing=8,
            ),
            padding=12,
            bgcolor="#eff6ff",
        )

    def analysis_progress_value(self):
        if self.analysis_total <= 0:
            return None

        return min(max(self.analysis_done / self.analysis_total, 0), 1)

    def alert_panel(self):
        if not self.alerts:
            return self.card(
                ft.Row(
                    [
                        ft.Icon(ft.Icons.NOTIFICATIONS_NONE, color="#94a3b8"),
                        ft.Text(
                            "아직 감지된 알림이 없습니다.",
                            size=12,
                            color="#64748b",
                            expand=True,
                        ),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=12,
                bgcolor="#f8fafc",
            )

        return self.card(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE, color="#2563eb"),
                            ft.Text("실시간 알림", weight=ft.FontWeight.BOLD, expand=True),
                            ft.Text(
                                f"{len(self.alerts)}건",
                                size=12,
                                color="#64748b",
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    self.alert_summary_row(),
                    ft.Column(
                        [self.alert_tile(alert) for alert in self.alerts[:4]],
                        spacing=8,
                    ),
                    *(
                        [
                            ft.Text(
                                f"외 {len(self.alerts) - 4}건의 알림이 더 있습니다.",
                                size=11,
                                color="#94a3b8",
                            )
                        ]
                        if len(self.alerts) > 4
                        else []
                    ),
                    ft.Row(
                        [
                            self.secondary_button("알림 비우기", self.clear_alerts),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
                spacing=10,
            ),
            padding=12,
            bgcolor="#f8fafc",
        )

    def alert_summary_row(self):
        danger = sum(1 for alert in self.alerts if alert.get("level") == "danger")
        watch = sum(1 for alert in self.alerts if alert.get("level") == "watch")
        good = sum(1 for alert in self.alerts if alert.get("level") == "good")

        return ft.Row(
            [
                self.alert_count_chip("위험", danger, "#ef4444"),
                self.alert_count_chip("주의", watch, "#f59e0b"),
                self.alert_count_chip("긍정", good, "#16a34a"),
            ],
            spacing=6,
            wrap=True,
        )

    @staticmethod
    def alert_count_chip(label, count, color):
        return ft.Container(
            content=ft.Text(
                f"{label} {count}",
                size=11,
                color=color,
                weight=ft.FontWeight.BOLD,
            ),
            padding=ft.Padding(8, 5, 8, 5),
            border_radius=12,
            bgcolor="#ffffff",
            border=ft.Border(
                left=ft.BorderSide(1, color),
                top=ft.BorderSide(1, color),
                right=ft.BorderSide(1, color),
                bottom=ft.BorderSide(1, color),
            ),
        )

    def clear_alerts(self, _=None):
        self.alerts = []
        self.alert_history = set()
        self.snack("알림을 비웠습니다.")
        self.render()

    def alert_tile(self, alert):
        level = alert.get("level", "info")
        color = {
            "danger": "#ef4444",
            "good": "#16a34a",
            "watch": "#f59e0b",
        }.get(level, "#2563eb")

        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        width=8,
                        height=8,
                        border_radius=4,
                        bgcolor=color,
                    ),
                    ft.Column(
                        [
                            ft.Text(
                                alert.get("title", "알림"),
                                weight=ft.FontWeight.BOLD,
                                size=13,
                                color="#111827",
                            ),
                            ft.Text(
                                alert.get("message", ""),
                                size=12,
                                color="#64748b",
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.Text(alert.get("time", ""), size=11, color="#94a3b8"),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=10,
            border_radius=8,
            bgcolor="#ffffff",
        )

    def stock_tile(self, item):
        code = item.get("code", "")
        name = item.get("name", code)
        score = self.final_score_for(code)
        grade = self.grade_for(score)
        color = "#ef4444" if score >= 72 else "#2563eb" if score < 55 else "#64748b"
        holding = self.holding_text(code)
        record = self.real_record(code)
        detail = self.stock_detail_text(record)
        target = self.target_text(record)

        return self.card(
            ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(name, weight=ft.FontWeight.BOLD, size=15),
                            ft.Text(code, size=12, color="#64748b"),
                            *(
                                [ft.Text(detail, size=11, color="#64748b")]
                                if detail
                                else []
                            ),
                            *(
                                [
                                    ft.Text(
                                        self.data_quality_text(record),
                                        size=11,
                                        color=self.data_warning_color(record),
                                    )
                                ]
                                if record
                                else []
                            ),
                            *(
                                [ft.Text(target, size=11, color="#ef4444")]
                                if target
                                else []
                            ),
                            *(
                                [ft.Text(holding, size=11, color="#64748b")]
                                if holding
                                else []
                            ),
                        ],
                        expand=True,
                        spacing=2,
                    ),
                    ft.Column(
                        [
                            ft.Text(
                                f"{score:.1f}",
                                weight=ft.FontWeight.BOLD,
                                color=color,
                                text_align=ft.TextAlign.RIGHT,
                            ),
                            ft.Text(grade, size=11, color="#64748b"),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                        spacing=2,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=13,
        )

    def watchlist_view(self):
        return ft.Column(
            [
                self.header("관심종목", "PC 버전의 watchlist.json을 읽습니다."),
                self.group_dropdown(),
                self.group_editor(),
                self.card(
                    ft.Column(
                        [
                            ft.Row(
                                [self.search_name, self.search_code],
                                spacing=8,
                            ),
                            ft.Row(
                                [
                                    self.primary_button("검색", self.search_stock_input),
                                    self.secondary_button("직접 추가", self.add_stock),
                                    self.secondary_button(
                                        "새로고침",
                                        lambda _: self.reload_data(),
                                    ),
                                ],
                                spacing=8,
                            ),
                            self.stock_search_results_panel(),
                        ],
                        spacing=10,
                    )
                ),
                ft.Column(
                    [
                        self.stock_tile_with_delete(item)
                        for item in self.current_stocks()
                    ]
                    or [self.empty_state("현재 그룹에 종목이 없습니다.")],
                    spacing=8,
                ),
                self.holding_editor(),
            ],
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
        )

    def group_editor(self):
        return self.card(
            ft.Column(
                [
                    ft.Text("그룹 관리", weight=ft.FontWeight.BOLD, size=16),
                    ft.Row(
                        [self.group_name],
                        spacing=8,
                    ),
                    ft.Row(
                        [
                            self.primary_button("그룹 추가", self.add_group),
                            self.secondary_button("현재 그룹 삭제", self.delete_group),
                        ],
                        spacing=8,
                    ),
                ],
                spacing=10,
            )
        )

    def stock_tile_with_delete(self, item):
        code = item.get("code", "")
        row = self.stock_tile(item)
        return ft.Row(
            [
                ft.Container(row, expand=True),
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    icon_color="#94a3b8",
                    tooltip="삭제",
                    on_click=lambda _, c=code: self.delete_stock(c),
                ),
            ],
            spacing=4,
        )

    def stock_preview_panel(self):
        if not self.stock_preview:
            return ft.Container(height=0)

        preview = self.stock_preview
        ok = preview.get("ok", False)
        color = "#16a34a" if ok else "#ef4444"
        icon = ft.Icons.CHECK_CIRCLE if ok else ft.Icons.ERROR_OUTLINE

        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(icon, color=color),
                            ft.Text(preview.get("title", "종목 미리보기"), weight=ft.FontWeight.BOLD, expand=True),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Text(preview.get("message", ""), size=12, color="#334155"),
                    *(
                        [
                            ft.Row(
                                [
                                    self.primary_button("이 종목 추가", self.add_preview_stock),
                                    self.secondary_button("취소", self.clear_stock_preview),
                                ],
                                spacing=8,
                            )
                        ]
                        if ok
                        else []
                    ),
                ],
                spacing=8,
            ),
            padding=12,
            border_radius=10,
            bgcolor="#f8fafc",
        )

    def stock_search_results_panel(self):
        if not self.stock_search_results:
            return ft.Container(height=0)

        rows = []

        for result in self.stock_search_results[:12]:
            code = result.get("code", "")
            name = result.get("name") or code
            market = result.get("market") or ("국내" if str(code).isdigit() else "해외")
            duplicate = any(
                item.get("code") == code
                for item in self.groups.get(self.selected_group, [])
            )

            rows.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(
                                        name,
                                        weight=ft.FontWeight.BOLD,
                                        color="#0f172a",
                                    ),
                                    ft.Text(
                                        f"{code} | {market}",
                                        size=12,
                                        color="#64748b",
                                    ),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            (
                                ft.Text("추가됨", size=12, color="#94a3b8")
                                if duplicate
                                else self.secondary_button(
                                    "추가",
                                    lambda _, item=result: self.add_search_result_stock(item),
                                )
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=10,
                    border_radius=8,
                    bgcolor="#ffffff",
                )
            )

        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("검색 결과", weight=ft.FontWeight.BOLD, expand=True),
                            self.secondary_button("닫기", self.clear_stock_search_results),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Column(rows, spacing=6),
                ],
                spacing=8,
            ),
            padding=12,
            border_radius=10,
            bgcolor="#f8fafc",
        )

    def holding_editor(self):
        stocks = self.current_stocks()

        if stocks and not any(
            item.get("code") == self.selected_holding_code for item in stocks
        ):
            self.selected_holding_code = stocks[0].get("code", "")

        self.sync_holding_inputs()

        return self.card(
            ft.Column(
                [
                    ft.Text("보유종목 입력", weight=ft.FontWeight.BOLD, size=16),
                    ft.Dropdown(
                        label="종목",
                        value=self.selected_holding_code or None,
                        options=[
                            ft.dropdown.Option(
                                key=item.get("code", ""),
                                text=f"{item.get('name', item.get('code', ''))} ({item.get('code', '')})",
                            )
                            for item in stocks
                        ],
                        on_select=self.on_holding_code_change,
                        dense=True,
                    ),
                    ft.Row(
                        [self.holding_quantity, self.holding_avg_price],
                        spacing=8,
                    ),
                    ft.Row(
                        [
                            self.primary_button("저장", self.save_holding),
                            self.secondary_button("보유 삭제", self.delete_holding),
                        ],
                        spacing=8,
                    ),
                ],
                spacing=10,
            )
        )

    def briefing_view(self):
        records = [
            {
                "item": item,
                "score": self.score_for(item.get("code", "")),
                "news_score": self.news_score_for(item.get("code", "")),
                "final_score": self.final_score_for(item.get("code", "")),
                "real": self.real_record(item.get("code", "")),
            }
            for item in self.current_stocks()
        ]
        records.sort(key=lambda item: item["final_score"], reverse=True)
        domestic = [
            record for record in records
            if record["item"].get("code", "").isdigit()
        ]
        overseas = [
            record for record in records
            if not record["item"].get("code", "").isdigit()
        ]

        return ft.Column(
            [
                self.header(
                    "AI 퀀트 브리핑",
                    "요약, 뉴스, 재무를 한 화면에서 전환",
                ),
                self.group_dropdown(),
                self.briefing_share_panel(records),
                self.briefing_mode_selector(),
                *self.briefing_mode_content(records, domestic, overseas),
            ],
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
        )

    def briefing_share_panel(self, records):
        return self.card(
            ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text("브리핑 공유", weight=ft.FontWeight.BOLD),
                            ft.Text(
                                "현재 그룹 요약을 텍스트로 복사합니다.",
                                size=12,
                                color="#64748b",
                            ),
                        ],
                        expand=True,
                        spacing=2,
                    ),
                    self.secondary_button("요약 복사", lambda _: self.copy_briefing(records)),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=12,
            bgcolor="#f8fafc",
        )

    def briefing_mode_selector(self):
        return ft.Row(
            [
                self.chip_button(
                    mode,
                    self.briefing_mode == mode,
                    lambda _, m=mode: self.set_briefing_mode(m),
                )
                for mode in ["요약", "뉴스", "재무"]
            ],
            spacing=8,
            wrap=True,
        )

    def set_briefing_mode(self, mode):
        self.briefing_mode = mode
        self.render()

    def copy_briefing(self, records):
        text = self.build_briefing_text(records)

        try:
            clipboard = self.page.clipboard

            if hasattr(clipboard, "set_text"):
                clipboard.set_text(text)
            elif hasattr(clipboard, "set"):
                clipboard.set(text)
            else:
                self.page.set_clipboard(text)
        except Exception as exc:
            self.snack(f"브리핑 복사 실패: {exc}")
            return

        self.snack("브리핑 요약을 복사했습니다.")

    def build_briefing_text(self, records):
        lines = [
            f"AI 퀀트 브리핑 - {datetime.now():%Y-%m-%d %H:%M}",
            f"그룹: {self.selected_group or '-'}",
            "",
            "| 종목 | 현재가 | 1일 | 점수 | 등급 | 요약 |",
            "|---|---:|---:|---:|---|---|",
        ]

        for record in records:
            item = record["item"]
            code = item.get("code", "")
            name = item.get("name", code)
            real = record.get("real")
            final_score = record["final_score"]
            grade = real.get("grade") if real else self.grade_for(final_score)

            if real:
                price = self.format_price(
                    code,
                    safe_number(real.get("price", 0)),
                    real.get("currency", None),
                )
                change = f"{safe_number(real.get('change_1d', 0)):+.2f}%"
                summary = real.get("comment") or self.briefing_comment(
                    record["score"],
                    record["news_score"],
                    final_score,
                )
            else:
                price = "-"
                change = "-"
                summary = self.briefing_comment(
                    record["score"],
                    record["news_score"],
                    final_score,
                )

            summary = str(summary).replace("|", "/")
            lines.append(
                f"| {name} `{code}` | {price} | {change} | "
                f"{final_score:.1f} | {grade} | {summary} |"
            )

        lines.extend([
            "",
            "데이터 안내:",
            f"- 실제 데이터 갱신: {self.real_data_loaded_at or '아직 없음'}",
            "- 투자 판단 참고용이며 투자자문이 아닙니다.",
        ])
        return "\n".join(lines)

    def briefing_mode_content(self, records, domestic, overseas):
        if self.briefing_mode == "뉴스":
            return [
                self.real_data_hint(),
                self.news_content(),
            ]

        if self.briefing_mode == "재무":
            return [
                self.real_data_hint(),
                self.finance_content(),
            ]

        return [
            self.card(
                ft.Column(
                    [
                        ft.Text(
                            f"생성시각 {datetime.now():%Y-%m-%d %H:%M}",
                            size=12,
                            color="#64748b",
                        ),
                        ft.Text(
                            "퀀트 70% + 뉴스 30% 기준 모바일 요약입니다.",
                            size=13,
                            color="#334155",
                        ),
                    ],
                    spacing=6,
                ),
                bgcolor="#eef6ff",
            ),
            ft.Text("최종 등급표", weight=ft.FontWeight.BOLD, size=16),
            self.grade_summary(records),
            self.briefing_section("국내 종목", domestic),
            self.briefing_section("해외 종목", overseas),
        ]

    def grade_summary(self, records):
        grouped = {}

        for record in records:
            grouped.setdefault(
                self.grade_for(record["final_score"]),
                [],
            ).append(record["item"].get("name", record["item"].get("code", "")))

        rows = []

        for grade in ("STRONG BUY", "BUY", "HOLD", "REDUCE", "SELL"):
            names = grouped.get(grade)

            if names:
                rows.append(
                    ft.Text(
                        f"{grade}: {', '.join(names[:5])}",
                        size=13,
                        color="#334155",
                    )
                )

        return self.card(
            ft.Column(rows or [ft.Text("-", color="#64748b")], spacing=6)
        )

    def briefing_section(self, title, records):
        return ft.Column(
            [
                ft.Text(title, weight=ft.FontWeight.BOLD, size=16),
                ft.Column(
                    [
                        self.briefing_tile(record)
                        for record in records
                    ]
                    or [self.empty_state("해당 종목이 없습니다.")],
                    spacing=8,
                ),
            ],
            spacing=8,
        )

    def briefing_tile(self, record):
        item = record["item"]
        quant_score = record["score"]
        news_score = record["news_score"]
        final_score = record["final_score"]
        code = item.get("code", "")
        real = record.get("real")
        grade = real.get("grade") if real else self.grade_for(final_score)
        market = "국내" if code.isdigit() else "해외"
        holding = self.holding_text(code)
        real_line = self.stock_detail_text(real)
        target = self.target_text(real)
        analyst = real.get("analyst") if real else ""
        score_reason = real.get("score_reason", "") if real else ""
        factor_text = self.factor_score_text(real) if real else ""
        comment = (
            real.get("comment")
            if real
            else self.briefing_comment(quant_score, news_score, final_score)
        )

        return self.card(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(
                                f"{item.get('name', code)} ({code})",
                                weight=ft.FontWeight.BOLD,
                                expand=True,
                            ),
                            ft.Text(
                                grade,
                                color="#ef4444" if final_score >= 72 else "#2563eb",
                                weight=ft.FontWeight.BOLD,
                            ),
                        ]
                    ),
                    ft.Text(
                        f"{market} | 퀀트 {quant_score:.1f} | 뉴스 {news_score:.1f} | 평균 {final_score:.1f}",
                        size=12,
                        color="#64748b",
                    ),
                    *(
                        [ft.Text(score_reason, size=11, color="#475569")]
                        if score_reason
                        else []
                    ),
                    *(
                        [ft.Text(factor_text, size=11, color="#64748b")]
                        if factor_text
                        else []
                    ),
                    *(
                        [ft.Text(real_line, size=12, color="#64748b")]
                        if real_line
                        else []
                    ),
                    *(
                        [
                            ft.Text(
                                self.data_quality_text(real),
                                size=11,
                                color=self.data_warning_color(real),
                            )
                        ]
                        if real
                        else []
                    ),
                    *(
                        [ft.Text(target, size=12, color="#ef4444", weight=ft.FontWeight.BOLD)]
                        if target
                        else []
                    ),
                    *(
                        [ft.Text(f"애널리스트: {analyst}", size=12, color="#334155")]
                        if analyst and analyst != "-"
                        else []
                    ),
                    ft.Text(
                        comment,
                        size=12,
                        color="#334155",
                    ),
                    *(
                        [ft.Text(holding, size=12, color="#334155")]
                        if holding
                        else []
                    ),
                ],
                spacing=6,
            ),
            padding=13,
        )

    def factor_score_text(self, record):
        factor_scores = (record or {}).get("factor_scores") or {}

        if not factor_scores:
            return ""

        labels = {
            "value": "가치",
            "quality": "품질",
            "growth": "성장",
            "stability": "안정",
            "momentum": "추세",
            "dividend": "배당",
        }
        parts = []

        for key in ["value", "quality", "growth", "stability", "momentum", "dividend"]:
            if key in factor_scores:
                parts.append(
                    f"{labels[key]} {safe_number(factor_scores.get(key, 0)):.1f}"
                )

        return "팩터 | " + " · ".join(parts) if parts else ""

    def briefing_comment(self, quant_score, news_score, final_score):
        if final_score >= 85:
            return "가격 흐름과 뉴스 흐름이 모두 강한 편이라 적극 관심 구간입니다."
        if final_score >= 72:
            return "긍정 신호가 우세하지만 변동성과 가격 부담은 같이 확인해야 합니다."
        if quant_score >= 72 > news_score:
            return "가격 지표는 괜찮지만 뉴스 흐름이 아직 점수를 눌러 보수적으로 봅니다."
        if news_score >= 72 > quant_score:
            return "뉴스는 긍정적이나 가격/재무 신호 확인 전까지 추격은 신중합니다."
        if final_score >= 55:
            return "중립권입니다. 추세 전환이나 추가 호재 확인이 필요합니다."

        return "위험 신호가 더 커서 관망 또는 비중 축소 검토 구간입니다."

    def news_view(self):
        return ft.Column(
            [
                self.header("뉴스", "호재/악재와 날짜를 종목별로 확인"),
                self.group_dropdown(),
                self.real_data_hint(),
                self.news_content(),
            ],
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
        )

    def news_content(self):
        records = self.records_for_current_group()

        return ft.Column(
            [
                self.news_stock_card(item, record)
                for item, record in records
            ]
            or [self.empty_state("뉴스를 볼 종목이 없습니다.")],
            spacing=10,
        )

    def news_stock_card(self, item, record):
        code = item.get("code", "")
        name = item.get("name", code)
        news_items = record.get("news", []) if record else []
        score = self.news_score_for(code)

        if not news_items:
            news_items = self.sample_news_items(code, name)

        return self.card(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(name, weight=ft.FontWeight.BOLD),
                                    ft.Text(code, size=12, color="#64748b"),
                                ],
                                expand=True,
                                spacing=2,
                            ),
                            ft.Text(
                                f"뉴스 {score:.1f}",
                                color="#ef4444" if score >= 65 else "#2563eb",
                                weight=ft.FontWeight.BOLD,
                            ),
                        ]
                    ),
                    ft.Text(
                        self.news_meta_text(news_items),
                        size=11,
                        color="#64748b",
                    ),
                    self.news_summary_box(news_items),
                    ft.Column(
                        [
                            self.news_item_row(news)
                            for news in news_items[:5]
                        ],
                        spacing=8,
                    ),
                ],
                spacing=10,
            )
        )

    def news_summary_box(self, news_items):
        summary = self.ai_news_group_summary(news_items)
        color = {
            "호재 우세": "#16a34a",
            "악재 우세": "#ef4444",
            "중립": "#64748b",
        }.get(summary["tone"], "#64748b")

        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("AI 뉴스 요약", weight=ft.FontWeight.BOLD, expand=True),
                            ft.Text(
                                summary["tone"],
                                size=12,
                                color=color,
                                weight=ft.FontWeight.BOLD,
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Text(summary["summary"], size=12, color="#334155"),
                    ft.Text(summary["watch"], size=12, color="#64748b"),
                ],
                spacing=5,
            ),
            padding=12,
            border_radius=8,
            bgcolor="#f8fafc",
        )

    def news_item_row(self, news):
        label = news.get("impact_label") or "중립"
        impact_score = safe_number(news.get("impact_score", 0))
        color = {
            "강한 호재": "#16a34a",
            "호재": "#ef4444",
            "강한 악재": "#dc2626",
            "악재": "#2563eb",
            "중립": "#64748b",
        }.get(label, "#64748b")
        date = news.get("date") or "-"
        summary = self.ai_news_summary(
            news.get("title") or "",
            label,
            impact_score,
            date if date != "-" else "",
        )

        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(date, size=11, color="#94a3b8"),
                            ft.Text(label, size=11, color=color, weight=ft.FontWeight.BOLD),
                        ],
                        spacing=8,
                    ),
                    ft.Text(
                        news.get("title") or "-",
                        size=13,
                        color="#111827",
                    ),
                    ft.Text(summary, size=12, color="#334155"),
                    *(
                        [ft.Text(news.get("source"), size=11, color="#94a3b8")]
                        if news.get("source")
                        else []
                    ),
                ],
                spacing=3,
            ),
            padding=ft.Padding(0, 2, 0, 2),
        )

    def sample_news_items(self, code, name):
        score = self.news_score_for(code)
        label = "호재" if score >= 65 else "악재" if score <= 40 else "중립"

        return [
            {
                "date": "-",
                "impact_label": label,
                "title": f"{name} 실제 뉴스는 설정에서 실제 분석 데이터를 불러오면 표시됩니다.",
                "source": "모바일 안내",
            }
        ]

    def ai_news_group_summary(self, news_items):
        valid_items = [
            item for item in news_items
            if item.get("title")
        ]

        if not valid_items:
            return {
                "tone": "중립",
                "summary": "확인된 뉴스가 부족해 방향성을 판단하기 어렵습니다.",
                "watch": "새로고침 후 최신 뉴스와 가격 반응을 같이 확인하세요.",
            }

        impact_sum = sum(
            safe_number(item.get("impact_score", 0))
            for item in valid_items
        )
        positive_count = sum(
            1 for item in valid_items
            if "호재" in str(item.get("impact_label", ""))
            or safe_number(item.get("impact_score", 0)) >= 4
        )
        negative_count = sum(
            1 for item in valid_items
            if "악재" in str(item.get("impact_label", ""))
            or safe_number(item.get("impact_score", 0)) <= -4
        )
        keywords = self.news_keywords(valid_items)

        if impact_sum >= 8 or positive_count > negative_count:
            tone = "호재 우세"
            summary = (
                f"긍정 뉴스 {positive_count}건이 우세합니다. "
                f"{keywords} 관련 기대가 점수에 우호적으로 반영됩니다."
            )
            watch = "다만 실제 주가가 거래량을 동반해 따라오는지 확인하는 구간입니다."
        elif impact_sum <= -8 or negative_count > positive_count:
            tone = "악재 우세"
            summary = (
                f"부정 뉴스 {negative_count}건이 우세합니다. "
                f"{keywords} 이슈가 단기 리스크로 작용할 수 있습니다."
            )
            watch = "가격 하락이 멈추는지와 추가 악재가 이어지는지 먼저 확인하세요."
        else:
            tone = "중립"
            summary = (
                f"호재와 악재가 섞여 있습니다. "
                f"{keywords} 흐름은 아직 방향성이 강하지 않습니다."
            )
            watch = "뉴스보다 가격 추세와 재무 지표를 함께 보고 판단하는 편이 좋습니다."

        return {
            "tone": tone,
            "summary": summary,
            "watch": watch,
        }

    @staticmethod
    def news_keywords(news_items):
        buckets = [
            ("실적", ["실적", "매출", "영업이익", "순이익", "earnings", "revenue"]),
            ("수주", ["수주", "계약", "공급", "order", "contract"]),
            ("AI", ["ai", "인공지능", "데이터센터", "반도체", "hbm"]),
            ("규제", ["규제", "소송", "조사", "제재", "antitrust", "lawsuit"]),
            ("투자", ["투자", "증설", "capex", "facility"]),
            ("목표가", ["목표가", "상향", "하향", "upgrade", "downgrade"]),
        ]
        text = " ".join(
            str(item.get("title", "")).lower()
            for item in news_items
        )
        matched = [
            label for label, words in buckets
            if any(word.lower() in text for word in words)
        ]

        return ", ".join(matched[:3]) if matched else "최근 이슈"

    def finance_view(self):
        return ft.Column(
            [
                self.header("재무", "가치/수익성/안정성/수급 지표"),
                self.group_dropdown(),
                self.real_data_hint(),
                self.finance_content(),
            ],
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
        )

    def finance_content(self):
        records = self.records_for_current_group()

        return ft.Column(
            [
                self.finance_stock_card(item, record)
                for item, record in records
            ]
            or [self.empty_state("재무를 볼 종목이 없습니다.")],
            spacing=10,
        )

    def finance_stock_card(self, item, record):
        code = item.get("code", "")
        name = item.get("name", code)
        finance = record.get("finance", {}) if record else {}

        return self.card(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(name, weight=ft.FontWeight.BOLD),
                                    ft.Text(code, size=12, color="#64748b"),
                                ],
                                expand=True,
                                spacing=2,
                            ),
                            ft.Text(
                                record.get("grade", self.grade_for(self.final_score_for(code)))
                                if record
                                else self.grade_for(self.final_score_for(code)),
                                color="#ef4444" if self.final_score_for(code) >= 72 else "#2563eb",
                                weight=ft.FontWeight.BOLD,
                            ),
                        ]
                    ),
                    ft.Text(
                        self.data_quality_text(record),
                        size=11,
                        color=self.data_warning_color(record),
                    ),
                    self.finance_metric_grid(
                        [
                            ("PER", self.format_ratio(finance.get("per"))),
                            ("PBR", self.format_ratio(finance.get("pbr"))),
                            ("PCR", self.format_ratio(finance.get("pcr"))),
                            ("PSR", self.format_ratio(finance.get("psr"))),
                        ]
                    ),
                    self.finance_metric_grid(
                        [
                            ("ROE", self.format_percent_value(finance.get("roe"))),
                            ("ROA", self.format_percent_value(finance.get("roa"))),
                            ("영업이익률", self.format_percent_value(finance.get("operating_margin"))),
                            ("부채비율", self.format_percent_value(finance.get("debt_ratio"))),
                        ]
                    ),
                    self.finance_metric_grid(
                        [
                            ("FCF수익률", self.format_percent_value(finance.get("fcf_yield"))),
                            ("ROIC", self.format_percent_value(finance.get("roic"))),
                            ("공매도", self.format_percent_value(finance.get("short_ratio"))),
                            ("배당률", self.format_percent_value(finance.get("dividend_yield"))),
                        ]
                    ),
                    ft.Text(
                        self.finance_comment(finance, record),
                        size=12,
                        color="#334155",
                    ),
                ],
                spacing=10,
            )
        )

    def finance_metric_grid(self, pairs):
        return ft.Row(
            [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(label, size=11, color="#64748b"),
                            ft.Text(value, size=13, weight=ft.FontWeight.BOLD),
                        ],
                        spacing=2,
                    ),
                    expand=True,
                    padding=ft.Padding(8, 8, 8, 8),
                    bgcolor="#f8fafc",
                    border_radius=10,
                )
                for label, value in pairs
            ],
            spacing=6,
        )

    def finance_comment(self, finance, record):
        if not finance:
            return "재무 데이터 없음 | 새로고침 후에도 비어 있으면 해당 종목의 공개 재무 수집이 제한된 상태입니다."

        parts = []
        roe = safe_number(finance.get("roe"))
        debt = safe_number(finance.get("debt_ratio"))
        per = safe_number(finance.get("per"))
        fcf_yield = safe_number(finance.get("fcf_yield"))

        if roe >= 10:
            parts.append("ROE 양호")
        elif roe <= 0:
            parts.append("수익성 확인 필요")

        if debt >= 200:
            parts.append("부채비율 부담")
        elif debt > 0 and debt <= 100:
            parts.append("재무 안정성 양호")

        if per > 0 and per <= 15:
            parts.append("PER 부담 낮음")
        elif per >= 40:
            parts.append("밸류에이션 부담")

        if fcf_yield > 0:
            parts.append("현금흐름 플러스")

        if record and record.get("asset_type") == "ETF":
            parts.append("ETF는 재무보다 구성자산/추세 중심")

        if record and record.get("price_date"):
            parts.append(f"가격 기준일 {record.get('price_date')}")

        return " | ".join(parts) if parts else "특이 재무 신호는 제한적입니다."

    def chart_view(self):
        stocks = self.current_stocks()

        if stocks and not any(
            item.get("code") == self.selected_chart_code for item in stocks
        ):
            self.selected_chart_code = stocks[0].get("code", "")

        selected = self.stock_by_code(self.selected_chart_code) if stocks else None
        code = selected.get("code", "") if selected else ""
        name = selected.get("name", code) if selected else ""
        values = self.chart_values(code, self.chart_period)
        latest = values[-1] if values else 0
        first = values[0] if values else latest
        high = max(values) if values else 0
        low = min(values) if values else 0
        ma_lines = self.chart_ma_lines(values)
        change = ((latest - first) / first * 100) if first else 0
        price_text = self.format_price(code, latest)
        selected_price_text = (
            self.format_price(code, self.chart_selected_price)
            if self.chart_selected_price
            else ""
        )
        change_color = "#ef4444" if change >= 0 else "#2563eb"

        return ft.Column(
            [
                self.header("차트", "모바일용 토스 스타일 가격 흐름"),
                self.chart_stock_dropdown(stocks),
                self.card(
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Column(
                                        [
                                            ft.Text(
                                                name or "종목 없음",
                                                size=15,
                                                weight=ft.FontWeight.BOLD,
                                            ),
                                            ft.Text(
                                                code or "-",
                                                size=12,
                                                color="#64748b",
                                            ),
                                        ],
                                        expand=True,
                                        spacing=2,
                                    ),
                                    ft.Column(
                                        [
                                            ft.Text(
                                                price_text,
                                                size=19,
                                                weight=ft.FontWeight.BOLD,
                                                color="#111827",
                                                text_align=ft.TextAlign.RIGHT,
                                            ),
                                            ft.Text(
                                                f"{change:+.2f}%",
                                                color=change_color,
                                                weight=ft.FontWeight.BOLD,
                                                text_align=ft.TextAlign.RIGHT,
                                            ),
                                        ],
                                        horizontal_alignment=ft.CrossAxisAlignment.END,
                                        spacing=2,
                                    ),
                                ]
                            ),
                            *(
                                [
                                    ft.Text(
                                        f"선택 가격 {selected_price_text}",
                                        size=13,
                                        color="#111827",
                                        weight=ft.FontWeight.BOLD,
                                    )
                                ]
                                if selected_price_text
                                else []
                            ),
                            self.chart_image(values, change >= 0, ma_lines),
                            self.chart_legend(change >= 0, ma_lines),
                            self.chart_detail_panel(code, values, first, latest, high, low, change, ma_lines),
                            ft.Row(
                                [
                                    self.chip_button(
                                        period,
                                        self.chart_period == period,
                                        lambda _, p=period: self.set_chart_period(p),
                                    )
                                    for period in [
                                        "1일",
                                        "1주",
                                        "1개월",
                                        "3개월",
                                        "6개월",
                                        "1년",
                                    ]
                                ],
                                spacing=6,
                                wrap=True,
                            ),
                            ft.Text(
                                self.chart_data_note(),
                                size=11,
                                color="#94a3b8",
                            ),
                        ],
                        spacing=14,
                    )
                ),
            ],
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
        )

    def chart_detail_panel(self, code, values, first, latest, high, low, change, ma_lines=None):
        if not values:
            return self.empty_state("차트 상세 데이터가 없습니다.")

        ma_lines = ma_lines or {}

        selected = (
            self.chart_selected_price
            if self.chart_selected_price is not None
            else latest
        )
        selected_index = (
            self.chart_selected_index
            if self.chart_selected_index is not None
            else len(values) - 1
        )

        return ft.Column(
            [
                self.finance_metric_grid(
                    [
                        ("현재", self.format_price(code, latest)),
                        ("시작", self.format_price(code, first)),
                        ("고가", self.format_price(code, high)),
                        ("저가", self.format_price(code, low)),
                    ]
                ),
                self.finance_metric_grid(
                    [
                        ("선택", self.format_price(code, selected)),
                        ("위치", f"{selected_index + 1}/{len(values)}" if values else "-"),
                        ("구간", f"{change:+.2f}%"),
                        ("변동폭", self.format_price(code, high - low)),
                    ]
                ),
                self.finance_metric_grid(
                    [
                        ("20일선", self.format_ma_price(code, ma_lines.get("MA20"))),
                        ("40일선", self.format_ma_price(code, ma_lines.get("MA40"))),
                        ("60일선", self.format_ma_price(code, ma_lines.get("MA60"))),
                        ("데이터수", f"{len(values)}개"),
                    ]
                ),
            ],
            spacing=6,
        )

    def format_ma_price(self, code, values):
        if not values:
            return "-"

        latest = next(
            (
                value for value in reversed(values)
                if value is not None and safe_number(value) > 0
            ),
            None,
        )

        if latest is None:
            return "-"

        return self.format_price(code, latest)

    def chart_ma_lines(self, values):
        return {
            "MA20": self.moving_average(values, 20),
            "MA40": self.moving_average(values, 40),
            "MA60": self.moving_average(values, 60),
        }

    @staticmethod
    def moving_average(values, window):
        if not values:
            return []

        result = []

        for index in range(len(values)):
            if index + 1 < window:
                result.append(None)
                continue

            chunk = values[index + 1 - window:index + 1]
            result.append(sum(chunk) / len(chunk))

        return result

    def chart_legend(self, positive, ma_lines):
        line_color = "#ef4444" if positive else "#2563eb"
        items = [
            ("가격", line_color),
            ("20일선", "#f59e0b"),
            ("40일선", "#10b981"),
            ("60일선", "#8b5cf6"),
        ]

        return ft.Row(
            [
                ft.Row(
                    [
                        ft.Container(width=14, height=4, bgcolor=color, border_radius=4),
                        ft.Text(label, size=11, color="#64748b"),
                    ],
                    spacing=4,
                )
                for label, color in items
            ],
            spacing=10,
            wrap=True,
        )

    def chart_data_note(self):
        if self.bridge and self.real_chart_cache:
            return "실제 가격 히스토리를 우선 표시합니다. 차트를 누르면 선택 지점 가격이 표시됩니다."

        return "실제 데이터가 없으면 샘플 흐름을 표시합니다. 차트를 누르면 선택 지점 가격이 표시됩니다."

    def chart_stock_dropdown(self, stocks):
        return ft.Dropdown(
            label="차트 종목",
            value=self.selected_chart_code or None,
            options=[
                ft.dropdown.Option(
                    key=item.get("code", ""),
                    text=f"{item.get('name', item.get('code', ''))} ({item.get('code', '')})",
                )
                for item in stocks
            ],
            on_select=self.on_chart_stock_change,
            dense=True,
        )

    def on_chart_stock_change(self, event):
        self.selected_chart_code = event.control.value or ""
        self.chart_selected_index = None
        self.chart_selected_price = None
        self.render()

    def set_chart_period(self, period):
        self.chart_period = period
        self.chart_selected_index = None
        self.chart_selected_price = None
        self.render()

    def stock_by_code(self, code):
        for item in self.current_stocks():
            if item.get("code") == code:
                return item

        return {}

    def chart_values(self, code, period):
        bridge_values = self.real_chart_values(code, period)

        if bridge_values:
            return bridge_values

        counts = {
            "1일": 48,
            "1주": 40,
            "1개월": 30,
            "3개월": 36,
            "6개월": 30,
            "1년": 52,
        }
        count = counts.get(period, 30)
        seed = sum(ord(ch) for ch in f"{code}:{period}") or 1
        rng = random.Random(seed)
        base = 55000 + (seed % 800) * 120 if str(code).isdigit() else 30 + (seed % 240)
        trend = rng.uniform(-0.008, 0.012)
        value = float(base)
        values = []

        for index in range(count):
            wave = 0.012 * random.Random(seed + index * 17).uniform(-1, 1)
            value = max(base * 0.55, value * (1 + trend + wave))
            values.append(round(value, 2))

        return values

    def real_chart_values(self, code, period):
        if not code or not self.bridge:
            return []

        key = (code, period)

        if key in self.real_chart_cache:
            return self.real_chart_cache[key]

        period_map = {
            "1일": ("1d", "5m"),
            "1주": ("5d", "30m"),
            "1개월": ("1mo", "1d"),
            "3개월": ("3mo", "1d"),
            "6개월": ("6mo", "1d"),
            "1년": ("1y", "1d"),
        }
        api_period, interval = period_map.get(period, ("1mo", "1d"))
        values = self.bridge.chart_values(code, api_period, interval)
        self.real_chart_cache[key] = values
        return values

    def chart_image(self, values, positive, ma_lines=None):
        if not values:
            return self.empty_state("차트 데이터가 없습니다.")

        color = "#ef4444" if positive else "#2563eb"
        svg = self.chart_svg(values, color, self.chart_selected_index, ma_lines or {})
        encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")

        return ft.GestureDetector(
            content=ft.Container(
                height=230,
                border_radius=16,
                bgcolor="#ffffff",
                content=ft.Image(
                    src=f"data:image/svg+xml;base64,{encoded}",
                    fit=ft.BoxFit.CONTAIN,
                ),
            ),
            on_tap_down=lambda event, data=values: self.on_chart_tap(event, data),
        )

    def on_chart_tap(self, event, values):
        if not values:
            return

        position = getattr(event, "local_position", None)
        x = safe_number(getattr(position, "x", 0), 0)
        chart_width = 398
        ratio = max(0, min(x / chart_width, 1))
        index = round(ratio * (len(values) - 1))
        index = max(0, min(index, len(values) - 1))
        self.chart_selected_index = index
        self.chart_selected_price = values[index]
        self.render()

    def chart_svg(self, values, color, selected_index=None, ma_lines=None):
        width = 760
        height = 300
        left = 24
        right = 24
        top = 26
        bottom = 32
        min_value = min(values)
        max_value = max(values)
        span = max(max_value - min_value, max_value * 0.01, 1)
        plot_width = width - left - right
        plot_height = height - top - bottom
        points = []

        for index, value in enumerate(values):
            x = left + (plot_width * index / max(len(values) - 1, 1))
            y = top + plot_height - ((value - min_value) / span * plot_height)
            points.append((x, y))

        line_points = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        ma_markup = self.chart_ma_svg(
            ma_lines or {},
            min_value,
            span,
            left,
            top,
            plot_width,
            plot_height,
        )
        area_points = (
            f"{left},{height - bottom} "
            + line_points
            + f" {width - right},{height - bottom}"
        )
        grid = "\n".join(
            f'<line x1="{left}" y1="{top + i * plot_height / 3:.1f}" '
            f'x2="{width - right}" y2="{top + i * plot_height / 3:.1f}" '
            'stroke="#f1f5f9" stroke-width="1"/>'
            for i in range(4)
        )
        end_x, end_y = points[-1]
        selected_markup = ""

        if selected_index is not None and 0 <= selected_index < len(points):
            selected_x, selected_y = points[selected_index]
            selected_markup = (
                f'<line x1="{selected_x:.1f}" y1="{top}" '
                f'x2="{selected_x:.1f}" y2="{height - bottom}" '
                'stroke="#94a3b8" stroke-width="2" stroke-dasharray="7 7"/>'
                f'<circle cx="{selected_x:.1f}" cy="{selected_y:.1f}" r="8" '
                f'fill="#ffffff" stroke="{color}" stroke-width="4"/>'
            )

        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" fill="#ffffff"/>
  {grid}
  <polygon points="{html.escape(area_points)}" fill="{color}" opacity="0.08"/>
  <polyline points="{html.escape(line_points)}" fill="none" stroke="{color}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
  {ma_markup}
  {selected_markup}
  <circle cx="{end_x:.1f}" cy="{end_y:.1f}" r="7" fill="#ffffff" stroke="{color}" stroke-width="4"/>
</svg>"""

    def chart_ma_svg(self, ma_lines, min_value, span, left, top, plot_width, plot_height):
        colors = {
            "MA20": "#f59e0b",
            "MA40": "#10b981",
            "MA60": "#8b5cf6",
        }
        segments = []

        for name, values in ma_lines.items():
            color = colors.get(name, "#64748b")
            usable = [
                (index, value)
                for index, value in enumerate(values or [])
                if value is not None and safe_number(value) > 0
            ]

            if len(usable) < 2:
                continue

            total = max(len(values) - 1, 1)
            points = []

            for index, value in usable:
                x = left + (plot_width * index / total)
                y = top + plot_height - ((value - min_value) / span * plot_height)
                points.append(f"{x:.1f},{y:.1f}")

            segments.append(
                f'<polyline points="{" ".join(points)}" fill="none" '
                f'stroke="{color}" stroke-width="2.5" '
                'stroke-linecap="round" stroke-linejoin="round" opacity="0.88"/>'
            )

        return "\n  ".join(segments)

    def format_price(self, code, value, currency=None):
        currency = currency or ("KRW" if str(code).isdigit() else "USD")

        if currency == "KRW":
            return f"{value:,.0f}원"

        return f"${value:,.2f}"

    def records_for_current_group(self):
        return [
            (item, self.real_record(item.get("code", "")))
            for item in self.current_stocks()
        ]

    def real_data_hint(self):
        if self.analysis_loading:
            return self.card(
                ft.Row(
                    [
                        ft.ProgressRing(
                            width=18,
                            height=18,
                            stroke_width=2,
                            color="#2563eb",
                        ),
                        ft.Text(
                            self.analysis_loading_message or "실제 데이터를 불러오는 중입니다.",
                            size=12,
                            color="#2563eb",
                            expand=True,
                        ),
                    ],
                    spacing=8,
                ),
                padding=12,
                bgcolor="#eff6ff",
            )

        if self.real_data_loaded_at:
            return self.card(
                ft.Text(
                    f"실제 분석 데이터 연결됨: {self.real_data_loaded_at}",
                    size=12,
                    color="#16a34a",
                ),
                padding=12,
                bgcolor="#f0fdf4",
            )

        return self.card(
            ft.Text(
                "설정에서 실제 분석 데이터를 불러오면 뉴스/재무가 실데이터로 채워집니다.",
                size=12,
                color="#64748b",
            ),
            padding=12,
            bgcolor="#f8fafc",
        )

    @staticmethod
    def format_ratio(value):
        value = safe_number(value)
        return "-" if value == 0 else f"{value:.2f}배"

    @staticmethod
    def format_percent_value(value):
        value = safe_number(value)
        return "-" if value == 0 else f"{value:.2f}%"

    def settings_view(self):
        stock_count = sum(len(items) for items in self.groups.values())
        holding_count = len(self.holdings)

        return ft.Column(
            [
                self.header("설정", "데이터 연결 상태"),
                ft.Row(
                    [
                        self.metric_card("그룹", f"{len(self.groups)}개"),
                        self.metric_card("종목", f"{stock_count}개"),
                    ],
                    spacing=10,
                ),
                self.metric_card("보유 입력", f"{holding_count}개", wide=True),
                self.card(
                    ft.Column(
                        [
                            self.app_info_panel(),
                            self.app_health_panel(),
                            ft.Divider(),
                            ft.Text("저장 위치", weight=ft.FontWeight.BOLD),
                            ft.Text(self.storage_mode_label(), size=12, color="#334155"),
                            ft.Text(str(self.storage_dir), size=12, color="#64748b"),
                            self.primary_button("저장 데이터 새로고침", self.reload_data),
                            self.server_settings_panel(),
                            self.analysis_action_control(),
                            self.analysis_status_panel(),
                            self.auto_refresh_panel(),
                            self.alert_settings_panel(),
                            ft.Divider(),
                            ft.Text("파일 상태", weight=ft.FontWeight.BOLD),
                            self.file_status_row("관심종목", self.watchlist_file),
                            self.file_status_row("보유종목", self.holdings_file),
                            self.file_status_row("앱 설정", self.settings_file),
                            ft.Divider(),
                            ft.Text("완성 단계", weight=ft.FontWeight.BOLD),
                            ft.Text("1. 관심종목/보유종목 읽기 및 저장 완료", color="#334155"),
                            ft.Text("2. 모바일 브리핑/차트 UI 구성 완료", color="#334155"),
                            ft.Text("3. PC 분석 엔진 브릿지 연결 완료", color="#334155"),
                            ft.Text("4. 모바일 뉴스/재무 상세 화면 분리 완료", color="#334155"),
                            ft.Text("5. 분석 로딩 화면과 중복 실행 방지 완료", color="#334155"),
                            ft.Text("6. 하단 메뉴 5개로 모바일 화면 정리 완료", color="#334155"),
                            ft.Text("7. 자동 실시간 데이터 새로고침 완료", color="#334155"),
                        ],
                        spacing=8,
                    )
                ),
            ],
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
        )

    def server_settings_panel(self):
        status = (
            "Render 서버 사용 중"
            if self.api_base_url
            else "서버 URL 없음, 로컬 분석 사용"
        )
        color = "#16a34a" if self.api_base_url else "#64748b"

        return self.card(
            ft.Column(
                [
                    ft.Text("분석 서버", weight=ft.FontWeight.BOLD),
                    ft.Text(status, size=12, color=color),
                    self.api_base_url_input,
                    ft.Text(
                        "Render URL을 넣으면 새로고침 때 서버 분석을 먼저 사용합니다.",
                        size=12,
                        color="#64748b",
                    ),
                    ft.Row(
                        [
                            self.primary_button("서버 설정 저장", self.save_server_settings),
                            self.secondary_button("기본 서버", self.clear_server_settings),
                        ],
                        spacing=8,
                    ),
                ],
                spacing=8,
            ),
            padding=12,
            bgcolor="#f8fafc",
        )

    def alert_settings_panel(self):
        return self.card(
            ft.Column(
                [
                    ft.Text("앱 알림 기준", weight=ft.FontWeight.BOLD),
                    ft.Row(
                        [self.alert_score_input, self.alert_change_input],
                        spacing=8,
                    ),
                    ft.Row(
                        [self.alert_upside_input, self.alert_loss_input],
                        spacing=8,
                    ),
                    ft.Row(
                        [self.alert_bad_news_input, self.auto_interval_input],
                        spacing=8,
                    ),
                    ft.Text(
                        "자동 새로고침은 분 단위입니다. 보유 손실 기준은 음수로 입력하세요.",
                        size=12,
                        color="#64748b",
                    ),
                    ft.Row(
                        [
                            self.primary_button("알림 설정 저장", self.save_alert_settings),
                            self.secondary_button("기본값", self.reset_alert_settings),
                        ],
                        spacing=8,
                    ),
                ],
                spacing=8,
            ),
            padding=12,
            bgcolor="#f8fafc",
        )

    def app_info_panel(self):
        app_name = self.build_config.get("app_name", "Morning Stock")
        bundle_id = self.build_config.get("bundle_id", "com.kck.morningstock")
        version = self.build_config.get("build_version", "0.1.0")
        build_number = self.build_config.get("build_number", "1")

        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.SYSTEM_UPDATE_ALT, color="#2563eb"),
                            ft.Text("앱 정보/업데이트", weight=ft.FontWeight.BOLD, expand=True),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    self.info_line("앱 이름", app_name),
                    self.info_line("앱 ID", bundle_id),
                    self.info_line("버전", f"{version} / 빌드 {build_number}"),
                    ft.Text(
                        "업데이트 설치는 앱 ID와 서명 키를 유지하고 빌드 번호만 올리면 됩니다.",
                        size=12,
                        color="#334155",
                    ),
                    ft.Text(
                        "업데이트 빌드 명령: build_apk.ps1 -BumpBuildNumber -RunBuild",
                        size=11,
                        color="#64748b",
                    ),
                ],
                spacing=6,
            ),
            padding=12,
            border_radius=10,
            bgcolor="#eff6ff",
        )

    @staticmethod
    def info_line(label, value):
        return ft.Row(
            [
                ft.Text(label, size=12, color="#64748b", expand=True),
                ft.Text(str(value), size=12, color="#111827", weight=ft.FontWeight.BOLD),
            ],
            spacing=8,
        )

    def app_health_panel(self):
        checks = self.app_health_checks()
        danger_count = sum(1 for item in checks if item["level"] == "danger")
        watch_count = sum(1 for item in checks if item["level"] == "watch")
        title = (
            "앱 상태 점검 필요"
            if danger_count
            else "앱 상태 주의"
            if watch_count
            else "앱 상태 양호"
        )
        color = "#ef4444" if danger_count else "#f59e0b" if watch_count else "#16a34a"

        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.HEALTH_AND_SAFETY, color=color),
                            ft.Text(title, weight=ft.FontWeight.BOLD, expand=True),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Column(
                        [self.health_check_row(item) for item in checks],
                        spacing=6,
                    ),
                ],
                spacing=8,
            ),
            padding=12,
            border_radius=10,
            bgcolor="#f8fafc",
        )

    def app_health_checks(self):
        stock_count = sum(len(items) for items in self.groups.values())
        holding_count = len(self.holdings)
        stale_count = sum(
            1 for record in self.real_records.values()
            if safe_number(record.get("freshness_days", -1), -1) >= 3
        )
        unknown_date_count = sum(
            1 for record in self.real_records.values()
            if safe_number(record.get("freshness_days", -1), -1) < 0
        )
        checks = []

        checks.append({
            "label": "관심종목",
            "value": f"{stock_count}개",
            "level": "good" if stock_count else "danger",
            "hint": "관심종목을 추가해야 분석과 알림이 동작합니다.",
        })
        checks.append({
            "label": "보유종목",
            "value": f"{holding_count}개",
            "level": "good" if holding_count else "watch",
            "hint": "수량과 평균가를 입력하면 포트폴리오 피드백이 좋아집니다.",
        })
        checks.append({
            "label": "실제 데이터",
            "value": f"{len(self.real_records)}개",
            "level": "good" if self.real_records else "watch",
            "hint": "새로고침을 실행하면 가격/뉴스/재무가 채워집니다.",
        })
        checks.append({
            "label": "오래된 가격",
            "value": f"{stale_count}개",
            "level": "danger" if stale_count else "good",
            "hint": "가격 기준일이 오래된 종목은 최신성 확인이 필요합니다.",
        })
        checks.append({
            "label": "기준일 미확인",
            "value": f"{unknown_date_count}개",
            "level": "watch" if unknown_date_count else "good",
            "hint": "일부 종목은 데이터 제공처가 기준일을 주지 않을 수 있습니다.",
        })
        return checks

    def health_check_row(self, item):
        color = {
            "danger": "#ef4444",
            "watch": "#f59e0b",
            "good": "#16a34a",
        }.get(item["level"], "#64748b")

        return ft.Row(
            [
                ft.Container(width=8, height=8, border_radius=4, bgcolor=color),
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text(item["label"], size=12, color="#334155", expand=True),
                                ft.Text(item["value"], size=12, color=color, weight=ft.FontWeight.BOLD),
                            ],
                            spacing=8,
                        ),
                        ft.Text(item["hint"], size=11, color="#94a3b8"),
                    ],
                    spacing=2,
                    expand=True,
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

    def backup_panel(self):
        latest = self.latest_backup_file()
        latest_text = (
            f"최근 백업: {latest.name}"
            if latest
            else "아직 백업 파일이 없습니다."
        )

        return self.card(
            ft.Column(
                [
                    ft.Text("데이터 백업/복원", weight=ft.FontWeight.BOLD),
                    ft.Text(latest_text, size=12, color="#64748b"),
                    ft.Text(
                        "관심종목, 보유종목, 앱 설정을 앱 저장소 안에 백업합니다.",
                        size=12,
                        color="#64748b",
                    ),
                    ft.Row(
                        [
                            self.primary_button("백업 만들기", self.create_data_backup),
                            self.secondary_button("최근 백업 복원", self.restore_latest_backup),
                        ],
                        spacing=8,
                    ),
                    ft.Row(
                        [
                            self.secondary_button("백업 내보내기", self.export_latest_backup),
                            self.secondary_button("백업 파일 가져오기", self.import_backup_file),
                        ],
                        spacing=8,
                    ),
                    ft.Text(
                        "파일 선택이 제한되는 환경에서는 먼저 백업을 만든 뒤 앱 저장소의 backups 폴더를 확인하세요.",
                        size=11,
                        color="#94a3b8",
                    ),
                ],
                spacing=8,
            ),
            padding=12,
            bgcolor="#f8fafc",
        )

    def create_data_backup(self, _=None):
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = f"{datetime.now():%Y%m%d_%H%M%S}"
        backup_file = self.backup_dir / f"morning_stock_backup_{timestamp}.json"
        data = {
            "created_at": f"{datetime.now():%Y-%m-%d %H:%M:%S}",
            "app": {
                "bundle_id": self.build_config.get("bundle_id", "com.kck.morningstock"),
                "build_version": self.build_config.get("build_version", "0.1.0"),
                "build_number": self.build_config.get("build_number", "1"),
            },
            "watchlist": self.groups,
            "holdings": self.holdings,
            "settings": {
                "alert_threshold_score": self.alert_threshold_score,
                "alert_threshold_change": self.alert_threshold_change,
                "alert_threshold_upside": self.alert_threshold_upside,
                "alert_threshold_loss": self.alert_threshold_loss,
                "alert_threshold_bad_news": self.alert_threshold_bad_news,
                "auto_refresh_enabled": self.auto_refresh_enabled,
                "auto_refresh_interval_minutes": self.auto_refresh_interval_minutes,
                "api_base_url": self.api_base_url,
            },
        }
        save_json(backup_file, data)
        self.snack(f"백업을 만들었습니다: {backup_file.name}")
        self.render()

    def restore_latest_backup(self, _=None):
        backup_file = self.latest_backup_file()

        if not backup_file:
            self.snack("복원할 백업 파일이 없습니다.")
            return

        self.restore_backup_data(load_json(backup_file, {}), backup_file.name)

    def export_latest_backup(self, _=None):
        backup_file = self.latest_backup_file()

        if not backup_file:
            self.create_data_backup()
            backup_file = self.latest_backup_file()

        if not backup_file or not backup_file.exists():
            self.snack("내보낼 백업 파일이 없습니다.")
            return

        try:
            saved_path = self.file_picker.save_file(
                dialog_title="백업 파일 저장",
                file_name=backup_file.name,
                allowed_extensions=["json"],
                src_bytes=backup_file.read_bytes(),
            )
        except Exception as exc:
            self.snack(f"백업 내보내기 실패: {exc}")
            return

        if saved_path:
            self.snack("백업 파일을 내보냈습니다.")
        else:
            self.snack("백업 내보내기가 취소되었습니다.")

    def import_backup_file(self, _=None):
        try:
            files = self.file_picker.pick_files(
                dialog_title="백업 파일 선택",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["json"],
                allow_multiple=False,
                with_data=True,
            )
        except Exception as exc:
            self.snack(f"백업 파일 선택 실패: {exc}")
            return

        if not files:
            self.snack("백업 파일 선택이 취소되었습니다.")
            return

        selected = files[0]

        try:
            file_bytes = getattr(selected, "bytes", None)

            if file_bytes:
                data = json.loads(file_bytes.decode("utf-8"))
            elif selected.path:
                data = load_json(Path(selected.path), {})
            else:
                data = {}
        except Exception as exc:
            self.snack(f"백업 파일 읽기 실패: {exc}")
            return

        self.restore_backup_data(data, selected.name)

    def restore_backup_data(self, data, source_name):
        watchlist = data.get("watchlist")
        holdings = data.get("holdings")
        settings = data.get("settings", {})

        if not isinstance(watchlist, dict) or not isinstance(holdings, dict):
            self.snack("백업 파일 형식이 올바르지 않습니다.")
            return

        self.groups = watchlist
        self.holdings = holdings
        save_json(self.watchlist_file, self.groups)
        save_json(self.holdings_file, self.holdings)

        if isinstance(settings, dict):
            self.apply_restored_settings(settings)
            self.save_app_settings()

        self.selected_group = next(iter(self.groups), "")
        first = self.current_stocks()[0] if self.current_stocks() else {}
        self.selected_chart_code = first.get("code", "")
        self.selected_holding_code = first.get("code", "")
        self.real_records = {}
        self.real_chart_cache = {}
        self.alerts = []
        self.alert_history = set()
        self.sync_alert_inputs()
        self.snack(f"백업을 복원했습니다: {source_name}")
        self.render()

    def apply_restored_settings(self, settings):
        self.alert_threshold_score = safe_number(
            settings.get("alert_threshold_score", self.alert_threshold_score),
            self.alert_threshold_score,
        )
        self.alert_threshold_change = safe_number(
            settings.get("alert_threshold_change", self.alert_threshold_change),
            self.alert_threshold_change,
        )
        self.alert_threshold_upside = safe_number(
            settings.get("alert_threshold_upside", self.alert_threshold_upside),
            self.alert_threshold_upside,
        )
        self.alert_threshold_loss = safe_number(
            settings.get("alert_threshold_loss", self.alert_threshold_loss),
            self.alert_threshold_loss,
        )
        self.alert_threshold_bad_news = safe_number(
            settings.get("alert_threshold_bad_news", self.alert_threshold_bad_news),
            self.alert_threshold_bad_news,
        )
        self.auto_refresh_enabled = bool(
            settings.get("auto_refresh_enabled", self.auto_refresh_enabled)
        )
        self.auto_refresh_interval_minutes = max(
            1,
            int(
                safe_number(
                    settings.get(
                        "auto_refresh_interval_minutes",
                        self.auto_refresh_interval_minutes,
                    ),
                    self.auto_refresh_interval_minutes,
                )
            ),
        )
        self.api_base_url = str(
            settings.get("api_base_url", self.api_base_url)
        ).strip()

    def latest_backup_file(self):
        if not self.backup_dir.exists():
            return None

        backups = sorted(
            self.backup_dir.glob("morning_stock_backup_*.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        return backups[0] if backups else None

    def analysis_status_panel(self):
        if self.analysis_loading:
            text = self.analysis_loading_message or "실제 분석 데이터를 불러오는 중입니다."
            color = "#2563eb"
        elif self.analysis_loading_message:
            text = self.analysis_loading_message
            color = "#16a34a"
        elif self.real_data_error:
            text = f"분석 연결 실패: {self.real_data_error}"
            color = "#ef4444"
        elif self.real_data_loaded_at:
            text = (
                f"실제 분석 데이터 {len(self.real_records)}개 연결됨 | "
                f"{self.real_data_loaded_at}"
            )
            color = "#16a34a"
        else:
            text = "아직 실제 분석 데이터를 불러오지 않았습니다."
            color = "#64748b"

        return ft.Text(text, ref=self.settings_status_ref, size=12, color=color)

    def current_analysis_status(self):
        if self.analysis_loading:
            elapsed = self.analysis_elapsed_seconds()
            suffix = f" | {elapsed}초 경과" if elapsed >= 0 else ""
            return (
                f"{self.analysis_loading_message or '실제 데이터를 불러오는 중입니다.'}{suffix}",
                "#2563eb",
            )

        if self.analysis_loading_message:
            return self.analysis_loading_message, "#16a34a"

        if self.real_data_error:
            return f"분석 연결 실패: {self.real_data_error}", "#ef4444"

        if self.real_data_loaded_at:
            return f"최근 갱신 {self.real_data_loaded_at}", "#16a34a"

        return "아직 실제 데이터를 불러오지 않았습니다.", "#64748b"

    def analysis_elapsed_seconds(self):
        if self.analysis_started_at is None:
            return -1

        return max(0, int(time.monotonic() - self.analysis_started_at))

    def update_visible_analysis_status(self):
        text, color = self.current_analysis_status()
        controls = []

        self.progress_overlay.visible = bool(
            self.analysis_loading or self.analysis_loading_message
        )
        self.progress_overlay.bgcolor = (
            "#eff6ff" if self.analysis_loading else "#f0fdf4"
        )
        self.progress_overlay_text.value = text
        self.progress_overlay_text.color = color
        controls.extend([self.progress_overlay, self.progress_overlay_text])

        for ref in [
            self.global_status_ref,
            self.home_status_ref,
            self.settings_status_ref,
            self.settings_loading_ref,
        ]:
            control = getattr(ref, "current", None)

            if control is None:
                continue

            control.value = text
            control.color = color
            controls.append(control)

        progress_bar = getattr(self.progress_bar_ref, "current", None)
        progress_detail = getattr(self.progress_detail_ref, "current", None)
        progress_percent = getattr(self.progress_percent_ref, "current", None)
        progress = self.analysis_progress_value()

        if progress_bar is not None:
            progress_bar.value = progress
            controls.append(progress_bar)

        if progress_detail is not None:
            elapsed = self.analysis_elapsed_seconds()
            detail = self.analysis_current or self.analysis_loading_message
            progress_detail.value = f"{detail} | {elapsed}초 경과"
            controls.append(progress_detail)

        if progress_percent is not None:
            progress_percent.value = (
                f"{int((progress or 0) * 100)}%"
                if progress is not None
                else "진행 중"
            )
            controls.append(progress_percent)

        if controls:
            try:
                self.page.update(*controls)
            except Exception:
                try:
                    self.page.schedule_update()
                except Exception:
                    pass

    def set_analysis_message(self, message, current=None, update_page=True):
        self.analysis_loading_message = message

        if current is not None:
            self.analysis_current = current

        self.update_visible_analysis_status()

        if update_page:
            self.safe_update()

    def start_status_watcher(self):
        if self.status_watcher_started:
            return

        self.status_watcher_started = True
        self.page.run_thread(self.status_watcher)

    def status_watcher(self):
        while True:
            snapshot = (
                self.analysis_loading,
                self.analysis_loading_message,
                self.analysis_elapsed_seconds(),
                self.real_data_loaded_at,
                self.real_data_error,
                self.selected_index,
                len(self.real_records),
            )

            if snapshot != self.last_status_snapshot:
                self.last_status_snapshot = snapshot
                self.update_visible_analysis_status()

            time.sleep(0.25)

    def analysis_action_control(self):
        if self.analysis_loading:
            return self.card(
                ft.Row(
                    [
                        ft.ProgressRing(
                            width=22,
                            height=22,
                            stroke_width=3,
                            color="#2563eb",
                        ),
                        ft.Text(
                            self.analysis_loading_message or "분석 중...",
                            ref=self.settings_loading_ref,
                            color="#334155",
                            expand=True,
                        ),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=12,
                bgcolor="#eff6ff",
            )

        return self.secondary_button(
            "새로고침",
            self.load_real_analysis,
        )

    def auto_refresh_panel(self):
        status = (
            f"켜짐 | {self.auto_refresh_interval_minutes}분마다"
            if self.auto_refresh_enabled
            else "꺼짐"
        )
        last = self.auto_refresh_last_at or "아직 없음"

        return self.card(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text("자동 새로고침", weight=ft.FontWeight.BOLD),
                                    ft.Text(f"{status} | 실제 데이터 갱신", size=12, color="#64748b"),
                                ],
                                expand=True,
                                spacing=2,
                            ),
                            ft.Switch(
                                value=self.auto_refresh_enabled,
                                on_change=self.toggle_auto_refresh,
                                active_color="#2563eb",
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Text(f"마지막 자동 새로고침: {last}", size=12, color="#64748b"),
                ],
                spacing=8,
            ),
            padding=12,
            bgcolor="#f8fafc",
        )

    def toggle_auto_refresh(self, event):
        self.auto_refresh_enabled = bool(event.control.value)
        self.save_app_settings()

        if self.auto_refresh_enabled:
            self.start_auto_refresh()

        self.render()

    def save_server_settings(self, _=None):
        value = str(self.api_base_url_input.value or "").strip().rstrip("/")

        if not value:
            value = DEFAULT_SERVER_URL

        if value and not value.startswith(("http://", "https://")):
            self.snack("서버 URL은 https:// 로 시작해야 합니다.")
            return

        self.api_base_url = value
        self.save_app_settings()
        self.snack("서버 설정을 저장했습니다.")
        self.render()

    def clear_server_settings(self, _=None):
        self.api_base_url = DEFAULT_SERVER_URL
        self.api_base_url_input.value = DEFAULT_SERVER_URL
        self.save_app_settings()
        self.snack("기본 서버 주소로 되돌렸습니다.")
        self.render()

    def save_alert_settings(self, _=None):
        values = {
            "alert_threshold_score": safe_number(self.alert_score_input.value, -1),
            "alert_threshold_change": safe_number(self.alert_change_input.value, -1),
            "alert_threshold_upside": safe_number(self.alert_upside_input.value, -1),
            "alert_threshold_loss": safe_number(self.alert_loss_input.value, 1),
            "alert_threshold_bad_news": safe_number(self.alert_bad_news_input.value, -1),
            "auto_refresh_interval_minutes": safe_number(self.auto_interval_input.value, -1),
        }

        if (
            values["alert_threshold_score"] < 0
            or values["alert_threshold_change"] <= 0
            or values["alert_threshold_upside"] < 0
            or values["alert_threshold_bad_news"] < 0
            or values["auto_refresh_interval_minutes"] < 1
        ):
            self.snack("알림 기준은 올바른 숫자로 입력하세요.")
            return

        if values["alert_threshold_loss"] > 0:
            self.snack("보유 손실 기준은 -10처럼 음수로 입력하세요.")
            return

        self.alert_threshold_score = values["alert_threshold_score"]
        self.alert_threshold_change = values["alert_threshold_change"]
        self.alert_threshold_upside = values["alert_threshold_upside"]
        self.alert_threshold_loss = values["alert_threshold_loss"]
        self.alert_threshold_bad_news = values["alert_threshold_bad_news"]
        self.auto_refresh_interval_minutes = int(values["auto_refresh_interval_minutes"])
        self.alert_history = set()
        self.save_app_settings()
        self.snack("알림 설정을 저장했습니다.")
        self.render()

    def reset_alert_settings(self, _=None):
        self.alert_threshold_score = 75
        self.alert_threshold_change = 5
        self.alert_threshold_upside = 30
        self.alert_threshold_loss = -10
        self.alert_threshold_bad_news = 35
        self.auto_refresh_interval_minutes = 30
        self.sync_alert_inputs()
        self.alert_history = set()
        self.save_app_settings()
        self.snack("알림 설정을 기본값으로 되돌렸습니다.")
        self.render()

    def sync_alert_inputs(self):
        self.alert_score_input.value = f"{self.alert_threshold_score:g}"
        self.alert_change_input.value = f"{self.alert_threshold_change:g}"
        self.alert_upside_input.value = f"{self.alert_threshold_upside:g}"
        self.alert_loss_input.value = f"{self.alert_threshold_loss:g}"
        self.alert_bad_news_input.value = f"{self.alert_threshold_bad_news:g}"
        self.auto_interval_input.value = f"{self.auto_refresh_interval_minutes:g}"
        self.api_base_url_input.value = self.api_base_url

    def save_app_settings(self):
        save_json(
            self.settings_file,
            {
                "alert_threshold_score": self.alert_threshold_score,
                "alert_threshold_change": self.alert_threshold_change,
                "alert_threshold_upside": self.alert_threshold_upside,
                "alert_threshold_loss": self.alert_threshold_loss,
                "alert_threshold_bad_news": self.alert_threshold_bad_news,
                "auto_refresh_enabled": self.auto_refresh_enabled,
                "auto_refresh_interval_minutes": self.auto_refresh_interval_minutes,
                "api_base_url": self.api_base_url,
            },
        )

    def file_status_row(self, label, path):
        exists = path.exists()
        status = "연결됨" if exists else "없음"
        color = "#16a34a" if exists else "#ef4444"
        detail = (
            f"{path.stat().st_size:,} bytes"
            if exists
            else "파일을 만들거나 PC 앱에서 저장하세요."
        )

        return ft.Row(
            [
                ft.Text(label, expand=True, color="#334155"),
                ft.Column(
                    [
                        ft.Text(status, color=color, weight=ft.FontWeight.BOLD),
                        ft.Text(detail, size=11, color="#94a3b8"),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.END,
                    spacing=1,
                ),
            ]
        )

    def add_stock(self, _):
        name = (self.search_name.value or "").strip()
        code = (self.search_code.value or "").strip().upper()

        resolved = self.resolve_stock_input(name, code)

        if not resolved:
            self.snack("종목명이나 종목 코드를 입력하세요.")
            return

        name = resolved["name"]
        code = resolved["code"]

        if not self.selected_group:
            self.selected_group = "기본"
            self.groups.setdefault(self.selected_group, [])

        if self.selected_group not in self.groups:
            self.groups[self.selected_group] = []

        stocks = self.groups.setdefault(self.selected_group, [])

        if any(item.get("code") == code for item in stocks):
            self.snack("이미 있는 종목입니다.")
            return

        stocks.append({"name": name or code, "code": code})
        save_json(self.watchlist_file, self.groups)
        self.selected_chart_code = code
        self.selected_holding_code = code
        self.real_records.pop(code, None)
        self.real_chart_cache = {}
        self.search_name.value = ""
        self.search_code.value = ""
        self.stock_preview = None
        self.stock_search_results = []
        self.snack("관심종목을 추가했습니다.")
        self.render()

    def search_stock_input(self, _=None):
        name = (self.search_name.value or "").strip()
        code = (self.search_code.value or "").strip().upper()
        keyword = code or name

        if not keyword:
            self.snack("검색할 종목명이나 종목 코드를 입력하세요.")
            return

        results = []

        try:
            results = self.search_service_factory().search(keyword, limit=12)
        except Exception:
            results = []

        if not results:
            resolved = self.resolve_stock_input(name, code)

            if resolved:
                results = [{
                    "name": resolved.get("name") or resolved.get("code", ""),
                    "code": resolved.get("code", ""),
                    "market": "국내" if str(resolved.get("code", "")).isdigit() else "해외",
                }]

        normalized = []
        seen = set()

        for item in results or []:
            item_code = self.normalize_stock_code(
                item.get("code")
                or item.get("symbol")
                or item.get("ticker")
                or ""
            )
            item_name = item.get("name") or item.get("company") or item_code

            if not item_code or item_code in seen:
                continue

            seen.add(item_code)
            normalized.append({
                "name": item_name,
                "code": item_code,
                "market": item.get("market")
                or ("국내" if item_code.isdigit() else "해외"),
            })

        self.stock_search_results = normalized
        self.stock_preview = None

        if not normalized:
            self.snack("검색 결과가 없습니다.")

        self.render()

    def add_search_result_stock(self, item):
        self.search_name.value = item.get("name", "")
        self.search_code.value = item.get("code", "")
        self.add_stock(None)

    def clear_stock_search_results(self, _=None):
        self.stock_search_results = []
        self.render()

    def preview_stock_input(self, _=None):
        name = (self.search_name.value or "").strip()
        code = (self.search_code.value or "").strip().upper()
        resolved = self.resolve_stock_input(name, code)

        if not resolved:
            self.stock_preview = {
                "ok": False,
                "title": "종목 인식 실패",
                "message": "종목명이나 코드를 다시 입력하세요. 예: 삼성전자, NVDA, 레졸루트",
            }
            self.render()
            return

        normalized_code = resolved["code"]
        resolved_name = resolved.get("name") or normalized_code
        market = "국내" if normalized_code.isdigit() else "해외"
        duplicate = any(
            item.get("code") == normalized_code
            for item in self.groups.get(self.selected_group, [])
        )

        self.stock_preview = {
            "ok": not duplicate,
            "name": resolved_name,
            "code": normalized_code,
            "title": "종목 인식 완료" if not duplicate else "이미 추가된 종목",
            "message": (
                f"{resolved_name} ({normalized_code}) | {market} 종목으로 인식했습니다."
                if not duplicate
                else f"{resolved_name} ({normalized_code})는 현재 그룹에 이미 있습니다."
            ),
        }
        self.render()

    def add_preview_stock(self, _=None):
        if not self.stock_preview or not self.stock_preview.get("ok"):
            self.snack("추가할 미리보기 종목이 없습니다.")
            return

        self.search_name.value = self.stock_preview.get("name", "")
        self.search_code.value = self.stock_preview.get("code", "")
        self.add_stock(None)

    def clear_stock_preview(self, _=None):
        self.stock_preview = None
        self.render()

    def resolve_stock_input(self, name, code):
        return self.stock_resolver().resolve(name, code)

    def resolve_stock_by_keyword(self, keyword):
        return self.stock_resolver().resolve_keyword(keyword)

    def resolve_with_search_service(self, keyword):
        return self.stock_resolver().resolve_with_search_service(keyword)

    def resolve_with_local_files(self, keyword):
        return self.stock_resolver().resolve_with_local_files(keyword)

    @staticmethod
    def normalize_stock_code(code):
        from morning_stock_assistant.shared.stock_resolver import StockResolver

        return StockResolver.normalize_code(code)

    def stock_resolver(self):
        from morning_stock_assistant.shared.stock_resolver import StockResolver

        return StockResolver(
            APP_ROOT,
            search_service_factory=self.search_service_factory,
        )

    def search_service_factory(self):
        if not self.api_base_url:
            raise RuntimeError("Render 서버 URL이 필요합니다.")

        return RemoteAnalysisClient(self.api_base_url)

    def add_group(self, _):
        name = (self.group_name.value or "").strip()

        if not name:
            self.snack("그룹명을 입력하세요.")
            return

        if name in self.groups:
            self.snack("이미 있는 그룹입니다.")
            self.selected_group = name
            self.render()
            return

        self.groups[name] = []
        self.selected_group = name
        self.group_name.value = ""
        save_json(self.watchlist_file, self.groups)
        self.snack("그룹을 추가했습니다.")
        self.render()

    def delete_group(self, _):
        if not self.selected_group:
            self.snack("삭제할 그룹이 없습니다.")
            return

        self.groups.pop(self.selected_group, None)
        save_json(self.watchlist_file, self.groups)
        self.selected_group = next(iter(self.groups), "")
        self.stock_preview = None
        first = self.current_stocks()[0] if self.current_stocks() else {}
        self.selected_chart_code = first.get("code", "")
        self.selected_holding_code = first.get("code", "")
        self.real_records = {}
        self.real_chart_cache = {}
        self.snack("그룹을 삭제했습니다.")
        self.render()

    def delete_stock(self, code):
        if not self.selected_group:
            return

        self.groups[self.selected_group] = [
            item for item in self.groups.get(self.selected_group, [])
            if item.get("code") != code
        ]
        save_json(self.watchlist_file, self.groups)
        self.stock_preview = None

        if self.selected_chart_code == code:
            first = self.current_stocks()[0] if self.current_stocks() else {}
            self.selected_chart_code = first.get("code", "")

        if self.selected_holding_code == code:
            first = self.current_stocks()[0] if self.current_stocks() else {}
            self.selected_holding_code = first.get("code", "")

        self.snack("삭제했습니다.")
        self.render()

    def on_holding_code_change(self, event):
        self.selected_holding_code = event.control.value or ""
        self.sync_holding_inputs()
        self.render()

    def sync_holding_inputs(self):
        holding = self.holdings.get(self.selected_holding_code, {})
        quantity = holding.get("quantity", None)
        avg_price = holding.get("avg_price", None)

        self.holding_quantity.value = (
            ""
            if quantity is None or quantity == ""
            else f"{safe_number(quantity):g}"
        )
        self.holding_avg_price.value = (
            ""
            if avg_price is None or avg_price == ""
            else f"{safe_number(avg_price):g}"
        )

    def save_holding(self, _):
        code = self.selected_holding_code

        if not code:
            self.snack("보유 종목을 선택하세요.")
            return

        quantity = safe_number(self.holding_quantity.value, -1)
        avg_price = safe_number(self.holding_avg_price.value, -1)

        if quantity < 0 or avg_price < 0:
            self.snack("수량과 평균가를 숫자로 입력하세요.")
            return

        self.holdings[code] = {
            "quantity": quantity,
            "avg_price": avg_price,
        }
        save_json(self.holdings_file, self.holdings)
        self.snack("보유 정보를 저장했습니다.")
        self.render()

    def delete_holding(self, _):
        code = self.selected_holding_code

        if not code or code not in self.holdings:
            self.snack("삭제할 보유 정보가 없습니다.")
            return

        self.holdings.pop(code, None)
        save_json(self.holdings_file, self.holdings)
        self.holding_quantity.value = ""
        self.holding_avg_price.value = ""
        self.snack("보유 정보를 삭제했습니다.")
        self.render()

    def load_real_analysis(self, _=None):
        if self.analysis_loading:
            self.snack("이미 실제 분석 데이터를 불러오는 중입니다.")
            return

        stocks = self.current_stocks()

        if not stocks:
            self.snack("분석할 관심종목이 없습니다.")
            return

        self.analysis_loading = True
        self.analysis_started_at = time.monotonic()
        self.analysis_total = len(stocks)
        self.analysis_done = 0
        self.analysis_current = "분석 준비 중"
        self.analysis_last_duration = 0
        self.analysis_loading_message = f"분석 준비 중... 0/{len(stocks)}"
        self.last_progress_update_at = 0.0
        self.real_data_error = ""
        self.render()
        self.update_visible_analysis_status()
        self.page.run_thread(self.load_real_analysis_worker, list(stocks), "수동")

    def start_auto_refresh(self):
        if self.auto_refresh_started:
            return

        self.auto_refresh_started = True
        self.page.run_thread(self.auto_refresh_worker)

    def auto_refresh_worker(self):
        self.wait_seconds(3)

        while True:
            if self.auto_refresh_enabled and not self.analysis_loading:
                stocks = self.current_stocks()

                if stocks:
                    self.analysis_loading = True
                    self.analysis_started_at = time.monotonic()
                    self.analysis_total = len(stocks)
                    self.analysis_done = 0
                    self.analysis_current = "자동 새로고침 준비 중"
                    self.analysis_last_duration = 0
                    self.analysis_loading_message = (
                        f"자동 새로고침 준비 중... 0/{len(stocks)}"
                    )
                    self.last_progress_update_at = 0.0
                    self.real_data_error = ""
                    self.update_visible_analysis_status()
                    self.load_real_analysis_worker(list(stocks), "자동")

            self.wait_seconds(self.auto_refresh_interval_minutes * 60)

    def wait_seconds(self, seconds):
        remaining = max(int(seconds), 1)

        while remaining > 0:
            time.sleep(min(5, remaining))
            remaining -= 5

    def load_real_analysis_worker(self, stocks, source="수동"):
        source_label = source

        try:
            records = None

            if self.api_base_url:
                try:
                    self.set_analysis_message(
                        f"{source} 서버 접속 중... Render 서버를 깨우는 중입니다. 0/{len(stocks)}",
                        "서버 접속 중",
                    )
                    self.set_analysis_message(
                        f"{source} 서버 분석 요청 중... 0/{len(stocks)}",
                        "서버 분석 요청 중",
                        update_page=False,
                    )
                    records = self.load_remote_analysis(stocks)
                    source_label = f"{source}/서버"
                    self.analysis_done = len(stocks)
                    self.analysis_current = "서버 분석 완료"
                except Exception as remote_exc:
                    self.analysis_loading_message = f"서버 분석 실패: {remote_exc}"
                    self.update_visible_analysis_status()
                    raise RuntimeError(
                        f"서버 분석 실패: {remote_exc}"
                    ) from remote_exc
            else:
                raise RuntimeError(
                    "Render 서버 URL이 필요합니다. 설정에서 서버 주소를 입력하세요."
                )

            if records is None:
                raise RuntimeError(
                    "서버에서 분석 결과를 받지 못했습니다."
                )

        except Exception as exc:
            self.real_data_error = str(exc)
            self.analysis_loading = False
            self.analysis_started_at = None
            self.analysis_current = ""
            self.analysis_loading_message = ""
            self.update_visible_analysis_status()
            self.safe_update()
            return

        self.real_records = {
            record.get("code", ""): record
            for record in records
            if record.get("code")
        }
        new_alerts = self.build_alerts(records)
        self.real_chart_cache = {}
        self.real_data_error = ""
        now = f"{datetime.now():%Y-%m-%d %H:%M}"
        self.real_data_loaded_at = f"{now} ({source_label})"

        if source == "자동":
            self.auto_refresh_last_at = now

        self.analysis_loading = False
        elapsed = self.analysis_elapsed_seconds()
        self.analysis_last_duration = elapsed
        self.analysis_done = self.analysis_total
        self.analysis_current = "새로고침 완료"
        self.analysis_started_at = None
        self.analysis_loading_message = f"{source_label} 새로고침 완료"
        self.update_visible_analysis_status()
        self.safe_update()
        if new_alerts:
            top = new_alerts[0]
            self.snack(f"{top['title']}: {top['message']}")
        else:
            self.snack(f"{source_label} 새로고침이 완료되었습니다. ({elapsed}초)")
        self.wait_seconds(3)
        self.analysis_loading_message = ""
        self.analysis_current = ""
        self.update_visible_analysis_status()

    def build_alerts(self, records):
        rules = AlertRules(
            score=self.alert_threshold_score,
            change=self.alert_threshold_change,
            upside=self.alert_threshold_upside,
            loss=self.alert_threshold_loss,
            bad_news=self.alert_threshold_bad_news,
        )
        new_alerts = AlertEngine(rules).build_alerts(
            records,
            holdings=self.holdings,
            alert_history=self.alert_history,
        )

        if new_alerts:
            self.alerts = (new_alerts + self.alerts)[:20]

        return new_alerts

    def load_remote_analysis(self, stocks):
        return RemoteAnalysisClient(self.api_base_url).build_records(
            stocks,
            holdings=self.holdings,
            preset="균형형",
            analyze=True,
            max_workers=6,
        )

    def news_alert_candidates(self, record, stock_name):
        return AlertEngine().news_alert_candidates(record, stock_name)

    def ai_news_summary(self, title, label, impact_score, date):
        return AlertEngine.ai_news_summary(title, label, impact_score, date)

    @staticmethod
    def news_reason(title, label, impact_score):
        return AlertEngine.news_reason(title, label, impact_score)

    def on_analysis_progress(self, index, total, name, code, source="수동"):
        self.analysis_total = total
        self.analysis_done = index
        self.analysis_current = f"{name} ({code})"
        self.analysis_loading_message = (
            f"{source} 분석 중... {index}/{total} {name} ({code})"
        )
        now = time.monotonic()

        if index >= total or now - self.last_progress_update_at >= 0.7:
            self.last_progress_update_at = now
            self.update_visible_analysis_status()

    def get_bridge(self):
        raise RuntimeError(
            "모바일 앱에서는 로컬 분석을 사용하지 않습니다. Render 서버 URL을 설정하세요."
        )

    def reload_data(self):
        if self.analysis_loading:
            self.snack("분석 중에는 저장 데이터를 새로고침할 수 없습니다.")
            return

        self.groups = load_json(self.watchlist_file, {})
        self.holdings = load_json(self.holdings_file, {})

        if self.selected_group not in self.groups:
            self.selected_group = next(iter(self.groups), "")

        if self.selected_chart_code not in {
            item.get("code") for item in self.current_stocks()
        }:
            first = self.current_stocks()[0] if self.current_stocks() else {}
            self.selected_chart_code = first.get("code", "")

        if self.selected_holding_code not in {
            item.get("code") for item in self.current_stocks()
        }:
            first = self.current_stocks()[0] if self.current_stocks() else {}
            self.selected_holding_code = first.get("code", "")

        self.real_records = {}
        self.real_chart_cache = {}
        self.real_data_loaded_at = ""
        self.real_data_error = ""
        self.alerts = []
        self.alert_history = set()
        self.snack("데이터를 다시 불러왔습니다.")
        self.render()

    def estimated_holding_values(self):
        krw_total = 0
        usd_total = 0

        for code, holding in self.holdings.items():
            quantity = safe_number(holding.get("quantity", 0))
            avg_price = safe_number(holding.get("avg_price", 0))

            if str(code).isdigit():
                krw_total += quantity * avg_price
            else:
                usd_total += quantity * avg_price

        return krw_total, usd_total

    def holding_text(self, code):
        holding = self.holdings.get(code)

        if not holding:
            return ""

        quantity = safe_number(holding.get("quantity", 0))
        avg_price = safe_number(holding.get("avg_price", 0))
        unit = "원" if str(code).isdigit() else "$"
        price = f"{avg_price:,.0f}원" if unit == "원" else f"${avg_price:,.2f}"

        return f"보유 {quantity:g}주 | 평균가 {price}"

    def portfolio_feedback_panel(self):
        items = self.portfolio_feedback_items()

        if not items:
            return self.card(
                ft.Row(
                    [
                        ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED, color="#94a3b8"),
                        ft.Text(
                            "보유 수량과 평균가를 입력하면 포트폴리오 피드백이 표시됩니다.",
                            size=12,
                            color="#64748b",
                            expand=True,
                        ),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=12,
                bgcolor="#f8fafc",
            )

        risk_count = sum(1 for item in items if item["level"] == "danger")
        good_count = sum(1 for item in items if item["level"] == "good")
        title = (
            "포트폴리오 주의 필요"
            if risk_count
            else "포트폴리오 양호"
            if good_count
            else "포트폴리오 점검"
        )
        color = "#ef4444" if risk_count else "#16a34a" if good_count else "#2563eb"

        return self.card(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET, color=color),
                            ft.Text(title, weight=ft.FontWeight.BOLD, expand=True),
                            ft.Text(f"{len(items)}종목", size=12, color="#64748b"),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Column(
                        [
                            self.portfolio_feedback_tile(item)
                            for item in items[:4]
                        ],
                        spacing=8,
                    ),
                ],
                spacing=10,
            ),
            padding=12,
            bgcolor="#f8fafc",
        )

    def portfolio_feedback_tile(self, item):
        color = {
            "danger": "#ef4444",
            "good": "#16a34a",
            "watch": "#f59e0b",
        }.get(item["level"], "#2563eb")

        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(item["name"], weight=ft.FontWeight.BOLD, expand=True),
                            ft.Text(item["pnl_text"], color=color, weight=ft.FontWeight.BOLD),
                        ],
                        spacing=8,
                    ),
                    ft.Text(item["summary"], size=12, color="#334155"),
                    ft.Text(item["feedback"], size=12, color="#64748b"),
                ],
                spacing=3,
            ),
            padding=10,
            border_radius=8,
            bgcolor="#ffffff",
        )

    def portfolio_feedback_items(self):
        items = []
        total_value = 0

        for code, holding in self.holdings.items():
            quantity = safe_number(holding.get("quantity", 0))
            current_price = self.current_price_for(code)

            if quantity <= 0 or current_price <= 0:
                continue

            total_value += quantity * current_price

        for code, holding in self.holdings.items():
            item = self.portfolio_feedback_item(code, holding, total_value)

            if item:
                items.append(item)

        level_rank = {"danger": 0, "watch": 1, "good": 2, "info": 3}
        items.sort(
            key=lambda item: (
                level_rank.get(item["level"], 9),
                -abs(item["pnl_rate"]),
            )
        )
        return items

    def portfolio_feedback_item(self, code, holding, total_value):
        quantity = safe_number(holding.get("quantity", 0))
        avg_price = safe_number(holding.get("avg_price", 0))
        current_price = self.current_price_for(code)

        if quantity <= 0 or avg_price <= 0:
            return None

        record = self.real_record(code)
        name = self.stock_name_for(code)
        score = self.final_score_for(code)
        news_score = self.news_score_for(code)
        current_value = quantity * current_price if current_price > 0 else quantity * avg_price
        cost = quantity * avg_price
        pnl_rate = ((current_value - cost) / cost * 100) if cost else 0
        weight = (current_value / total_value * 100) if total_value else 0
        level, feedback = self.portfolio_feedback_text(
            pnl_rate,
            weight,
            score,
            news_score,
            record,
        )
        currency = record.get("currency", None) if record else None
        price_text = (
            self.format_price(code, current_price, currency)
            if current_price > 0
            else "현재가 없음"
        )
        value_text = self.format_price(code, current_value, currency)

        return {
            "code": code,
            "name": name,
            "level": level,
            "pnl_rate": pnl_rate,
            "pnl_text": f"{pnl_rate:+.1f}%",
            "summary": (
                f"비중 {weight:.1f}% | 현재 {price_text} | 평가 {value_text} | "
                f"점수 {score:.1f} | 뉴스 {news_score:.1f}"
            ),
            "feedback": feedback,
        }

    def portfolio_feedback_text(self, pnl_rate, weight, score, news_score, record):
        if pnl_rate <= self.alert_threshold_loss and news_score <= self.alert_threshold_bad_news:
            return "danger", "손실과 뉴스 리스크가 겹쳐 비중 축소 또는 추가 확인이 필요합니다."

        if pnl_rate <= self.alert_threshold_loss:
            return "danger", "평균가 대비 손실 구간입니다. 하락 원인과 지지 구간을 먼저 확인하세요."

        if weight >= 35 and score < 55:
            return "watch", "비중이 큰데 점수가 낮습니다. 포트폴리오 쏠림을 점검하세요."

        if news_score <= self.alert_threshold_bad_news:
            return "watch", "뉴스 점수가 낮습니다. 악재가 일시적인지 구조적인지 확인하세요."

        freshness_days = safe_number(record.get("freshness_days", -1), -1) if record else -1

        if freshness_days >= 3:
            return "watch", "가격 기준일이 오래되었습니다. 최신 가격 확인 후 판단하세요."

        if score >= self.alert_threshold_score and pnl_rate >= 0:
            return "good", "점수와 수익률이 모두 양호합니다. 추세 유지 여부를 확인하세요."

        return "info", "큰 위험 신호는 제한적입니다. 목표 비중과 새 뉴스만 점검하세요."

    def current_price_for(self, code):
        record = self.real_record(code)

        if record:
            price = safe_number(record.get("price", 0))

            if price > 0:
                return price

        holding = self.holdings.get(code, {})
        return safe_number(holding.get("avg_price", 0))

    def stock_name_for(self, code):
        for item in self.current_stocks():
            if item.get("code") == code:
                return item.get("name", code)

        return code

    def holding_tiles(self):
        code_to_name = {
            item.get("code", ""): item.get("name", item.get("code", ""))
            for item in self.current_stocks()
        }
        rows = []

        for code, holding in self.holdings.items():
            quantity = safe_number(holding.get("quantity", 0))
            avg_price = safe_number(holding.get("avg_price", 0))

            if quantity <= 0:
                continue

            is_kr = str(code).isdigit()
            current_price = self.current_price_for(code)
            value = quantity * current_price if current_price > 0 else quantity * avg_price
            cost = quantity * avg_price
            pnl_rate = ((value - cost) / cost * 100) if cost else 0
            value_text = f"{value:,.0f}원" if is_kr else f"${value:,.2f}"
            avg_text = f"{avg_price:,.0f}원" if is_kr else f"${avg_price:,.2f}"
            current_text = (
                f"{current_price:,.0f}원"
                if is_kr
                else f"${current_price:,.2f}"
            )
            feedback = self.portfolio_feedback_item(code, holding, value)
            pnl_color = "#ef4444" if pnl_rate >= 0 else "#2563eb"

            rows.append(
                self.card(
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(
                                        code_to_name.get(code, code),
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Text(
                                        f"{code} | {quantity:g}주 | 평균가 {avg_text}",
                                        size=12,
                                        color="#64748b",
                                    ),
                                    ft.Text(
                                        f"현재가 {current_text} | 손익 {pnl_rate:+.1f}%",
                                        size=12,
                                        color=pnl_color,
                                    ),
                                    *(
                                        [ft.Text(feedback["feedback"], size=11, color="#64748b")]
                                        if feedback
                                        else []
                                    ),
                                ],
                                expand=True,
                                spacing=2,
                            ),
                            ft.Text(
                                value_text,
                                weight=ft.FontWeight.BOLD,
                                color="#111827",
                            ),
                        ]
                    ),
                    padding=13,
                )
            )

        return rows

    def empty_state(self, text):
        return self.card(
            ft.Container(
                content=ft.Text(text, color="#64748b"),
                alignment=ft.Alignment(0, 0),
                height=80,
            )
        )

    def snack(self, text):
        self.page.snack_bar = ft.SnackBar(ft.Text(text))
        self.page.snack_bar.open = True
        self.page.update()

    def safe_update(self):
        try:
            self.render()
        except Exception:
            try:
                self.page.update()
            except Exception:
                pass


def main(page: ft.Page):
    MobileStockApp(page).run()


if __name__ == "__main__":
    if str(APP_ROOT / "src") not in sys.path:
        sys.path.insert(0, str(APP_ROOT / "src"))

    ft.run(main)
