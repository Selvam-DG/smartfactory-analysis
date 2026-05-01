"""
ETL pipeline for SmartFactory Reliability Analytics.

Pipeline steps:
1. Read raw CSV files from data/raw.
2. Validate and clean each DataFrame.
3. Bulk load into PostgreSQL raw schema using psycopg2 execute_values.
4. Build analytics tables using SQLAlchemy SQL execution.
5. Log row counts, dropped rows, timing, and analytics rows written.

Hybrid data strategy:
- Main operational analytics use synthetic tyre-factory CSVs:
  machine_sensor_data.csv
  breakdown_logs.csv
  production_data.csv
  maintenance_schedule.csv

- Azure Predictive Maintenance sample-style files may also exist in data/raw:
  azure_telemetry.csv
  azure_errors.csv
  azure_failures.csv
  azure_maintenance.csv
  azure_machines.csv

This ETL loads the 4 SmartFactory operational files and includes optional Azure loaders
so the project remains aligned with the hybrid architecture.
"""

from __future__ import annotations

import argparse
import logging
import os
import time
from pathlib import Path
from typing import Any

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from sqlalchemy import Engine, text

from src.utils.db import get_engine


LOG_FORMAT = "%(asctime)s %(levelname)-8s %(message)s"

LOGGER = logging.getLogger(__name__)


SMARTFACTORY_FILES = {
    "sensors": "machine_sensor_data.csv",
    "breakdown": "breakdown_logs.csv",
    "production": "production_data.csv",
    "schedule": "maintenance_schedule.csv",
}

AZURE_FILES = {
    "azure_telemetry": "azure_telemetry.csv",
    "azure_errors": "azure_errors.csv",
    "azure_failures": "azure_failures.csv",
    "azure_maintenance": "azure_maintenance.csv",
    "azure_machines": "azure_machines.csv",
}


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


def get_psycopg2_database_url() -> str:
    """
    psycopg2 does not understand the SQLAlchemy '+psycopg' driver token.

    Converts:
        postgresql+psycopg://...
    to:
        postgresql://...
    """
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required.")

    return database_url.replace("postgresql+psycopg://", "postgresql://")


# ============================================================
# STEP 1 — Read CSV files
# ============================================================

def read_csv_if_exists(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        LOGGER.warning("CSV file not found: %s", path)
        return None

    df = pd.read_csv(path)
    LOGGER.info("Read file=%s rows=%s", path.name, len(df))
    return df


def read_raw_csvs(raw_dir: Path) -> dict[str, pd.DataFrame]:
    """
    Read SmartFactory and optional Azure PM CSV files from data/raw.
    """
    dataframes: dict[str, pd.DataFrame] = {}

    for key, filename in SMARTFACTORY_FILES.items():
        path = raw_dir / filename
        df = read_csv_if_exists(path)

        if df is None:
            raise FileNotFoundError(f"Required SmartFactory CSV missing: {path}")

        dataframes[key] = df

    for key, filename in AZURE_FILES.items():
        path = raw_dir / filename
        df = read_csv_if_exists(path)

        if df is not None:
            dataframes[key] = df

    return dataframes


# ============================================================
# STEP 2 — Validate each DataFrame
# ============================================================

def log_dropped_rows(table_name: str, reason: str, before_count: int, after_count: int) -> None:
    dropped = before_count - after_count

    if dropped > 0:
        LOGGER.warning(
            "Validation dropped rows table=%s reason='%s' dropped=%s before=%s after=%s",
            table_name,
            reason,
            dropped,
            before_count,
            after_count,
        )
    else:
        LOGGER.info(
            "Validation passed table=%s reason='%s' dropped=0 rows=%s",
            table_name,
            reason,
            after_count,
        )


def validate_sensors(df: pd.DataFrame) -> pd.DataFrame:
    table_name = "raw.machine_sensor_data"
    df = df.copy()
    start_count = len(df)

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)

    before = len(df)
    df = df.dropna(subset=["machine_id", "timestamp"])
    log_dropped_rows(table_name, "null machine_id or timestamp", before, len(df))

    before = len(df)
    df = df[
        (df["temperature_c"].between(-10, 150))
        & (df["vibration_mm_s"].between(0, 30))
        & (df["motor_current_a"].between(0, 200))
    ]
    log_dropped_rows(
        table_name,
        "sensor values outside valid ranges",
        before,
        len(df),
    )

    before = len(df)
    df = df.drop_duplicates(subset=["machine_id", "timestamp"], keep="first")
    log_dropped_rows(table_name, "duplicate machine_id/timestamp", before, len(df))

    if "anomaly_flag" in df.columns:
        df["anomaly_flag"] = df["anomaly_flag"].astype(bool)

    if "data_source" not in df.columns:
        df["data_source"] = "synthetic_tyre_factory"

    LOGGER.info(
        "Validated sensors rows_before=%s rows_after=%s total_dropped=%s",
        start_count,
        len(df),
        start_count - len(df),
    )

    return df


