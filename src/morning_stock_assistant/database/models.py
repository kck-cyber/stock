from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text

from sqlalchemy.orm import declarative_base

from datetime import datetime

Base = declarative_base()


class Company(Base):

    __tablename__ = "company"

    id = Column(Integer, primary_key=True, autoincrement=True)

    company_name = Column(String(100), nullable=False)

    stock_code = Column(String(20))

    market = Column(String(20))

    current_price = Column(Float)

    market_cap = Column(Float)

    per = Column(Float)

    eps = Column(Float)

    book_value = Column(Float)

    currency = Column(String(10))

    sector = Column(String(100))

    industry = Column(String(100))

    last_collected_at = Column(DateTime)

    target_price = Column(Float)

    fair_price = Column(Float)

    holding_quantity = Column(Integer)

    average_price = Column(Float)

    investment_point = Column(Text)

    risk_factor = Column(Text)

    recent_earnings = Column(Text)

    ai_analysis = Column(Text)

    memo = Column(Text)

    created_at = Column(DateTime, default=datetime.now)

    updated_at = Column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
    )