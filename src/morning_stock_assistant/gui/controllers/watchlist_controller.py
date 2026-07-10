"""
Watchlist Controller

GroupPanel
StockPanel
ResultPanel
ChartPanel
NewsPanel
연결 담당
"""


class WatchlistController:

    def __init__(
        self,
        service,
        group_panel,
        stock_panel,
        result_panel,
        chart_panel,
        news_panel,
    ):

        self.service = service

        self.group_panel = group_panel
        self.stock_panel = stock_panel
        self.result_panel = result_panel
        self.chart_panel = chart_panel
        self.news_panel = news_panel

    # ---------------------------------------

    def group_selected(self, group):

        self.stock_panel.set_group(group)

    # ---------------------------------------

    def stock_selected(self, stock):

        code = stock["code"]

        result = self.service.analyze(
            code,
            "2025",
            "11011"
        )

        self.result_panel.show(result)

        self.chart_panel.show(stock)

        self.news_panel.show(stock)

    # ---------------------------------------

    def refresh(self):

        self.group_panel.refresh()

        self.stock_panel.refresh()