def validate_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    table_name = "raw.breakdown_logs"
    df = df.copy()
    start_count = len(df)

    df["start_time"] = pd.to_datetime(df["start_time"], errors="coerce", utc=True)
    df["end_time"] = pd.to_datetime(df["end_time"], errors="coerce", utc=True)

    before = len(df)
    df = df.dropna(subset=["machine_id", "start_time", "failure_type"])
    log_dropped_rows(table_name, "null machine_id/start_time/failure_type", before, len(df))

    before = len(df)
    df["downtime_hours"] = pd.to_numeric(df["downtime_hours"], errors="coerce")
    df = df[df["downtime_hours"].between(0, 720)]
    log_dropped_rows(table_name, "downtime_hours outside 0-720", before, len(df))

    before = len(df)
    df = df.drop_duplicates(subset=["log_id"], keep="first")
    log_dropped_rows(table_name, "duplicate log_id", before, len(df))

    if "data_source" not in df.columns:
        df["data_source"] = "synthetic_tyre_factory"

    LOGGER.info(
        "Validated breakdown rows_before=%s rows_after=%s total_dropped=%s",
        start_count,
        len(df),
        start_count - len(df),
    )

    return df


def validate_production(df: pd.DataFrame) -> pd.DataFrame:
    table_name = "raw.production_data"
    df = df.copy()
    start_count = len(df)

    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date

    before = len(df)
    df = df.dropna(subset=["date", "machine_id", "shift"])
    log_dropped_rows(table_name, "null date/machine_id/shift", before, len(df))

    df["actual_qty"] = pd.to_numeric(df["actual_qty"], errors="coerce").fillna(0)
    df["rejected_qty"] = pd.to_numeric(df["rejected_qty"], errors="coerce").fillna(0)

    df["actual_qty"] = df["actual_qty"].clip(lower=0).round().astype(int)
    df["rejected_qty"] = df["rejected_qty"].clip(lower=0).round().astype(int)

    # Rejected quantity cannot exceed actual quantity.
    df["rejected_qty"] = df[["rejected_qty", "actual_qty"]].min(axis=1)

    # Required rule: recalculate good_qty.
    df["good_qty"] = df["actual_qty"] - df["rejected_qty"]

    df["planned_qty"] = (
        pd.to_numeric(df["planned_qty"], errors="coerce")
        .fillna(0)
        .clip(lower=0)
        .round()
        .astype(int)
    )

    df["efficiency_pct"] = (
        df["actual_qty"] / df["planned_qty"].replace(0, pd.NA) * 100
    ).fillna(0).round(2)

    if "data_source" not in df.columns:
        df["data_source"] = "synthetic_tyre_factory"

    LOGGER.info(
        "Validated production rows_before=%s rows_after=%s total_dropped=%s",
        start_count,
        len(df),
        start_count - len(df),
    )

    return df


