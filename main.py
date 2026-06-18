"""
==========================================================
Morning Stock Assistant Pro
Database Manager
==========================================================

SQLite + SQLAlchemy
"""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------
# 프로젝트 경로
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATABASE_DIR = PROJECT_ROOT / "database"

DATABASE_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_FILE = DATABASE_DIR / "stock.db"

DATABASE_URL = f"sqlite:///{DATABASE_FILE}"


# ---------------------------------------------------------
# Base Model
# ---------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------
# Engine
# ---------------------------------------------------------

engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True
)

# ---------------------------------------------------------
# Session
# ---------------------------------------------------------

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False
)


# ---------------------------------------------------------
# Session Generator
# ---------------------------------------------------------

def get_session():

    session = SessionLocal()

    try:

        yield session

    finally:

        session.close()


# ---------------------------------------------------------
# Database Initialize
# ---------------------------------------------------------

def initialize_database():

    Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------
# Database Check
# ---------------------------------------------------------

def database_exists():

    return DATABASE_FILE.exists()