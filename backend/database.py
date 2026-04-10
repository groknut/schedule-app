"""Database engine and session factory."""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base

DATABASE_URL = "sqlite:///./schedule.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite-specific
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    Base.metadata.create_all(bind=engine)


def run_migrations():
    """
    Безопасная автомиграция: добавляет недостающие колонки в существующие таблицы.
    SQLAlchemy create_all() создаёт только новые таблицы, но не меняет схему
    существующих — поэтому при обновлении модели нужно явно добавить колонки.
    """
    with engine.connect() as conn:
        # Получаем список уже существующих колонок таблицы employees
        result = conn.execute(text("PRAGMA table_info(employees)"))
        existing_columns = {row[1] for row in result.fetchall()}

        migrations = [
            # (имя_колонки, SQL для ALTER TABLE)
            (
                "password_hash",
                "ALTER TABLE employees ADD COLUMN password_hash VARCHAR(255)",
            ),
            (
                "is_active",
                "ALTER TABLE employees ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1",
            ),
        ]

        for col_name, sql in migrations:
            if col_name not in existing_columns:
                conn.execute(text(sql))
                print(f"✅ Migration: added column 'employees.{col_name}'")

        conn.commit()


def get_db():
    """FastAPI dependency: yields a DB session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
