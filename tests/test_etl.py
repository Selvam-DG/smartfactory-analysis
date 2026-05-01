# tests/test_etl.py
"""
Unit tests for the SmartFactory ETL validation and idempotency logic.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text

from src.transformation.etl_pipeline import (
    validate_breakdown,
    validate_production,
    validate_sensors,
)


def _insert_sensors_sqlite(engine, sensor_df: pd.DataFrame) -> int:
    """
    SQLite-only helper for testing idempotency behavior.

    The production ETL uses psycopg2 execute_values with ON CONFLICT DO NOTHING.
    This test helper uses INSERT OR IGNORE to validate the same database-level
    idempotency concept against the unique key: (machine_id, timestamp).
    """
    insert_sql = text(
        """
        INSERT OR IGNORE INTO raw.machine_sensor_data (
            timestamp,
            machine_id,
            machine_type,
            shift,
            temperature_c,
            vibration_mm_s,
            motor_current_a,
            pressure_bar,
            speed_rpm,
            production_count,
            anomaly_flag,
            data_source
        )
        VALUES (
            :timestamp,
            :machine_id,
            :machine_type,
            :shift,
            :temperature_c,
            :vibration_mm_s,
            :motor_current_a,
            :pressure_bar,
            :speed_rpm,
            :production_count,
            :anomaly_flag,
            :data_source
        );
        """
    )

    records = sensor_df.copy()
    records["timestamp"] = pd.to_datetime(records["timestamp"]).astype(str)
    records["anomaly_flag"] = records["anomaly_flag"].astype(int)

    with engine.begin() as connection:
        before_count = connection.execute(
            text("SELECT COUNT(*) FROM raw.machine_sensor_data;")
        ).scalar_one()

        connection.execute(insert_sql, records.to_dict(orient="records"))

        after_count = connection.execute(
            text("SELECT COUNT(*) FROM raw.machine_sensor_data;")
        ).scalar_one()

    return int(after_count - before_count)


def test_validate_sensors_removes_high_temp(sample_sensor_df: pd.DataFrame) -> None:
    bad_row = sample_sensor_df.iloc[[0]].copy()
    bad_row["timestamp"] = pd.Timestamp("2024-01-02 00:00:00", tz="UTC")
    bad_row["temperature_c"] = 200

    input_df = pd.concat([sample_sensor_df, bad_row], ignore_index=True)

    result_df = validate_sensors(input_df)

    assert len(result_df) == len(sample_sensor_df)
    assert result_df["temperature_c"].max() <= 150


def test_validate_sensors_removes_null_machine_id(sample_sensor_df: pd.DataFrame) -> None:
    bad_row = sample_sensor_df.iloc[[0]].copy()
    bad_row["timestamp"] = pd.Timestamp("2024-01-02 00:00:00", tz="UTC")
    bad_row["machine_id"] = None

    input_df = pd.concat([sample_sensor_df, bad_row], ignore_index=True)

    result_df = validate_sensors(input_df)

    assert len(result_df) == len(sample_sensor_df)
    assert result_df["machine_id"].isna().sum() == 0


def test_validate_sensors_removes_duplicates(sample_sensor_df: pd.DataFrame) -> None:
    duplicate_row = sample_sensor_df.iloc[[0]].copy()

    input_df = pd.concat([sample_sensor_df, duplicate_row], ignore_index=True)

    result_df = validate_sensors(input_df)

    duplicate_count = result_df.duplicated(subset=["machine_id", "timestamp"]).sum()

    assert len(result_df) == len(sample_sensor_df)
    assert duplicate_count == 0


def test_validate_breakdown_removes_bad_downtime(sample_breakdown_df: pd.DataFrame) -> None:
    bad_row = sample_breakdown_df.iloc[[0]].copy()
    bad_row["log_id"] = "BD-999999"
    bad_row["downtime_hours"] = 1000

    input_df = pd.concat([sample_breakdown_df, bad_row], ignore_index=True)

    result_df = validate_breakdown(input_df)

    assert len(result_df) == len(sample_breakdown_df)
    assert result_df["downtime_hours"].max() <= 720


def test_etl_is_idempotent(test_engine, sample_sensor_df: pd.DataFrame) -> None:
    valid_df = validate_sensors(sample_sensor_df)

    first_insert_count = _insert_sensors_sqlite(test_engine, valid_df)
    second_insert_count = _insert_sensors_sqlite(test_engine, valid_df)

    with test_engine.connect() as connection:
        final_count = connection.execute(
            text("SELECT COUNT(*) FROM raw.machine_sensor_data;")
        ).scalar_one()

    assert first_insert_count == len(valid_df)
    assert second_insert_count == 0
    assert final_count == len(valid_df)


def test_production_good_qty_recalculated() -> None:
    input_df = pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-01", "2024-01-02"],
            "shift": ["A", "B", "C"],
            "machine_id": ["TBM-01", "BA-01", "MX-01"],
            "product_type": ["PCR 185/65R15", "TBR 295/80R22.5", "2W 100/90-17"],
            "operator_id": ["OP-001", "OP-002", "OP-003"],
            "planned_qty": [100, 200, 300],
            "actual_qty": [90, 180, -10],
            "rejected_qty": [5, 20, -2],
            "good_qty": [999, 999, 999],
            "efficiency_pct": [0, 0, 0],
            "data_source": ["synthetic_tyre_factory"] * 3,
        }
    )

    result_df = validate_production(input_df)

    assert (result_df["actual_qty"] >= 0).all()
    assert (result_df["rejected_qty"] >= 0).all()
    assert (result_df["good_qty"] == result_df["actual_qty"] - result_df["rejected_qty"]).all()
