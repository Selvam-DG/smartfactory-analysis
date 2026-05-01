from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine

load_dotenv()


def get_engine() -> Engine:
    """
    Create a SQLAlchemy engine using DATABASE_URL from environment variables.

    Expected DATABASE_URL example:
        postgresql+psycopg://smartfactory:smartfactory@localhost:5432/smartfactory
    """
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise ValueError(
            "DATABASE_URL environment variable is required. "
            "Example: postgresql+psycopg://smartfactory:smartfactory@localhost:5432/smartfactory"
        )

    return create_engine(
        database_url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        future=True,
    )
