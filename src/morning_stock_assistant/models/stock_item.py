"""
Stock Item Model

Morning Stock Assistant Pro
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StockItem:
    """
    관심종목 객체
    """

    # -------------------------
    # 기본 정보
    # -------------------------
    code: str
    name: str
    market: str = ""

    # -------------------------
    # 현재가
    # -------------------------
    price: float = 0.0
    change_rate: float = 0.0

    # -------------------------
    # 재무
    # -------------------------
    per: float = 0.0
    pbr: float = 0.0

    roe: float = 0.0
    debt_ratio: float = 0.0

    net_income: int = 0

    # -------------------------
    # AI
    # -------------------------
    score: float = 0.0
    signal: str = ""

    comment: str = ""

    # -------------------------
    # 사용자
    # -------------------------
    memo: str = ""

    favorite: bool = False

    # -------------------------
    # 시간
    # -------------------------
    updated: Optional[str] = None

    # -------------------------
    # JSON 저장
    # -------------------------
    def to_dict(self):

        return {
            "code": self.code,
            "name": self.name,
            "market": self.market,

            "price": self.price,
            "change_rate": self.change_rate,

            "per": self.per,
            "pbr": self.pbr,

            "roe": self.roe,
            "debt_ratio": self.debt_ratio,

            "net_income": self.net_income,

            "score": self.score,
            "signal": self.signal,
            "comment": self.comment,

            "memo": self.memo,
            "favorite": self.favorite,

            "updated": self.updated,
        }

    # -------------------------
    # JSON 로드
    # -------------------------
    @classmethod
    def from_dict(cls, data):

        return cls(

            code=data.get("code", ""),

            name=data.get("name", ""),

            market=data.get("market", ""),

            price=data.get("price", 0),

            change_rate=data.get("change_rate", 0),

            per=data.get("per", 0),

            pbr=data.get("pbr", 0),

            roe=data.get("roe", 0),

            debt_ratio=data.get("debt_ratio", 0),

            net_income=data.get("net_income", 0),

            score=data.get("score", 0),

            signal=data.get("signal", ""),

            comment=data.get("comment", ""),

            memo=data.get("memo", ""),

            favorite=data.get("favorite", False),

            updated=data.get("updated"),
        )