def validate_schedule(df: pd.DataFrame) -> pd.DataFrame:
    table_name = "raw.maintenance_schedule"
    df = df.copy()
    start_count = len(df)

    df["planned_date"] = pd.to_datetime(df["planned_date"], errors="coerce").dt.date
    df["actual_date"] = pd.to_datetime(df["actual_date"], errors="coerce").dt.date

    if "delay_days" in df.columns:
        df["delay_days"] = pd.to_numeric(df["delay_days"], errors="coerce")

    if "data_source" not in df.columns:
        df["data_source"] = "synthetic_tyre_factory"

    LOGGER.info(
        "Validated schedule rows_before=%s rows_after=%s total_dropped=%s",
        start_count,
        len(df),
        start_count - len(df),
    )

    LOGGER.info("Schedule validation table=%s rule='parse dates only'", table_name)

    return df


def validate_azure_dataframe(df: pd.DataFrame, table_key: str) -> pd.DataFrame:
    """
    Light validation for optional Azure PM sample-style files.

    These are reference/seed files in the hybrid architecture.
    Strict business validation is intentionally not applied here.
    """
    df = df.copy()

    for column in ["datetime", "timestamp"]:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], errors="coerce", utc=True)

    if "data_source" not in df.columns:
        df["data_source"] = "azure_predictive_maintenance_sample"

    LOGGER.info("Validated optional Azure table=%s rows=%s", table_key, len(df))
    return df


