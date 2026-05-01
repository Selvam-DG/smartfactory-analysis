"""
Hybrid data generator for SmartFactory Reliability Analytics.

This script supports two data sources:

1. Optional Azure Predictive Maintenance sample-style files:
   - PdM_telemetry.csv
   - PdM_errors.csv
   - PdM_failures.csv
   - PdM_maint.csv
   - PdM_machines.csv

2. Synthetic tyre manufacturing data inspired by:
   - Tyre Building Machines, TBM
   - Bead Apexing machines, BA
   - Curing/Vulcanizing machines, CV
   - Mixing machines, MX
   - Quality Control machines, QC

The final project-ready raw CSV files are written to data/raw/:

- machine_sensor_data.csv
- breakdown_logs.csv
- production_data.csv
- maintenance_schedule.csv
- azure_telemetry.csv
- azure_errors.csv
- azure_failures.csv
- azure_maintenance.csv
- azure_machines.csv
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class MachineProfile:
    machine_id: str
    machine_type: str
    age_years: int
    base_temperature_c: float
    base_vibration_mm_s: float
    base_motor_current_a: float
    base_pressure_bar: float
    base_speed_rpm: float
    base_shift_output: int


MACHINE_PROFILES: list[MachineProfile] = [
    MachineProfile("TBM-01", "Tyre Building Machine", 10, 58.0, 4.2, 42.0, 6.8, 95.0, 420),
    MachineProfile("TBM-02", "Tyre Building Machine", 6, 55.0, 3.4, 39.0, 6.5, 100.0, 450),
    MachineProfile("TBM-03", "Tyre Building Machine", 2, 52.0, 2.6, 36.0, 6.3, 105.0, 480),
    MachineProfile("BA-01", "Bead Apexing", 9, 62.0, 3.8, 34.0, 5.8, 85.0, 650),
    MachineProfile("BA-02", "Bead Apexing", 3, 56.0, 2.7, 30.0, 5.5, 90.0, 700),
    MachineProfile("CV-01", "Curing Press", 8, 138.0, 2.9, 48.0, 10.5, 35.0, 260),
    MachineProfile("CV-02", "Curing Press", 4, 134.0, 2.4, 45.0, 10.2, 38.0, 280),
    MachineProfile("MX-01", "Rubber Mixing", 10, 76.0, 5.0, 65.0, 7.4, 60.0, 180),
    MachineProfile("MX-02", "Rubber Mixing", 5, 72.0, 3.9, 59.0, 7.1, 65.0, 200),
    MachineProfile("QC-01", "Quality Control", 1, 36.0, 1.2, 12.0, 2.0, 25.0, 900),
]


FAILURE_TYPES = [
    "Bearing Failure",
    "Belt Breakage",
    "Motor Overload",
    "Hydraulic Leak",
    "PLC Fault",
    "Overheating",
    "Mechanical Jam",
]

ROOT_CAUSES = {
    "Bearing Failure": ["Bearing wear", "Lubrication missed", "Contamination in bearing housing"],
    "Belt Breakage": ["Belt tension issue", "Pulley misalignment", "Aged belt material"],
    "Motor Overload": ["High motor current", "Machine jam", "Cooling fan issue"],
    "Hydraulic Leak": ["Hydraulic hose crack", "Seal wear", "Loose hydraulic fitting"],
    "PLC Fault": ["PLC IO module fault", "Communication loss", "Sensor feedback mismatch"],
    "Overheating": ["Cooling fan failure", "Blocked ventilation", "High process temperature"],
    "Mechanical Jam": [
        "Material feed misalignment",
        "Worn guide roller",
        "Foreign material obstruction",
    ],
}

ACTION_TAKEN = {
    "Bearing Failure": ["Replaced bearing", "Lubricated bearing assembly"],
    "Belt Breakage": ["Replaced drive belt", "Adjusted belt tension"],
    "Motor Overload": ["Reset overload relay", "Removed jam and checked motor"],
    "Hydraulic Leak": ["Replaced hydraulic hose", "Replaced seal kit"],
    "PLC Fault": ["Replaced IO module", "Restored PLC communication"],
    "Overheating": ["Cleaned cooling path", "Replaced cooling fan"],
    "Mechanical Jam": ["Cleared jam", "Adjusted feed alignment"],
}

TECHNICIANS = [
    "TECH-MECH-01",
    "TECH-MECH-02",
    "TECH-ELEC-01",
    "TECH-ELEC-02",
    "TECH-AUTO-01",
    "TECH-HYD-01",
]

PRODUCT_TYPES = [
    "PCR 185/65R15",
    "TBR 295/80R22.5",
    "2W 100/90-17",
]


AZURE_FILE_MAP = {
    "PdM_telemetry.csv": "azure_telemetry.csv",
    "PdM_errors.csv": "azure_errors.csv",
    "PdM_failures.csv": "azure_failures.csv",
    "PdM_maint.csv": "azure_maintenance.csv",
    "PdM_machines.csv": "azure_machines.csv",
}


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def get_shift(timestamp: pd.Timestamp) -> str:
    if 6 <= timestamp.hour < 14:
        return "A"
    if 14 <= timestamp.hour < 22:
        return "B"
    return "C"


def machine_spike_probability(age_years: int) -> float:
    """
    Newer machine: around 1%
    10-year-old machine: around 5%
    """
    return min(0.05, 0.01 + (age_years / 10.0) * 0.04)


def machine_noise_multiplier(age_years: int) -> float:
    return 1.0 + (age_years / 10.0)


def copy_optional_azure_pm_files(
    azure_input_dir: Path,
    output_dir: Path,
) -> dict[str, int]:
    """
    Copies optional Azure Predictive Maintenance sample-style files into data/raw
    using normalized file names.

    If a file is missing, the script logs a warning and continues.
    """
    row_counts: dict[str, int] = {}

    if not azure_input_dir.exists():
        LOGGER.warning(
            "Azure input directory does not exist: %s. Continuing with synthetic data only.",
            azure_input_dir,
        )
        return row_counts

    for source_name, target_name in AZURE_FILE_MAP.items():
        source_path = azure_input_dir / source_name
        target_path = output_dir / target_name

        if not source_path.exists():
            LOGGER.warning("Optional Azure PM file missing: %s", source_path)
            continue

        df = pd.read_csv(source_path)

        # Add source metadata for traceability.
        df["data_source"] = "azure_predictive_maintenance_sample"
        df["source_file"] = source_name

        df.to_csv(target_path, index=False)
        row_counts[target_name] = len(df)

        LOGGER.info("Copied Azure PM file %s to %s rows=%s", source_path, target_path, len(df))

    return row_counts


def generate_machine_sensor_data(
    start_date: str,
    end_date: str,
    output_dir: Path,
    seed: int,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    timestamps = pd.date_range(
        start=start_date,
        end=end_date,
        freq="h",
        inclusive="left",
    )

    rows: list[dict[str, object]] = []

    for machine in MACHINE_PROFILES:
        noise_multiplier = machine_noise_multiplier(machine.age_years)
        spike_probability = machine_spike_probability(machine.age_years)

        for timestamp in timestamps:
            shift = get_shift(timestamp)
            is_spike = rng.random() < spike_probability

            shift_factor = {"A": 1.00, "B": 1.04, "C": 0.96}[shift]

            temperature = rng.normal(
                machine.base_temperature_c * shift_factor,
                1.6 * noise_multiplier,
            )
            vibration = rng.normal(
                machine.base_vibration_mm_s,
                0.35 * noise_multiplier,
            )
            motor_current = rng.normal(
                machine.base_motor_current_a * shift_factor,
                2.0 * noise_multiplier,
            )
            pressure = rng.normal(
                machine.base_pressure_bar,
                0.18 * noise_multiplier,
            )
            speed = rng.normal(
                machine.base_speed_rpm,
                3.5 * noise_multiplier,
            )

            if is_spike:
                temperature += rng.uniform(6.0, 18.0)
                vibration += rng.uniform(1.5, 5.0)
                motor_current += rng.uniform(6.0, 20.0)
                pressure += rng.uniform(-1.0, 1.5)
                speed *= rng.uniform(0.75, 1.12)

            hourly_output_base = machine.base_shift_output / 8
            production_count = max(
                0,
                int(rng.normal(hourly_output_base * shift_factor, hourly_output_base * 0.08)),
            )

            if is_spike:
                production_count = int(production_count * rng.uniform(0.55, 0.90))

            rows.append(
                {
                    "timestamp": timestamp,
                    "machine_id": machine.machine_id,
                    "machine_type": machine.machine_type,
                    "shift": shift,
                    "temperature_c": round(max(0, temperature), 2),
                    "vibration_mm_s": round(max(0, vibration), 3),
                    "motor_current_a": round(max(0, motor_current), 2),
                    "pressure_bar": round(max(0, pressure), 2),
                    "speed_rpm": round(max(0, speed), 2),
                    "production_count": production_count,
                    "anomaly_flag": bool(is_spike),
                    "data_source": "synthetic_tyre_factory",
                }
            )

    df = pd.DataFrame(rows)
    output_path = output_dir / "machine_sensor_data.csv"
    df.to_csv(output_path, index=False)

    LOGGER.info("Wrote synthetic sensor data rows=%s file=%s", len(df), output_path)
    return df


def weighted_failure_type(machine: MachineProfile, rng: np.random.Generator) -> str:
    if machine.machine_id.startswith("TBM"):
        probabilities = [0.22, 0.20, 0.14, 0.10, 0.12, 0.10, 0.12]
    elif machine.machine_id.startswith("BA"):
        probabilities = [0.18, 0.18, 0.12, 0.16, 0.12, 0.10, 0.14]
    elif machine.machine_id.startswith("CV"):
        probabilities = [0.14, 0.08, 0.18, 0.16, 0.10, 0.25, 0.09]
    elif machine.machine_id.startswith("MX"):
        probabilities = [0.24, 0.10, 0.22, 0.12, 0.08, 0.12, 0.12]
    else:
        probabilities = [0.08, 0.06, 0.08, 0.04, 0.34, 0.10, 0.30]

    return str(rng.choice(FAILURE_TYPES, p=probabilities))


def generate_breakdown_logs(
    start_date: str,
    end_date: str,
    output_dir: Path,
    seed: int,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 1)

    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    total_days = max(1, (end - start).days)

    rows: list[dict[str, object]] = []
    log_counter = 1

    for machine in MACHINE_PROFILES:
        monthly_base_rate = 0.8 + (machine.age_years * 0.22)

        if machine.machine_id.startswith(("TBM", "MX")):
            monthly_base_rate *= 1.15

        expected_failures = monthly_base_rate * (total_days / 30.0)
        failure_count = int(rng.poisson(expected_failures))

        for _ in range(failure_count):
            failure_type = weighted_failure_type(machine, rng)

            start_offset_hours = int(rng.integers(0, total_days * 24))
            start_time = start + pd.Timedelta(hours=start_offset_hours)

            downtime_hours = float(rng.exponential(scale=4.5))
            downtime_hours = max(0.25, min(downtime_hours, 36.0))

            end_time = start_time + pd.Timedelta(hours=downtime_hours)

            if end_time > end:
                end_time = end
                downtime_hours = max(0.25, (end_time - start_time).total_seconds() / 3600)

            severity = str(
                rng.choice(
                    ["Low", "Medium", "High", "Critical"],
                    p=[0.20, 0.45, 0.27, 0.08],
                )
            )

            base_cost = {
                "Bearing Failure": 450,
                "Belt Breakage": 180,
                "Motor Overload": 520,
                "Hydraulic Leak": 300,
                "PLC Fault": 650,
                "Overheating": 250,
                "Mechanical Jam": 120,
            }[failure_type]

            severity_multiplier = {
                "Low": 0.55,
                "Medium": 1.0,
                "High": 1.6,
                "Critical": 2.4,
            }[severity]

            spare_cost = max(
                0,
                rng.normal(base_cost * severity_multiplier, base_cost * 0.18),
            )

            rows.append(
                {
                    "log_id": f"BD-{log_counter:06d}",
                    "machine_id": machine.machine_id,
                    "failure_type": failure_type,
                    "start_time": start_time,
                    "end_time": end_time,
                    "downtime_hours": round(downtime_hours, 2),
                    "shift": get_shift(start_time),
                    "root_cause": str(rng.choice(ROOT_CAUSES[failure_type])),
                    "action_taken": str(rng.choice(ACTION_TAKEN[failure_type])),
                    "technician": str(rng.choice(TECHNICIANS)),
                    "severity": severity,
                    "spare_part_cost_eur": round(spare_cost, 2),
                    "data_source": "synthetic_tyre_factory",
                }
            )

            log_counter += 1

    df = pd.DataFrame(rows).sort_values("start_time").reset_index(drop=True)
    output_path = output_dir / "breakdown_logs.csv"
    df.to_csv(output_path, index=False)

    LOGGER.info("Wrote synthetic breakdown data rows=%s file=%s", len(df), output_path)
    return df


def product_mix_for_machine(machine_id: str, rng: np.random.Generator) -> str:
    if machine_id.startswith(("TBM", "CV")):
        return str(rng.choice(PRODUCT_TYPES, p=[0.50, 0.30, 0.20]))
    if machine_id.startswith("BA"):
        return str(rng.choice(PRODUCT_TYPES, p=[0.45, 0.35, 0.20]))
    if machine_id.startswith("MX"):
        return str(rng.choice(PRODUCT_TYPES, p=[0.40, 0.40, 0.20]))

    return str(rng.choice(PRODUCT_TYPES, p=[0.45, 0.25, 0.30]))


def generate_production_data(
    start_date: str,
    end_date: str,
    breakdowns: pd.DataFrame,
    output_dir: Path,
    seed: int,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 2)

    dates = pd.date_range(
        start=start_date,
        end=end_date,
        freq="D",
        inclusive="left",
    )

    breakdowns = breakdowns.copy()
    if not breakdowns.empty:
        breakdowns["breakdown_date"] = pd.to_datetime(breakdowns["start_time"]).dt.date

    rows: list[dict[str, object]] = []

    for date_value in dates:
        production_date = date_value.date()

        for machine in MACHINE_PROFILES:
            for shift in ["A", "B", "C"]:
                planned_qty = max(
                    1,
                    int(rng.normal(machine.base_shift_output, machine.base_shift_output * 0.05)),
                )

                downtime_penalty = 0.0
                if not breakdowns.empty:
                    mask = (
                        (breakdowns["machine_id"] == machine.machine_id)
                        & (breakdowns["breakdown_date"] == production_date)
                        & (breakdowns["shift"] == shift)
                    )
                    downtime_penalty = float(breakdowns.loc[mask, "downtime_hours"].sum())

                age_loss = machine.age_years * rng.uniform(0.003, 0.008)
                shift_loss = {"A": 0.03, "B": 0.05, "C": 0.08}[shift]
                downtime_loss = min(0.65, downtime_penalty / 8.0)

                efficiency = 1.0 - age_loss - shift_loss - downtime_loss
                efficiency += rng.normal(0.0, 0.035)
                efficiency = float(np.clip(efficiency, 0.35, 1.08))

                actual_qty = max(0, int(planned_qty * efficiency))

                reject_rate = 0.015 + machine.age_years * 0.002 + downtime_loss * 0.04
                rejected_qty = int(
                    np.clip(
                        rng.binomial(max(actual_qty, 1), min(reject_rate, 0.18)),
                        0,
                        actual_qty,
                    )
                )
                good_qty = actual_qty - rejected_qty

                rows.append(
                    {
                        "date": production_date,
                        "shift": shift,
                        "machine_id": machine.machine_id,
                        "product_type": product_mix_for_machine(machine.machine_id, rng),
                        "operator_id": f"OP-{int(rng.integers(1, 36)):03d}",
                        "planned_qty": planned_qty,
                        "actual_qty": actual_qty,
                        "rejected_qty": rejected_qty,
                        "good_qty": good_qty,
                        "efficiency_pct": round((actual_qty / planned_qty) * 100, 2),
                        "data_source": "synthetic_tyre_factory",
                    }
                )

    df = pd.DataFrame(rows)
    output_path = output_dir / "production_data.csv"
    df.to_csv(output_path, index=False)

    LOGGER.info("Wrote synthetic production data rows=%s file=%s", len(df), output_path)
    return df


def generate_maintenance_schedule(
    start_date: str,
    end_date: str,
    output_dir: Path,
    seed: int,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 3)

    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)

    rows: list[dict[str, object]] = []
    task_counter = 1

    for machine in MACHINE_PROFILES:
        for maintenance_type, interval_days in [
            ("Preventive Maintenance", 30),
            ("Overhaul", 180),
        ]:
            planned_date = start

            while planned_date < end:
                delay_days = int(max(0, rng.poisson(1.2 + machine.age_years * 0.12)))

                status = str(
                    rng.choice(
                        ["Completed", "Overdue", "Planned"],
                        p=[0.85, 0.10, 0.05],
                    )
                )

                actual_date = None
                if status == "Completed":
                    actual_date = planned_date + pd.Timedelta(days=delay_days)

                    if actual_date >= end:
                        status = "Overdue"
                        actual_date = None

                notes = (
                    "Routine lubrication, inspection, and safety checks"
                    if maintenance_type == "Preventive Maintenance"
                    else "Major inspection, alignment check, and component overhaul"
                )

                rows.append(
                    {
                        "task_id": f"PM-{task_counter:06d}",
                        "machine_id": machine.machine_id,
                        "maintenance_type": maintenance_type,
                        "planned_date": planned_date.date(),
                        "actual_date": actual_date.date() if actual_date is not None else "",
                        "technician": str(rng.choice(TECHNICIANS)),
                        "status": status,
                        "delay_days": delay_days if status == "Completed" else "",
                        "notes": notes,
                        "data_source": "synthetic_tyre_factory",
                    }
                )

                task_counter += 1
                planned_date += pd.Timedelta(days=interval_days)

    df = pd.DataFrame(rows)
    output_path = output_dir / "maintenance_schedule.csv"
    df.to_csv(output_path, index=False)

    LOGGER.info("Wrote synthetic maintenance data rows=%s file=%s", len(df), output_path)
    return df


def generate_all_data(
    start_date: str,
    end_date: str,
    azure_input_dir: Path,
    output_dir: Path,
    seed: int,
) -> dict[str, int]:
    output_dir.mkdir(parents=True, exist_ok=True)

    LOGGER.info("Generating hybrid SmartFactory dataset")
    LOGGER.info("Synthetic date range: %s to %s", start_date, end_date)
    LOGGER.info("Azure input directory: %s", azure_input_dir)
    LOGGER.info("Output directory: %s", output_dir)

    row_counts: dict[str, int] = {}

    azure_counts = copy_optional_azure_pm_files(
        azure_input_dir=azure_input_dir,
        output_dir=output_dir,
    )
    row_counts.update(azure_counts)

    sensor_df = generate_machine_sensor_data(
        start_date=start_date,
        end_date=end_date,
        output_dir=output_dir,
        seed=seed,
    )

    breakdown_df = generate_breakdown_logs(
        start_date=start_date,
        end_date=end_date,
        output_dir=output_dir,
        seed=seed,
    )

    production_df = generate_production_data(
        start_date=start_date,
        end_date=end_date,
        breakdowns=breakdown_df,
        output_dir=output_dir,
        seed=seed,
    )

    maintenance_df = generate_maintenance_schedule(
        start_date=start_date,
        end_date=end_date,
        output_dir=output_dir,
        seed=seed,
    )

    row_counts.update(
        {
            "machine_sensor_data.csv": len(sensor_df),
            "breakdown_logs.csv": len(breakdown_df),
            "production_data.csv": len(production_df),
            "maintenance_schedule.csv": len(maintenance_df),
        }
    )

    return row_counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate hybrid Azure PM + synthetic SmartFactory raw data."
    )

    parser.add_argument("--start-date", default="2024-01-01")
    parser.add_argument("--end-date", default="2026-01-01")
    parser.add_argument("--azure-input-dir", default="data/external/azure_pm")
    parser.add_argument("--output-dir", default="data/raw")
    parser.add_argument("--seed", type=int, default=42)

    return parser.parse_args()


def main() -> None:
    configure_logging()
    args = parse_args()

    row_counts = generate_all_data(
        start_date=args.start_date,
        end_date=args.end_date,
        azure_input_dir=Path(args.azure_input_dir),
        output_dir=Path(args.output_dir),
        seed=args.seed,
    )

    print("\nGenerated / copied CSV row counts:")
    for file_name, row_count in row_counts.items():
        print(f"- {file_name}: {row_count:,}")


if __name__ == "__main__":
    main()
