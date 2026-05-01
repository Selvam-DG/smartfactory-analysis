"""
Shared pytest fixtures for SmartFactory Reliability Analytics.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine


def _strip_postgres_comments(schema_sql: str) -> str:
    """
    Remove PostgreSQL COMMENT ON statements for SQLite compatibility.
    Handles multi-line COMMENT ON TABLE ... IS '...'; statements.
    """
    return re.sub(
        r"COMMENT\s+ON\s+TABLE\s+.*?;",
        "",
        schema_sql,
        flags=re.IGNORECASE | re.DOTALL,
    )


def _make_schema_sqlite_compatible(schema_sql: str) -> str:
    """
    Convert the production PostgreSQL schema.sql into a SQLite-compatible form.

    SQLite compatibility changes:
    - Remove CREATE SCHEMA statements.
    - Remove COMMENT ON TABLE statements.
    - Replace BIGSERIAL / SERIAL with INTEGER.
    - Replace TIMESTAMPTZ / TIMESTAMP WITH TIME ZONE with TEXT.
    - Keep raw.table_name and analytics.table_name by attaching SQLite databases
      named raw and analytics.
    """
    schema_sql = _strip_postgres_comments(schema_sql)

    replacements = [
        (r"CREATE\s+SCHEMA\s+IF\s+NOT\s+EXISTS\s+\w+;", ""),
        (r"BIGSERIAL", "INTEGER"),
        (r"\bSERIAL\b", "INTEGER"),
        (r"TIMESTAMP\s+WITH\s+TIME\s+ZONE", "TEXT"),
        (r"TIMESTAMPTZ", "TEXT"),
        (r"NOW\(\)", "CURRENT_TIMESTAMP"),
        (r"BOOLEAN", "INTEGER"),
        (r"NUMERIC\(\d+,\s*\d+\)", "REAL"),
        (r"NUMERIC", "REAL"),
    ]

    for pattern, replacement in replacements:
        schema_sql = re.sub(pattern, replacement, schema_sql, flags=re.IGNORECASE)

    return schema_sql


@pytest.fixture()
def test_engine():
    """
    Create an in-memory SQLite database with attached raw and analytics schemas.

    SQLite does not support PostgreSQL schemas directly, so this fixture attaches
    two in-memory databases named raw and analytics. This allows statements like
    CREATE TABLE raw.machine_sensor_data (...) to work during tests.
    """
    engine = create_engine("sqlite:///:memory:", future=True)

    project_root = Path(__file__).resolve().parents[1]
    schema_path = project_root / "sql" / "schema.sql"

    assert schema_path.exists(), f"Missing schema file: {schema_path}"

    schema_sql = schema_path.read_text(encoding="utf-8")
    sqlite_schema_sql = _make_schema_sqlite_compatible(schema_sql)

    raw_connection = engine.raw_connection()

    try:
        cursor = raw_connection.cursor()
        cursor.execute("ATTACH DATABASE ':memory:' AS raw;")
        cursor.execute("ATTACH DATABASE ':memory:' AS analytics;")
        cursor.executescript(sqlite_schema_sql)
        raw_connection.commit()
    finally:
        raw_connection.close()

    return engine


@pytest.fixture()
def sample_sensor_df() -> pd.DataFrame:
    """
    Return 20 valid hourly sensor rows.
    """
    timestamps = pd.date_range(
        start="2024-01-01 00:00:00",
        periods=20,
        freq="h",
        tz="UTC",
    )

    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "machine_id": ["TBM-01"] * 20,
            "machine_type": ["Tyre Building Machine"] * 20,
            "shift": ["A"] * 8 + ["B"] * 8 + ["C"] * 4,
            "temperature_c": [58.0 + i * 0.1 for i in range(20)],
            "vibration_mm_s": [4.2] * 20,
            "motor_current_a": [42.0] * 20,
            "pressure_bar": [6.8] * 20,
            "speed_rpm": [95.0] * 20,
            "production_count": [52] * 20,
            "anomaly_flag": [False] * 20,
            "data_source": ["synthetic_tyre_factory"] * 20,
        }
    )


@pytest.fixture()
def sample_breakdown_df() -> pd.DataFrame:
    """
    Return 5 valid breakdown log rows.
    """
    return pd.DataFrame(
        {
            "log_id": [f"BD-{i:06d}" for i in range(1, 6)],
            "machine_id": ["TBM-01", "TBM-01", "BA-01", "CV-01", "MX-01"],
            "failure_type": [
                "Bearing Failure",
                "Belt Breakage",
                "PLC Fault",
                "Overheating",
                "Motor Overload",
            ],
            "start_time": pd.to_datetime(
                [
                    "2024-01-02 08:00:00",
                    "2024-01-05 10:00:00",
                    "2024-01-08 14:00:00",
                    "2024-01-11 20:00:00",
                    "2024-01-15 06:00:00",
                ],
                utc=True,
            ),
            "end_time": pd.to_datetime(
                [
                    "2024-01-02 12:00:00",
                    "2024-01-05 12:30:00",
                    "2024-01-08 17:00:00",
                    "2024-01-12 02:00:00",
                    "2024-01-15 09:00:00",
                ],
                utc=True,
            ),
            "downtime_hours": [4.0, 2.5, 3.0, 6.0, 3.0],
            "shift": ["A", "A", "B", "C", "A"],
            "root_cause": [
                "Bearing wear",
                "Belt tension issue",
                "PLC IO module fault",
                "Cooling fan failure",
                "High motor current",
            ],
            "action_taken": [
                "Replaced bearing",
                "Adjusted belt tension",
                "Replaced IO module",
                "Replaced cooling fan",
                "Reset overload relay",
            ],
            "technician": [
                "TECH-MECH-01",
                "TECH-MECH-02",
                "TECH-AUTO-01",
                "TECH-ELEC-01",
                "TECH-ELEC-02",
            ],
            "severity": ["High", "Medium", "Medium", "High", "Medium"],
            "spare_part_cost_eur": [450.0, 180.0, 650.0, 250.0, 520.0],
            "data_source": ["synthetic_tyre_factory"] * 5,
        }
    )