def validate_dataframes(dataframes: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    validated = {
        "sensors": validate_sensors(dataframes["sensors"]),
        "breakdown": validate_breakdown(dataframes["breakdown"]),
        "production": validate_production(dataframes["production"]),
        "schedule": validate_schedule(dataframes["schedule"]),
    }

    for key in AZURE_FILES:
        if key in dataframes:
            validated[key] = validate_azure_dataframe(dataframes[key], key)

    return validated


# ============================================================
# STEP 3 — Bulk load raw schema using psycopg2 execute_values
# ============================================================

def normalize_value(value: Any) -> Any:
    if pd.isna(value):
        return None

    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()

    return value


def dataframe_to_records(df: pd.DataFrame, columns: list[str]) -> list[tuple[Any, ...]]:
    return [
        tuple(normalize_value(row[column]) for column in columns)
        for _, row in df[columns].iterrows()
    ]


def bulk_insert_execute_values(
    table_name: str,
    df: pd.DataFrame,
    columns: list[str],
    conflict_clause: str,
) -> int:
    """
    Bulk insert DataFrame rows into PostgreSQL using psycopg2 execute_values.

    Returns number of inserted rows based on cursor.rowcount.
    With ON CONFLICT DO NOTHING, duplicates are ignored.
    """
    if df.empty:
        LOGGER.warning("Skipping empty dataframe table=%s", table_name)
        return 0

    missing_columns = set(columns) - set(df.columns)
    if missing_columns:
        raise ValueError(f"Missing columns for {table_name}: {sorted(missing_columns)}")

    records = dataframe_to_records(df, columns)

    column_sql = ", ".join(columns)
    insert_sql = f"""
        INSERT INTO {table_name} ({column_sql})
        VALUES %s
        {conflict_clause}
    """

    database_url = get_psycopg2_database_url()

    started_at = time.perf_counter()

    with psycopg2.connect(database_url) as connection:
        with connection.cursor() as cursor:
            execute_values(cursor, insert_sql, records, page_size=5000)
            inserted_rows = cursor.rowcount
        connection.commit()

    duration_seconds = time.perf_counter() - started_at

    LOGGER.info(
        "Loaded raw table=%s attempted_rows=%s inserted_rows=%s duration_seconds=%.2f",
        table_name,
        len(records),
        inserted_rows,
        duration_seconds,
    )

    return inserted_rows


def load_sensors(df: pd.DataFrame) -> int:
    columns = [
        "timestamp",
        "machine_id",
        "machine_type",
        "shift",
        "temperature_c",
        "vibration_mm_s",
        "motor_current_a",
        "pressure_bar",
        "speed_rpm",
        "production_count",
        "anomaly_flag",
        "data_source",
    ]

    return bulk_insert_execute_values(
        table_name="raw.machine_sensor_data",
        df=df,
        columns=columns,
        conflict_clause="ON CONFLICT (machine_id, timestamp) DO NOTHING",
    )


def load_breakdown(df: pd.DataFrame) -> int:
    columns = [
        "log_id",
        "machine_id",
        "failure_type",
        "start_time",
        "end_time",
        "downtime_hours",
        "shift",
        "root_cause",
        "action_taken",
        "technician",
        "severity",
        "spare_part_cost_eur",
        "data_source",
    ]

    return bulk_insert_execute_values(
        table_name="raw.breakdown_logs",
        df=df,
        columns=columns,
        conflict_clause="ON CONFLICT (log_id) DO NOTHING",
    )


def load_production(df: pd.DataFrame) -> int:
    columns = [
        "date",
        "shift",
        "machine_id",
        "product_type",
        "operator_id",
        "planned_qty",
        "actual_qty",
        "rejected_qty",
        "good_qty",
        "efficiency_pct",
        "data_source",
    ]

    return bulk_insert_execute_values(
        table_name="raw.production_data",
        df=df,
        columns=columns,
        conflict_clause="ON CONFLICT (machine_id, date, shift) DO NOTHING",
    )


def load_schedule(df: pd.DataFrame) -> int:
    columns = [
        "task_id",
        "machine_id",
        "maintenance_type",
        "planned_date",
        "actual_date",
        "technician",
        "status",
        "delay_days",
        "notes",
        "data_source",
    ]

    return bulk_insert_execute_values(
        table_name="raw.maintenance_schedule",
        df=df,
        columns=columns,
        conflict_clause="ON CONFLICT (task_id) DO NOTHING",
    )


def load_optional_azure_tables(dataframes: dict[str, pd.DataFrame]) -> dict[str, int]:
    """
    Optional raw loading for Azure PM sample-style data.

    These files are not required for the SmartFactory synthetic KPI analytics,
    but they support the hybrid public + synthetic data strategy.
    """
    inserted: dict[str, int] = {}

    if "azure_telemetry" in dataframes:
        df = dataframes["azure_telemetry"]
        columns = [
            "datetime",
            "machineID",
            "volt",
            "rotate",
            "pressure",
            "vibration",
            "data_source",
            "source_file",
        ]
        inserted["raw.azure_telemetry"] = bulk_insert_execute_values(
            "raw.azure_telemetry",
            df,
            columns,
            "ON CONFLICT DO NOTHING",
        )

    if "azure_errors" in dataframes:
        df = dataframes["azure_errors"]
        columns = ["datetime", "machineID", "errorID", "data_source", "source_file"]
        inserted["raw.azure_errors"] = bulk_insert_execute_values(
            "raw.azure_errors",
            df,
            columns,
            "ON CONFLICT DO NOTHING",
        )

    if "azure_failures" in dataframes:
        df = dataframes["azure_failures"]
        columns = ["datetime", "machineID", "failure", "data_source", "source_file"]
        inserted["raw.azure_failures"] = bulk_insert_execute_values(
            "raw.azure_failures",
            df,
            columns,
            "ON CONFLICT DO NOTHING",
        )

    if "azure_maintenance" in dataframes:
        df = dataframes["azure_maintenance"]
        columns = ["datetime", "machineID", "comp", "data_source", "source_file"]
        inserted["raw.azure_maintenance"] = bulk_insert_execute_values(
            "raw.azure_maintenance",
            df,
            columns,
            "ON CONFLICT DO NOTHING",
        )

    if "azure_machines" in dataframes:
        df = dataframes["azure_machines"]
        columns = ["machineID", "model", "age", "data_source", "source_file"]
        inserted["raw.azure_machines"] = bulk_insert_execute_values(
            "raw.azure_machines",
            df,
            columns,
            "ON CONFLICT (machineID) DO NOTHING",
        )

    return inserted


def load_raw_tables(dataframes: dict[str, pd.DataFrame]) -> dict[str, int]:
    inserted_counts = {
        "raw.machine_sensor_data": load_sensors(dataframes["sensors"]),
        "raw.breakdown_logs": load_breakdown(dataframes["breakdown"]),
        "raw.production_data": load_production(dataframes["production"]),
        "raw.maintenance_schedule": load_schedule(dataframes["schedule"]),
    }

    inserted_counts.update(load_optional_azure_tables(dataframes))

    return inserted_counts


# ============================================================
# STEP 4 and STEP 5 — Compute analytics tables with SQLAlchemy
# ============================================================

def add_missing_analytics_columns(engine: Engine) -> None:
    """
    Adds columns required by the requested analytics logic if they do not exist yet.

    This keeps the ETL compatible with the earlier schema.sql while supporting:
    - machine_reliability.total_failures
    - machine_reliability.total_operating_hours
    - machine_reliability.availability_pct
    - machine_reliability.health_score
    """
    sql = """
    ALTER TABLE analytics.machine_reliability
        ADD COLUMN IF NOT EXISTS total_failures INTEGER,
        ADD COLUMN IF NOT EXISTS total_operating_hours NUMERIC(12, 2),
        ADD COLUMN IF NOT EXISTS availability_pct NUMERIC(6, 2),
        ADD COLUMN IF NOT EXISTS health_score NUMERIC(6, 2);

    ALTER TABLE analytics.machine_daily_kpi
        ADD COLUMN IF NOT EXISTS avg_temperature_c NUMERIC(10, 2),
        ADD COLUMN IF NOT EXISTS avg_vibration_mm_s NUMERIC(10, 3),
        ADD COLUMN IF NOT EXISTS avg_motor_current_a NUMERIC(10, 2),
        ADD COLUMN IF NOT EXISTS anomaly_count INTEGER DEFAULT 0;
    """

    with engine.begin() as connection:
        connection.execute(text(sql))

    LOGGER.info("Ensured required analytics columns exist")


def refresh_machine_daily_kpi(engine: Engine) -> int:
    sql = """
    TRUNCATE TABLE analytics.machine_daily_kpi RESTART IDENTITY;

    WITH production_daily AS (
        SELECT
            p.date AS kpi_date,
            p.machine_id,
            SUM(p.planned_qty) AS planned_qty,
            SUM(p.actual_qty) AS actual_qty,
            SUM(p.good_qty) AS good_qty,
            SUM(p.rejected_qty) AS rejected_qty,
            AVG(p.efficiency_pct) AS performance_pct
        FROM raw.production_data p
        GROUP BY p.date, p.machine_id
    ),
    sensor_daily AS (
        SELECT
            DATE(s.timestamp) AS kpi_date,
            s.machine_id,
            MAX(s.machine_type) AS machine_type,
            AVG(s.temperature_c) AS avg_temperature_c,
            AVG(s.vibration_mm_s) AS avg_vibration_mm_s,
            AVG(s.motor_current_a) AS avg_motor_current_a,
            SUM(CASE WHEN s.anomaly_flag THEN 1 ELSE 0 END) AS anomaly_count
        FROM raw.machine_sensor_data s
        GROUP BY DATE(s.timestamp), s.machine_id
    ),
    breakdown_daily AS (
        SELECT
            DATE(b.start_time) AS kpi_date,
            b.machine_id,
            SUM(b.downtime_hours) AS downtime_hours
        FROM raw.breakdown_logs b
        GROUP BY DATE(b.start_time), b.machine_id
    ),
    final_kpi AS (
        SELECT
            p.kpi_date,
            p.machine_id,
            s.machine_type,
            p.planned_qty,
            p.actual_qty,
            p.good_qty,
            p.rejected_qty,
            COALESCE(b.downtime_hours, 0) AS downtime_hours,
            GREATEST(0, LEAST(100, ((24.0 - COALESCE(b.downtime_hours, 0)) / 24.0) * 100)) AS availability_pct,
            GREATEST(0, LEAST(120, p.performance_pct)) AS performance_pct,
            CASE
                WHEN p.actual_qty > 0 THEN (p.good_qty::NUMERIC / p.actual_qty) * 100
                ELSE 0
            END AS quality_rate_pct,
            s.avg_temperature_c,
            s.avg_vibration_mm_s,
            s.avg_motor_current_a,
            COALESCE(s.anomaly_count, 0) AS anomaly_count
        FROM production_daily p
        LEFT JOIN sensor_daily s
            ON p.machine_id = s.machine_id
           AND p.kpi_date = s.kpi_date
        LEFT JOIN breakdown_daily b
            ON p.machine_id = b.machine_id
           AND p.kpi_date = b.kpi_date
    )
    INSERT INTO analytics.machine_daily_kpi (
        kpi_date,
        machine_id,
        machine_type,
        planned_qty,
        actual_qty,
        good_qty,
        rejected_qty,
        downtime_hours,
        availability_pct,
        performance_pct,
        quality_pct,
        oee_pct,
        avg_temperature_c,
        avg_vibration_mm_s,
        avg_motor_current_a,
        anomaly_count,
        created_at
    )
    SELECT
        kpi_date,
        machine_id,
        machine_type,
        planned_qty,
        actual_qty,
        good_qty,
        rejected_qty,
        downtime_hours,
        ROUND(availability_pct, 2),
        ROUND(performance_pct, 2),
        ROUND(quality_rate_pct, 2),
        ROUND((availability_pct * performance_pct * quality_rate_pct) / 10000, 2) AS oee_pct,
        ROUND(avg_temperature_c, 2),
        ROUND(avg_vibration_mm_s, 3),
        ROUND(avg_motor_current_a, 2),
        anomaly_count,
        NOW()
    FROM final_kpi;
    """

    count_sql = "SELECT COUNT(*) FROM analytics.machine_daily_kpi;"

    started_at = time.perf_counter()

    with engine.begin() as connection:
        connection.execute(text(sql))
        row_count = connection.execute(text(count_sql)).scalar_one()

    duration_seconds = time.perf_counter() - started_at

    LOGGER.info(
        "Analytics written table=analytics.machine_daily_kpi rows=%s duration_seconds=%.2f",
        row_count,
        duration_seconds,
    )

    return int(row_count)


def refresh_machine_reliability(engine: Engine) -> int:
    sql = """
    TRUNCATE TABLE analytics.machine_reliability RESTART IDENTITY;

    WITH machine_period AS (
        SELECT
            machine_id,
            MIN(date) AS period_start,
            MAX(date) AS period_end,
            COUNT(DISTINCT date) * 24.0 AS total_calendar_hours
        FROM raw.production_data
        GROUP BY machine_id
    ),
    failures AS (
        SELECT
            machine_id,
            COUNT(*) AS total_failures,
            SUM(downtime_hours) AS total_downtime_hours
        FROM raw.breakdown_logs
        GROUP BY machine_id
    ),
    maintenance AS (
        SELECT
            machine_id,
            SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS maintenance_completed_count,
            SUM(CASE WHEN status = 'Overdue' THEN 1 ELSE 0 END) AS maintenance_overdue_count,
            COUNT(*) AS total_maintenance_count
        FROM raw.maintenance_schedule
        GROUP BY machine_id
    ),
    reliability AS (
        SELECT
            mp.machine_id,
            mp.period_start,
            mp.period_end,
            COALESCE(f.total_failures, 0) AS total_failures,
            COALESCE(f.total_downtime_hours, 0) AS total_downtime_hours,
            GREATEST(0, mp.total_calendar_hours - COALESCE(f.total_downtime_hours, 0)) AS total_operating_hours,
            CASE
                WHEN COALESCE(f.total_failures, 0) > 0
                THEN GREATEST(0, mp.total_calendar_hours - COALESCE(f.total_downtime_hours, 0)) / f.total_failures
                ELSE NULL
            END AS mtbf_hours,
            CASE
                WHEN COALESCE(f.total_failures, 0) > 0
                THEN COALESCE(f.total_downtime_hours, 0) / f.total_failures
                ELSE NULL
            END AS mttr_hours,
            CASE
                WHEN mp.total_calendar_hours > 0
                THEN GREATEST(0, mp.total_calendar_hours - COALESCE(f.total_downtime_hours, 0)) / mp.total_calendar_hours * 100
                ELSE 0
            END AS availability_pct,
            CASE
                WHEN mp.total_calendar_hours > 0
                THEN COALESCE(f.total_downtime_hours, 0) / mp.total_calendar_hours
                ELSE 0
            END AS downtime_rate,
            COALESCE(m.maintenance_completed_count, 0) AS maintenance_completed_count,
            COALESCE(m.maintenance_overdue_count, 0) AS maintenance_overdue_count,
            CASE
                WHEN COALESCE(m.total_maintenance_count, 0) > 0
                THEN COALESCE(m.maintenance_completed_count, 0)::NUMERIC / m.total_maintenance_count * 100
                ELSE NULL
            END AS maintenance_compliance_pct
        FROM machine_period mp
        LEFT JOIN failures f
            ON mp.machine_id = f.machine_id
        LEFT JOIN maintenance m
            ON mp.machine_id = m.machine_id
    )
    INSERT INTO analytics.machine_reliability (
        machine_id,
        period_start,
        period_end,
        failure_count,
        total_failures,
        total_downtime_hours,
        total_operating_hours,
        mtbf_hours,
        mttr_hours,
        availability_pct,
        health_score,
        maintenance_completed_count,
        maintenance_overdue_count,
        maintenance_compliance_pct,
        created_at
    )
    SELECT
        machine_id,
        period_start,
        period_end,
        total_failures AS failure_count,
        total_failures,
        ROUND(total_downtime_hours, 2),
        ROUND(total_operating_hours, 2),
        ROUND(mtbf_hours, 2),
        ROUND(mttr_hours, 2),
        ROUND(availability_pct, 2),
        ROUND(
            GREATEST(
                0,
                LEAST(
                    100,
                    100 - (total_failures * 1.5) - (downtime_rate * 50)
                )
            ),
            2
        ) AS health_score,
        maintenance_completed_count,
        maintenance_overdue_count,
        ROUND(maintenance_compliance_pct, 2),
        NOW()
    FROM reliability;
    """

    count_sql = "SELECT COUNT(*) FROM analytics.machine_reliability;"

    started_at = time.perf_counter()

    with engine.begin() as connection:
        connection.execute(text(sql))
        row_count = connection.execute(text(count_sql)).scalar_one()

    duration_seconds = time.perf_counter() - started_at

    LOGGER.info(
        "Analytics written table=analytics.machine_reliability rows=%s duration_seconds=%.2f",
        row_count,
        duration_seconds,
    )

    return int(row_count)


def refresh_downtime_pareto(engine: Engine) -> int:
    sql = """
    TRUNCATE TABLE analytics.downtime_pareto RESTART IDENTITY;

    WITH bounds AS (
        SELECT
            MIN(DATE(start_time)) AS period_start,
            MAX(DATE(start_time)) AS period_end
        FROM raw.breakdown_logs
    ),
    grouped AS (
        SELECT
            b.failure_type,
            COUNT(*) AS failure_count,
            SUM(b.downtime_hours) AS downtime_hours
        FROM raw.breakdown_logs b
        GROUP BY b.failure_type
    ),
    totals AS (
        SELECT SUM(downtime_hours) AS total_downtime_hours
        FROM grouped
    ),
    ranked AS (
        SELECT
            g.failure_type,
            g.failure_count,
            g.downtime_hours,
            CASE
                WHEN t.total_downtime_hours > 0
                THEN g.downtime_hours / t.total_downtime_hours * 100
                ELSE 0
            END AS downtime_pct,
            SUM(g.downtime_hours) OVER (
                ORDER BY g.downtime_hours DESC
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS cumulative_downtime_hours,
            t.total_downtime_hours,
            ROW_NUMBER() OVER (ORDER BY g.downtime_hours DESC) AS pareto_rank
        FROM grouped g
        CROSS JOIN totals t
    )
    INSERT INTO analytics.downtime_pareto (
        period_start,
        period_end,
        machine_id,
        failure_type,
        failure_count,
        downtime_hours,
        downtime_pct,
        cumulative_downtime_pct,
        pareto_rank,
        created_at
    )
    SELECT
        bounds.period_start,
        bounds.period_end,
        NULL AS machine_id,
        ranked.failure_type,
        ranked.failure_count,
        ROUND(ranked.downtime_hours, 2),
        ROUND(ranked.downtime_pct, 2),
        ROUND(
            CASE
                WHEN ranked.total_downtime_hours > 0
                THEN ranked.cumulative_downtime_hours / ranked.total_downtime_hours * 100
                ELSE 0
            END,
            2
        ) AS cumulative_downtime_pct,
        ranked.pareto_rank,
        NOW()
    FROM ranked
    CROSS JOIN bounds
    ORDER BY ranked.pareto_rank;
    """

    count_sql = "SELECT COUNT(*) FROM analytics.downtime_pareto;"

    started_at = time.perf_counter()

    with engine.begin() as connection:
        connection.execute(text(sql))
        row_count = connection.execute(text(count_sql)).scalar_one()

    duration_seconds = time.perf_counter() - started_at

    LOGGER.info(
        "Analytics written table=analytics.downtime_pareto rows=%s duration_seconds=%.2f",
        row_count,
        duration_seconds,
    )

    return int(row_count)


def refresh_analytics_tables(engine: Engine) -> dict[str, int]:
    add_missing_analytics_columns(engine)

    row_counts = {
        "analytics.machine_daily_kpi": refresh_machine_daily_kpi(engine),
        "analytics.machine_reliability": refresh_machine_reliability(engine),
        "analytics.downtime_pareto": refresh_downtime_pareto(engine),
    }

    return row_counts


# ============================================================
# Main pipeline entry point
# ============================================================

def run_etl(raw_dir: Path = Path("data/raw")) -> dict[str, dict[str, int]]:
    """
    Main callable ETL function.

    This function can be imported and called from Airflow.
    """
    pipeline_started_at = time.perf_counter()

    LOGGER.info("Starting SmartFactory ETL pipeline raw_dir=%s", raw_dir)

    dataframes = read_raw_csvs(raw_dir)
    validated_dataframes = validate_dataframes(dataframes)

    raw_insert_counts = load_raw_tables(validated_dataframes)

    engine = get_engine()
    analytics_row_counts = refresh_analytics_tables(engine)

    duration_seconds = time.perf_counter() - pipeline_started_at

    LOGGER.info(
        "ETL pipeline completed duration_seconds=%.2f raw_tables=%s analytics_tables=%s",
        duration_seconds,
        len(raw_insert_counts),
        len(analytics_row_counts),
    )

    return {
        "raw_insert_counts": raw_insert_counts,
        "analytics_row_counts": analytics_row_counts,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SmartFactory ETL pipeline.")
    parser.add_argument(
        "--raw-dir",
        default="data/raw",
        help="Directory containing raw CSV files.",
    )
    return parser.parse_args()


def main() -> None:
    configure_logging()
    args = parse_args()

    results = run_etl(raw_dir=Path(args.raw_dir))

    LOGGER.info("Raw insert counts: %s", results["raw_insert_counts"])
    LOGGER.info("Analytics row counts: %s", results["analytics_row_counts"])


if __name__ == "__main__":
    main()