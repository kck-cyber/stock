from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from morning_stock_assistant.database.models import Base


class DatabaseManager:
    """
    SQLite Database Manager
    """

    def __init__(self, project_root: Path):

        database_dir = project_root / "database"
        database_dir.mkdir(exist_ok=True)

        self.database_path = database_dir / "morning_stock.db"

        self.engine = create_engine(
            f"sqlite:///{self.database_path}",
            echo=False,
            future=True,
        )

        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
        )

    def create_tables(self):

        Base.metadata.create_all(bind=self.engine)

    def get_session(self):

        return self.SessionLocal()