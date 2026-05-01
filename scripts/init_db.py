"""
Initialize SmartFactory PostgreSQL database.

Reads DATABASE_URL from environment variables and executes sql/schema.sql.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()
LOGGER = logging.getLogger(__name__)

EXPECTED_TABLES = [
    ("raw", "azure_telemetry"),
    ("raw", "azure_errors"),
    ("raw", "azure_failures"),
    ("raw", "azure_maintenance"),
    ("raw", "azure_machines"),
    ("raw", "machine_sensor_data"),
    ("raw", "breakdown_logs"),
    ("raw", "production_data"),
    ("raw", "maintenance_schedule"),
    ("analytics", "machine_daily_kpi"),
    ("analytics", "machine_reliability"),
    ("analytics", "downtime_pareto"),
    ("analytics", "downtime_predictions"),
]


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError(
            "DATABASE_URL is required. \nExample: "
            "postgresql+psycopg://smartfactory:smartfactory@localhost:5432/smartfactory"
        )

    return database_url


def get_schema_path() -> Path:
    project_root = Path(__file__).resolve().parents[1]
    schema_path = project_root / "sql" / "schema.sql"

    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    return schema_path


def run_schema(database_url: str, schema_path: Path) -> None:
    engine = create_engine(database_url, pool_pre_ping=True)

    schema_sql = schema_path.read_text(encoding="utf-8")

    LOGGER.info("Running database schema from %s", schema_path)

    try:
        with engine.begin() as connection:
            connection.execute(text(schema_sql))
    except SQLAlchemyError:
        LOGGER.exception("Schema initialization failed")
        raise

    LOGGER.info("Schema executed successfully")


def verify_tables(database_url: str) -> None:
    engine = create_engine(database_url, pool_pre_ping=True)

    query = text(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = :schema_name
              AND table_name = :table_name
        );
        """
    )

    try:
        with engine.connect() as connection:
            for schema_name, table_name in EXPECTED_TABLES:
                exists = connection.execute(
                    query,
                    {
                        "schema_name": schema_name,
                        "table_name": table_name,
                    },
                ).scalar_one()

                if exists:
                    LOGGER.info("Confirmed table created: %s.%s", schema_name, table_name)
                else:
                    LOGGER.warning("Expected table missing: %s.%s", schema_name, table_name)

    except SQLAlchemyError:
        LOGGER.exception("Table verification failed")
        raise


def main() -> None:
    configure_logging()

    database_url = get_database_url()
    schema_path = get_schema_path()

    run_schema(database_url=database_url, schema_path=schema_path)
    verify_tables(database_url=database_url)

    LOGGER.info("Database initialization completed successfully")


if __name__ == "__main__":
    main()