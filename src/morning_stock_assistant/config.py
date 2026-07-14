"""
Morning Stock Assistant Pro

프로그램 전체 설정
"""

from pathlib import Path
import os

from dotenv import load_dotenv


load_dotenv()


# =====================================================
# Project
# =====================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# =====================================================
# Directory
# =====================================================

DATA_DIR = PROJECT_ROOT / "data"

CACHE_DIR = PROJECT_ROOT / "cache"

REPORT_DIR = PROJECT_ROOT / "reports"

LOG_DIR = PROJECT_ROOT / "logs"


for directory in (

    DATA_DIR,

    CACHE_DIR,

    REPORT_DIR,

    LOG_DIR,

):

    directory.mkdir(parents=True, exist_ok=True)


# =====================================================
# Database
# =====================================================

DATABASE_FILE = DATA_DIR / "morning_stock.db"


# =====================================================
# API KEY
# =====================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

DART_API_KEY = os.getenv("DART_API_KEY", "")


# =====================================================
# AI
# =====================================================

OPENAI_MODEL = "gpt-5.1"


# =====================================================
# Server
# =====================================================

DEFAULT_ANALYSIS_SERVER_URL = (
    "https://morning-stock-api-613090042286.asia-northeast3.run.app"
)


# =====================================================
# News
# =====================================================

MAX_NEWS_COUNT = 10


# =====================================================
# Cache
# =====================================================

USE_CACHE = True

CACHE_EXPIRE_HOURS = 12


# =====================================================
# Yahoo
# =====================================================

DEFAULT_PERIOD = "1y"

DEFAULT_INTERVAL = "1d"


# =====================================================
# DART
# =====================================================

DEFAULT_BUSINESS_YEAR = "2024"

DEFAULT_REPORT_CODE = "11011"


# =====================================================
# GUI
# =====================================================

WINDOW_WIDTH = 1200

WINDOW_HEIGHT = 900
