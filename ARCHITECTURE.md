# SmartFactory Reliability Analytics — Architecture Document

**Author:** Selvam DG  
**Project Type:** project for Data Engineering / Python Developer 
**Domain:** Industrial reliability analytics, predictive maintenance, manufacturing data pipelines  
**Tech Stack:** Python 3.11, PostgreSQL 15, SQLAlchemy, pandas, Streamlit, Plotly, Scikit-learn, Docker Compose, GitHub Actions, pytest, ruff, black  
**Data Strategy:** Privacy-safe hybrid dataset using public Azure Predictive Maintenance sample data patterns plus synthetic industrial production, breakdown, and maintenance data.

---

## 1. System Overview

SmartFactory Reliability Analytics is an end-to-end industrial data pipeline and analytics platform that simulates a realistic smart factory environment without exposing confidential company data. The system ingests machine sensor readings, breakdown logs, production records, and preventive maintenance schedules from a hybrid data setup based on public predictive maintenance sample structures and synthetic factory data. It stores raw data in PostgreSQL, transforms it into analytics-ready tables, calculates manufacturing and reliability KPIs such as OEE, MTBF, and MTTR, detects abnormal sensor behavior, predicts downtime risk, and visualizes the results in a five-page Streamlit dashboard.

The project is designed to demonstrate practical skills in industrial data engineering, Python development, SQL modeling, analytics engineering, machine learning, Docker-based local deployment, CI quality checks, and portfolio-grade documentation.

---

### 1.1 User-Facing Features

| Feature | Description |
|---|---|
| Executive Overview Dashboard | High-level view of factory performance, OEE, downtime, production volume, and downtime risk. |
| Machine KPI Dashboard | Machine-level daily availability, performance, quality, OEE, downtime minutes, and production count. |
| Reliability Dashboard | MTBF, MTTR, breakdown frequency, maintenance compliance, and reliability trends by machine. |
| Downtime Pareto Dashboard | Pareto analysis of downtime causes, departments, machines, and recurring failure categories. |
| Predictive Downtime Dashboard | Machine downtime risk score, predicted risk class, anomaly flags, and recommended attention list. |
| Interactive Filters | Filter by date range, machine, line, shift, failure category, and risk level. |
| Trend Charts | Time-series charts for OEE, downtime, MTBF, MTTR, sensor values, and predicted risk. |
| Exportable Insights | Dashboard tables can be exported as CSV from Streamlit for recruiter/demo use. |
| Portfolio Demo Mode | Runs locally with generated data and does not require access to any confidential industrial system. |

---

### 1.2 Technical Capabilities

| Capability | Description |
|---|---|
| Synthetic Data Generation | Generates realistic factory data for sensors, breakdowns, production, and maintenance schedules. |
| Public Sample Data Integration | Supports Azure Predictive Maintenance style sample datasets as seed/reference data. |
| PostgreSQL Raw Layer | Stores immutable ingested records in `raw` schema. |
| SQL Analytics Layer | Builds clean KPI and reliability tables in `analytics` schema. |
| Idempotent ETL | ETL jobs can be safely re-run without duplicating records. |
| KPI Computation | Calculates OEE, availability, performance, quality, MTBF, MTTR, downtime Pareto, and prediction outputs. |
| Machine Learning Pipeline | Trains a Scikit-learn model for downtime risk prediction using historical sensor and maintenance features. |
| Anomaly Detection | Identifies abnormal sensor behavior using statistical thresholds or ML-based logic. |
| Streamlit Dashboard | Presents a five-page interactive web dashboard using Plotly visualizations. |
| Docker Compose Deployment | Runs PostgreSQL, ETL, optional Airflow, and Streamlit locally using containers. |
| CI Pipeline | GitHub Actions runs formatting, linting, tests, and basic import checks. |
| Testing | pytest-based unit and integration tests with minimum 60% target coverage. |
| Observability | Logs execution time, row counts, and transformation status for each pipeline step. |

---

## 2. Architecture Diagram

```mermaid
flowchart TD
    GH[GitHub Repository<br/>Source Code + Tests + Docs]
    CI[GitHub Actions CI<br/>ruff + black + pytest<br/>coverage + import checks]

    GH -->|push / pull request| CI

    RDS[Raw Data Sources<br/><br/>
    1. Azure PM sample pattern<br/>
    - telemetry<br/>
    - failures<br/>
    - errors<br/>
    - maintenance<br/>
    - machine metadata<br/><br/>
    2. Synthetic factory data<br/>
    - sensor readings<br/>
    - breakdown logs<br/>
    - production records<br/>
    - maintenance schedule<br/><br/>
    3. CSV files / generated<br/>
    local demo data]

    PDL[Python Data Layer<br/><br/>
    generate_data.py<br/>
    - generate hybrid demo data<br/><br/>
    etl_pipeline.py<br/>
    - validate<br/>
    - clean<br/>
    - load raw tables<br/>
    - run SQL transformations]

    PG[PostgreSQL 15<br/><br/>
    raw schema<br/>
    ├── machine_sensors<br/>
    ├── breakdown_logs<br/>
    ├── production_data<br/>
    └── maintenance_schedule<br/><br/>
    analytics schema<br/>
    ├── machine_daily_kpi<br/>
    ├── machine_reliability<br/>
    ├── downtime_pareto<br/>
    └── downtime_predictions]

    ML[ML Pipeline Layer<br/><br/>
    ml_pipeline.py<br/>
    - feature engineering<br/>
    - anomaly detection<br/>
    - downtime risk model<br/>
    - prediction table update]

    DASH[Streamlit Dashboard<br/><br/>
    dashboard/app.py<br/><br/>
    Page 1: Overview<br/>
    Page 2: Machine KPIs<br/>
    Page 3: Reliability<br/>
    Page 4: Downtime Pareto<br/>
    Page 5: Predictions]

    RDS -->|read CSV / generate data| PDL
    PDL -->|SQLAlchemy / pandas| PG
    PG -->|SQL transformations| ML
    ML -->|read analytics / write predictions| DASH

    ORCH[Orchestration Layer<br/><br/>
    Optional Airflow service<br/>
    ├── DAG: generate_demo_data<br/>
    ├── DAG: run_etl_pipeline<br/>
    ├── DAG: run_analytics_transformations<br/>
    └── DAG: run_ml_predictions]

    DOCKER[Docker Compose Services<br/><br/>
    postgres → PostgreSQL database<br/>
    streamlit → dashboard application<br/>
    etl → one-shot/manual ETL container<br/>
    airflow → optional orchestration service<br/>
    airflow-db → optional metadata database for Airflow]

    ORCH -. orchestrates .-> PDL
    ORCH -. orchestrates .-> ML
    DOCKER -. runs .-> PG
    DOCKER -. runs .-> DASH
    DOCKER -. runs .-> PDL
    DOCKER -. runs .-> ORCH
```
---

## 3. Database Design

### 3.1 Schema Strategy

The database uses two logical schemas:

| Schema      | Purpose                                                                                                                          |
| ----------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `raw`       | Stores ingested source-like data with minimal transformation. This layer preserves traceability and supports idempotent reloads. |
| `analytics` | Stores cleaned, joined, aggregated, and model-ready tables for dashboarding and machine learning.                                |

---

### 3.2 Table: `raw.machine_sensors`

**Schema:** `raw`
**Purpose:** Stores timestamped machine sensor readings from public sample patterns and synthetic factory data.

#### Columns

| Column             |       Data Type | Description                                                      |
| ------------------ | --------------: | ---------------------------------------------------------------- |
| `sensor_id`        |     `BIGSERIAL` | Surrogate primary key for each sensor reading.                   |
| `source_record_id` |          `TEXT` | Stable source identifier used for idempotent loading.            |
| `machine_id`       |          `TEXT` | Unique machine identifier, for example `MCH-001`.                |
| `line_id`          |          `TEXT` | Production line identifier.                                      |
| `timestamp_utc`    |   `TIMESTAMPTZ` | Timestamp of the sensor reading in UTC.                          |
| `voltage`          | `NUMERIC(10,3)` | Electrical voltage reading.                                      |
| `rotation`         | `NUMERIC(10,3)` | Rotational speed or equivalent rotating component signal.        |
| `pressure`         | `NUMERIC(10,3)` | Pneumatic or hydraulic pressure reading.                         |
| `vibration`        | `NUMERIC(10,3)` | Machine vibration reading.                                       |
| `temperature_c`    | `NUMERIC(10,3)` | Synthetic machine temperature in Celsius.                        |
| `current_a`        | `NUMERIC(10,3)` | Synthetic motor current in amperes.                              |
| `load_pct`         |  `NUMERIC(6,3)` | Machine load percentage.                                         |
| `data_source`      |          `TEXT` | Source label, for example `azure_sample_pattern` or `synthetic`. |
| `ingested_at`      |   `TIMESTAMPTZ` | Timestamp when the record was loaded into PostgreSQL.            |

#### Keys and Indexes

| Type              | Columns                       | Purpose                                    |
| ----------------- | ----------------------------- | ------------------------------------------ |
| Primary Key       | `sensor_id`                   | Unique internal row identifier.            |
| Unique Constraint | `source_record_id`            | Prevents duplicate loads.                  |
| Index             | `(machine_id, timestamp_utc)` | Fast machine-level time-series queries.    |
| Index             | `(timestamp_utc)`             | Fast date filtering.                       |
| Index             | `(data_source)`               | Supports source-level data quality checks. |

#### Estimated Row Count After 2 Years

Assumption: 50 machines, hourly sensor readings.

```text
50 machines × 24 hours × 365 days × 2 years = 876,000 rows
```

Estimated size: **~876,000 rows**

---

### 3.3 Table: `raw.breakdown_logs`

**Schema:** `raw`
**Purpose:** Stores machine downtime and breakdown event records.

#### Columns

| Column                |       Data Type | Description                                                                        |
| --------------------- | --------------: | ---------------------------------------------------------------------------------- |
| `breakdown_id`        |     `BIGSERIAL` | Surrogate primary key for each breakdown event.                                    |
| `source_record_id`    |          `TEXT` | Stable source identifier used for idempotent loading.                              |
| `machine_id`          |          `TEXT` | Machine where the breakdown occurred.                                              |
| `line_id`             |          `TEXT` | Production line affected by the breakdown.                                         |
| `breakdown_start`     |   `TIMESTAMPTZ` | Breakdown start timestamp.                                                         |
| `breakdown_end`       |   `TIMESTAMPTZ` | Breakdown end timestamp.                                                           |
| `downtime_minutes`    | `NUMERIC(10,2)` | Total downtime duration in minutes.                                                |
| `failure_category`    |          `TEXT` | High-level category such as mechanical, electrical, pneumatic, sensor, or process. |
| `failure_code`        |          `TEXT` | More specific failure code.                                                        |
| `failure_description` |          `TEXT` | Short human-readable description of the breakdown.                                 |
| `detected_by`         |          `TEXT` | Detection source such as operator, maintenance, sensor alarm, or system alert.     |
| `shift`               |          `TEXT` | Shift during which the breakdown occurred.                                         |
| `is_planned_stop`     |       `BOOLEAN` | Indicates whether the stop was planned.                                            |
| `data_source`         |          `TEXT` | Source label, usually `synthetic` or mapped public sample failure data.            |
| `ingested_at`         |   `TIMESTAMPTZ` | Timestamp when the record was loaded into PostgreSQL.                              |

#### Keys and Indexes

| Type              | Columns                         | Purpose                                       |
| ----------------- | ------------------------------- | --------------------------------------------- |
| Primary Key       | `breakdown_id`                  | Unique internal row identifier.               |
| Unique Constraint | `source_record_id`              | Prevents duplicate breakdown events.          |
| Index             | `(machine_id, breakdown_start)` | Fast reliability queries by machine and time. |
| Index             | `(failure_category)`            | Supports Pareto analysis.                     |
| Index             | `(shift)`                       | Supports shift-level downtime analysis.       |
| Index             | `(is_planned_stop)`             | Separates planned and unplanned downtime.     |

#### Estimated Row Count After 2 Years

Assumption: 50 machines, average 3 breakdowns per machine per month.

```text
50 machines × 3 breakdowns/month × 24 months = 3,600 rows
```

Estimated size: **~3,600 rows**

---

### 3.4 Table: `raw.production_data`

**Schema:** `raw`
**Purpose:** Stores production output, cycle time, scrap, and shift-level manufacturing records.

#### Columns

| Column                       |       Data Type | Description                                           |
| ---------------------------- | --------------: | ----------------------------------------------------- |
| `production_id`              |     `BIGSERIAL` | Surrogate primary key for each production record.     |
| `source_record_id`           |          `TEXT` | Stable source identifier used for idempotent loading. |
| `machine_id`                 |          `TEXT` | Machine that produced the output.                     |
| `line_id`                    |          `TEXT` | Production line identifier.                           |
| `production_date`            |          `DATE` | Calendar date of production.                          |
| `shift`                      |          `TEXT` | Shift identifier, for example `A`, `B`, or `C`.       |
| `planned_production_minutes` | `NUMERIC(10,2)` | Planned available production time.                    |
| `actual_runtime_minutes`     | `NUMERIC(10,2)` | Actual runtime excluding downtime.                    |
| `planned_quantity`           |       `INTEGER` | Planned production quantity.                          |
| `actual_quantity`            |       `INTEGER` | Actual produced quantity.                             |
| `good_quantity`              |       `INTEGER` | Accepted good quantity.                               |
| `scrap_quantity`             |       `INTEGER` | Rejected or scrapped quantity.                        |
| `ideal_cycle_time_seconds`   | `NUMERIC(10,3)` | Ideal time required to produce one unit.              |
| `product_family`             |          `TEXT` | Synthetic product category.                           |
| `data_source`                |          `TEXT` | Source label, usually `synthetic`.                    |
| `ingested_at`                |   `TIMESTAMPTZ` | Timestamp when the record was loaded into PostgreSQL. |

#### Keys and Indexes

| Type              | Columns                         | Purpose                              |
| ----------------- | ------------------------------- | ------------------------------------ |
| Primary Key       | `production_id`                 | Unique internal row identifier.      |
| Unique Constraint | `source_record_id`              | Prevents duplicate production rows.  |
| Index             | `(production_date)`             | Fast date filtering.                 |
| Index             | `(machine_id, production_date)` | Fast machine/day KPI aggregation.    |
| Index             | `(line_id, production_date)`    | Fast line-level dashboard filtering. |
| Index             | `(shift)`                       | Shift-level KPI analysis.            |

#### Estimated Row Count After 2 Years

Assumption: 50 machines, 3 shifts per day.

```text
50 machines × 3 shifts × 365 days × 2 years = 109,500 rows
```

Estimated size: **~109,500 rows**

---

### 3.5 Table: `raw.maintenance_schedule`

**Schema:** `raw`
**Purpose:** Stores planned and completed preventive maintenance activities.

#### Columns

| Column                     |       Data Type | Description                                                                |
| -------------------------- | --------------: | -------------------------------------------------------------------------- |
| `maintenance_id`           |     `BIGSERIAL` | Surrogate primary key for each maintenance event.                          |
| `source_record_id`         |          `TEXT` | Stable source identifier used for idempotent loading.                      |
| `machine_id`               |          `TEXT` | Machine planned for maintenance.                                           |
| `line_id`                  |          `TEXT` | Production line identifier.                                                |
| `scheduled_start`          |   `TIMESTAMPTZ` | Planned maintenance start time.                                            |
| `scheduled_end`            |   `TIMESTAMPTZ` | Planned maintenance end time.                                              |
| `actual_start`             |   `TIMESTAMPTZ` | Actual maintenance start time.                                             |
| `actual_end`               |   `TIMESTAMPTZ` | Actual maintenance end time.                                               |
| `maintenance_type`         |          `TEXT` | Preventive, corrective, inspection, lubrication, calibration, or overhaul. |
| `maintenance_status`       |          `TEXT` | Scheduled, completed, delayed, missed, or cancelled.                       |
| `planned_duration_minutes` | `NUMERIC(10,2)` | Planned maintenance duration.                                              |
| `actual_duration_minutes`  | `NUMERIC(10,2)` | Actual maintenance duration.                                               |
| `technician_team`          |          `TEXT` | Synthetic maintenance team identifier.                                     |
| `notes`                    |          `TEXT` | Optional synthetic remarks.                                                |
| `data_source`              |          `TEXT` | Source label, usually `synthetic`.                                         |
| `ingested_at`              |   `TIMESTAMPTZ` | Timestamp when the record was loaded into PostgreSQL.                      |

#### Keys and Indexes

| Type              | Columns                         | Purpose                                     |
| ----------------- | ------------------------------- | ------------------------------------------- |
| Primary Key       | `maintenance_id`                | Unique internal row identifier.             |
| Unique Constraint | `source_record_id`              | Prevents duplicate maintenance records.     |
| Index             | `(machine_id, scheduled_start)` | Fast maintenance history lookup by machine. |
| Index             | `(maintenance_status)`          | Maintenance compliance analysis.            |
| Index             | `(maintenance_type)`            | Maintenance category analysis.              |

#### Estimated Row Count After 2 Years

Assumption: 50 machines, weekly scheduled maintenance.

```text
50 machines × 52 weeks × 2 years = 5,200 rows
```

Estimated size: **~5,200 rows**

---

### 3.6 Table: `analytics.machine_daily_kpi`

**Schema:** `analytics`
**Purpose:** Stores daily machine-level production and OEE KPI values for dashboard consumption.

#### Columns

| Column                       |       Data Type | Description                                 |
| ---------------------------- | --------------: | ------------------------------------------- |
| `kpi_id`                     |     `BIGSERIAL` | Surrogate primary key.                      |
| `machine_id`                 |          `TEXT` | Machine identifier.                         |
| `line_id`                    |          `TEXT` | Production line identifier.                 |
| `kpi_date`                   |          `DATE` | KPI date.                                   |
| `planned_production_minutes` | `NUMERIC(10,2)` | Total planned production time for the day.  |
| `runtime_minutes`            | `NUMERIC(10,2)` | Actual runtime minutes.                     |
| `downtime_minutes`           | `NUMERIC(10,2)` | Total downtime minutes.                     |
| `planned_quantity`           |       `INTEGER` | Planned production quantity.                |
| `actual_quantity`            |       `INTEGER` | Actual produced quantity.                   |
| `good_quantity`              |       `INTEGER` | Accepted good quantity.                     |
| `scrap_quantity`             |       `INTEGER` | Scrapped quantity.                          |
| `availability_pct`           |  `NUMERIC(6,3)` | Availability percentage.                    |
| `performance_pct`            |  `NUMERIC(6,3)` | Performance percentage.                     |
| `quality_pct`                |  `NUMERIC(6,3)` | Quality percentage.                         |
| `oee_pct`                    |  `NUMERIC(6,3)` | Overall Equipment Effectiveness percentage. |
| `created_at`                 |   `TIMESTAMPTZ` | Timestamp when KPI row was created.         |

#### Keys and Indexes

| Type              | Columns                                                   | Purpose                                   |
| ----------------- | --------------------------------------------------------- | ----------------------------------------- |
| Primary Key       | `kpi_id`                                                  | Unique internal row identifier.           |
| Unique Constraint | `(machine_id, kpi_date)`                                  | Ensures one KPI row per machine per date. |
| Foreign Key       | `machine_id` references raw machine identifiers logically | Logical relationship to raw tables.       |
| Index             | `(kpi_date)`                                              | Dashboard date filtering.                 |
| Index             | `(machine_id, kpi_date)`                                  | Machine-level trend queries.              |
| Index             | `(line_id, kpi_date)`                                     | Line-level trend queries.                 |
| Index             | `(oee_pct)`                                               | Fast sorting by OEE.                      |

#### Estimated Row Count After 2 Years

```text
50 machines × 365 days × 2 years = 36,500 rows
```

Estimated size: **~36,500 rows**

---

### 3.7 Table: `analytics.machine_reliability`

**Schema:** `analytics`
**Purpose:** Stores machine-level reliability KPIs such as MTBF, MTTR, failure count, and maintenance compliance.

#### Columns

| Column                        |       Data Type | Description                                    |
| ----------------------------- | --------------: | ---------------------------------------------- |
| `reliability_id`              |     `BIGSERIAL` | Surrogate primary key.                         |
| `machine_id`                  |          `TEXT` | Machine identifier.                            |
| `line_id`                     |          `TEXT` | Production line identifier.                    |
| `period_start`                |          `DATE` | Start date of reliability period.              |
| `period_end`                  |          `DATE` | End date of reliability period.                |
| `operating_minutes`           | `NUMERIC(12,2)` | Total operating time in the period.            |
| `failure_count`               |       `INTEGER` | Number of unplanned breakdowns.                |
| `total_downtime_minutes`      | `NUMERIC(12,2)` | Total unplanned downtime minutes.              |
| `mtbf_minutes`                | `NUMERIC(12,2)` | Mean Time Between Failures in minutes.         |
| `mttr_minutes`                | `NUMERIC(12,2)` | Mean Time To Repair in minutes.                |
| `maintenance_completed_count` |       `INTEGER` | Number of completed maintenance events.        |
| `maintenance_missed_count`    |       `INTEGER` | Number of missed maintenance events.           |
| `maintenance_compliance_pct`  |  `NUMERIC(6,3)` | Percentage of scheduled maintenance completed. |
| `created_at`                  |   `TIMESTAMPTZ` | Timestamp when reliability row was created.    |

#### Keys and Indexes

| Type              | Columns                                  | Purpose                                 |
| ----------------- | ---------------------------------------- | --------------------------------------- |
| Primary Key       | `reliability_id`                         | Unique internal row identifier.         |
| Unique Constraint | `(machine_id, period_start, period_end)` | Prevents duplicate period calculations. |
| Index             | `(machine_id, period_start)`             | Machine reliability trend queries.      |
| Index             | `(period_start, period_end)`             | Period-based dashboard filtering.       |
| Index             | `(failure_count)`                        | Ranking unreliable machines.            |
| Index             | `(mtbf_minutes)`                         | Ranking machines by reliability.        |

#### Estimated Row Count After 2 Years

Assumption: monthly reliability calculation.

```text
50 machines × 24 months = 1,200 rows
```

Estimated size: **~1,200 rows**

---

### 3.8 Table: `analytics.downtime_pareto`

**Schema:** `analytics`
**Purpose:** Stores aggregated downtime contribution by failure category, machine, line, and period.

#### Columns

| Column                    |       Data Type | Description                             |
| ------------------------- | --------------: | --------------------------------------- |
| `pareto_id`               |     `BIGSERIAL` | Surrogate primary key.                  |
| `period_start`            |          `DATE` | Start date of Pareto period.            |
| `period_end`              |          `DATE` | End date of Pareto period.              |
| `line_id`                 |          `TEXT` | Production line identifier.             |
| `machine_id`              |          `TEXT` | Machine identifier.                     |
| `failure_category`        |          `TEXT` | Breakdown category.                     |
| `failure_count`           |       `INTEGER` | Number of failures in the group.        |
| `downtime_minutes`        | `NUMERIC(12,2)` | Total downtime minutes for the group.   |
| `downtime_pct`            |  `NUMERIC(6,3)` | Percentage of total downtime.           |
| `cumulative_downtime_pct` |  `NUMERIC(6,3)` | Cumulative percentage for Pareto chart. |
| `pareto_rank`             |       `INTEGER` | Rank by downtime contribution.          |
| `created_at`              |   `TIMESTAMPTZ` | Timestamp when row was created.         |

#### Keys and Indexes

| Type              | Columns                                                             | Purpose                              |
| ----------------- | ------------------------------------------------------------------- | ------------------------------------ |
| Primary Key       | `pareto_id`                                                         | Unique internal row identifier.      |
| Unique Constraint | `(period_start, period_end, line_id, machine_id, failure_category)` | Prevents duplicate aggregation rows. |
| Index             | `(period_start, period_end)`                                        | Date filtering.                      |
| Index             | `(failure_category)`                                                | Failure category filtering.          |
| Index             | `(pareto_rank)`                                                     | Fast Pareto chart rendering.         |
| Index             | `(downtime_minutes)`                                                | Ranking by downtime impact.          |

#### Estimated Row Count After 2 Years

Assumption: monthly Pareto aggregation for 50 machines and 5 failure categories.

```text
24 months × 50 machines × 5 categories = 6,000 rows
```

Estimated size: **~6,000 rows**

---

### 3.9 Table: `analytics.downtime_predictions`

**Schema:** `analytics`
**Purpose:** Stores downtime risk predictions and anomaly flags generated by the ML pipeline.

#### Columns

| Column                        |       Data Type | Description                                         |
| ----------------------------- | --------------: | --------------------------------------------------- |
| `prediction_id`               |     `BIGSERIAL` | Surrogate primary key.                              |
| `machine_id`                  |          `TEXT` | Machine identifier.                                 |
| `line_id`                     |          `TEXT` | Production line identifier.                         |
| `prediction_timestamp`        |   `TIMESTAMPTZ` | Timestamp when prediction was generated.            |
| `prediction_date`             |          `DATE` | Prediction date.                                    |
| `risk_score`                  |  `NUMERIC(6,5)` | Probability-like downtime risk score from 0 to 1.   |
| `risk_class`                  |          `TEXT` | Low, medium, or high.                               |
| `predicted_downtime_next_24h` |       `BOOLEAN` | Whether downtime is predicted in the next 24 hours. |
| `anomaly_score`               | `NUMERIC(10,5)` | Numeric anomaly score from sensor behavior.         |
| `is_sensor_anomaly`           |       `BOOLEAN` | Whether the latest sensor pattern is anomalous.     |
| `top_feature_1`               |          `TEXT` | Most influential feature, if available.             |
| `top_feature_2`               |          `TEXT` | Second most influential feature, if available.      |
| `model_version`               |          `TEXT` | Model version used for prediction.                  |
| `created_at`                  |   `TIMESTAMPTZ` | Timestamp when prediction row was stored.           |

#### Keys and Indexes

| Type              | Columns                                             | Purpose                               |
| ----------------- | --------------------------------------------------- | ------------------------------------- |
| Primary Key       | `prediction_id`                                     | Unique internal row identifier.       |
| Unique Constraint | `(machine_id, prediction_timestamp, model_version)` | Prevents duplicate predictions.       |
| Index             | `(prediction_date)`                                 | Dashboard date filtering.             |
| Index             | `(machine_id, prediction_timestamp)`                | Machine-level prediction timeline.    |
| Index             | `(risk_class)`                                      | Fast filtering of high-risk machines. |
| Index             | `(is_sensor_anomaly)`                               | Fast filtering of anomalous machines. |

#### Estimated Row Count After 2 Years

Assumption: daily prediction per machine.

```text
50 machines × 365 days × 2 years = 36,500 rows
```

Estimated size: **~36,500 rows**

---

## 4. Module Design

### 4.1 Module: `src/generate_data.py`

**Purpose:** Generates privacy-safe hybrid demo data based on public predictive maintenance sample patterns and synthetic industrial operating assumptions.

#### Public Functions

| Function / Class                | Signature                                                                                          | Description                                                                    |
| ------------------------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `generate_sensor_data`          | `generate_sensor_data(config: DataGenerationConfig) -> pd.DataFrame`                               | Generates timestamped machine sensor readings.                                 |
| `generate_breakdown_logs`       | `generate_breakdown_logs(config: DataGenerationConfig, sensors: pd.DataFrame) -> pd.DataFrame`     | Generates realistic breakdown events influenced by sensor conditions.          |
| `generate_production_data`      | `generate_production_data(config: DataGenerationConfig, breakdowns: pd.DataFrame) -> pd.DataFrame` | Generates shift-level production output and quality records.                   |
| `generate_maintenance_schedule` | `generate_maintenance_schedule(config: DataGenerationConfig) -> pd.DataFrame`                      | Generates planned and completed maintenance records.                           |
| `write_csv_outputs`             | `write_csv_outputs(dataframes: dict[str, pd.DataFrame], output_dir: Path) -> None`                 | Writes generated datasets to local CSV files.                                  |
| `main`                          | `main() -> None`                                                                                   | CLI entry point for data generation.                                           |
| `DataGenerationConfig`          | `@dataclass class DataGenerationConfig`                                                            | Stores generation settings such as machine count, date range, and random seed. |

#### Dependencies

```python
from dataclasses import dataclass
from pathlib import Path
import logging
import numpy as np
import pandas as pd
```

#### Calls Other Modules

| Called Module              | Purpose                             |
| -------------------------- | ----------------------------------- |
| `src.utils.logging_config` | Optional centralized logging setup. |
| `src.utils.paths`          | Optional project path helpers.      |

---

### 4.2 Module: `src/etl_pipeline.py`

**Purpose:** Loads raw CSV/generated data into PostgreSQL, validates records, runs SQL transformations, and refreshes analytics tables.

#### Public Functions

| Function / Class            | Signature                                                                                           | Description                                                  |
| --------------------------- | --------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| `load_raw_table`            | `load_raw_table(engine: Engine, df: pd.DataFrame, schema: str, table: str, unique_key: str) -> int` | Loads a dataframe into a raw table idempotently.             |
| `run_sql_file`              | `run_sql_file(engine: Engine, sql_path: Path) -> None`                                              | Executes a SQL transformation file.                          |
| `refresh_analytics_tables`  | `refresh_analytics_tables(engine: Engine, sql_dir: Path) -> None`                                   | Runs all analytics SQL transformations in dependency order.  |
| `validate_required_columns` | `validate_required_columns(df: pd.DataFrame, required_columns: set[str], table_name: str) -> None`  | Validates that an input dataframe contains required columns. |
| `load_all_raw_data`         | `load_all_raw_data(engine: Engine, input_dir: Path) -> dict[str, int]`                              | Loads all raw CSV files and returns row counts by table.     |
| `run_etl`                   | `run_etl(input_dir: Path, sql_dir: Path) -> dict[str, int]`                                         | End-to-end ETL entry point.                                  |
| `main`                      | `main() -> None`                                                                                    | CLI entry point for ETL execution.                           |

#### Dependencies

```python
from pathlib import Path
import logging
import time
import pandas as pd
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError
from src.utils.db import get_engine
```

#### Calls Other Modules

| Called Module       | Purpose                                                                |
| ------------------- | ---------------------------------------------------------------------- |
| `src.utils.db`      | Creates SQLAlchemy engine and database connections.                    |
| `src.generate_data` | Optional fallback for demo data generation when CSV files are missing. |

---

### 4.3 Module: `src/ml_pipeline.py`

**Purpose:** Builds features, trains a downtime risk model, detects sensor anomalies, and writes prediction results into PostgreSQL.

#### Public Functions

| Function / Class          | Signature                                                                         | Description                                                    |                               |                                                      |
| ------------------------- | --------------------------------------------------------------------------------- | -------------------------------------------------------------- | ----------------------------- | ---------------------------------------------------- |
| `load_training_data`      | `load_training_data(engine: Engine, start_date: date                              | None = None, end_date: date                                    | None = None) -> pd.DataFrame` | Loads joined feature and label data from PostgreSQL. |
| `build_features`          | `build_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]`              | Creates model features and target labels.                      |                               |                                                      |
| `train_downtime_model`    | `train_downtime_model(X: pd.DataFrame, y: pd.Series) -> Pipeline`                 | Trains a Scikit-learn classification pipeline.                 |                               |                                                      |
| `detect_sensor_anomalies` | `detect_sensor_anomalies(sensor_df: pd.DataFrame) -> pd.DataFrame`                | Adds anomaly score and anomaly flag columns.                   |                               |                                                      |
| `generate_predictions`    | `generate_predictions(model: Pipeline, feature_df: pd.DataFrame) -> pd.DataFrame` | Generates downtime risk scores and risk classes.               |                               |                                                      |
| `save_model`              | `save_model(model: Pipeline, model_path: Path) -> None`                           | Persists trained model to disk.                                |                               |                                                      |
| `load_model`              | `load_model(model_path: Path) -> Pipeline`                                        | Loads trained model from disk.                                 |                               |                                                      |
| `write_predictions`       | `write_predictions(engine: Engine, predictions: pd.DataFrame) -> int`             | Writes prediction results to `analytics.downtime_predictions`. |                               |                                                      |
| `run_ml_pipeline`         | `run_ml_pipeline(model_path: Path) -> int`                                        | End-to-end ML pipeline entry point.                            |                               |                                                      |
| `main`                    | `main() -> None`                                                                  | CLI entry point for ML execution.                              |                               |                                                      |

#### Dependencies

```python
from datetime import date
from pathlib import Path
import logging
import joblib
import pandas as pd
from sqlalchemy import Engine
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from src.utils.db import get_engine
```

#### Calls Other Modules

| Called Module      | Purpose                                         |
| ------------------ | ----------------------------------------------- |
| `src.utils.db`     | Provides PostgreSQL engine.                     |
| `src.etl_pipeline` | Optional validation or SQL execution utilities. |

---

### 4.4 Module: `src/dashboard/app.py`

**Purpose:** Streamlit application that visualizes industrial KPIs, reliability metrics, downtime Pareto, and prediction results.

#### Public Functions

| Function / Class          | Signature                                                                 | Description                                            |
| ------------------------- | ------------------------------------------------------------------------- | ------------------------------------------------------ |
| `main`                    | `main() -> None`                                                          | Streamlit app entry point.                             |
| `load_kpi_data`           | `load_kpi_data(start_date: date, end_date: date) -> pd.DataFrame`         | Loads OEE and production KPI data from PostgreSQL.     |
| `load_reliability_data`   | `load_reliability_data(start_date: date, end_date: date) -> pd.DataFrame` | Loads MTBF, MTTR, and maintenance compliance data.     |
| `load_pareto_data`        | `load_pareto_data(start_date: date, end_date: date) -> pd.DataFrame`      | Loads downtime Pareto data.                            |
| `load_prediction_data`    | `load_prediction_data(start_date: date, end_date: date) -> pd.DataFrame`  | Loads downtime risk prediction data.                   |
| `render_sidebar_filters`  | `render_sidebar_filters() -> dict[str, Any]`                              | Renders dashboard filters and returns selected values. |
| `render_overview_page`    | `render_overview_page(filters: dict[str, Any]) -> None`                   | Renders executive overview.                            |
| `render_machine_kpi_page` | `render_machine_kpi_page(filters: dict[str, Any]) -> None`                | Renders machine KPI page.                              |
| `render_reliability_page` | `render_reliability_page(filters: dict[str, Any]) -> None`                | Renders reliability page.                              |
| `render_pareto_page`      | `render_pareto_page(filters: dict[str, Any]) -> None`                     | Renders downtime Pareto page.                          |
| `render_predictions_page` | `render_predictions_page(filters: dict[str, Any]) -> None`                | Renders predictive downtime page.                      |

#### Dependencies

```python
from datetime import date
from typing import Any
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from src.utils.db import get_engine
```

#### Calls Other Modules

| Called Module  | Purpose                                        |
| -------------- | ---------------------------------------------- |
| `src.utils.db` | Creates database engine for dashboard queries. |

---

### 4.5 Module: `src/utils/db.py`

**Purpose:** Provides reusable database connection and query utilities.

#### Public Functions

| Function / Class   | Signature                                                       | Description                                     |                                                |
| ------------------ | --------------------------------------------------------------- | ----------------------------------------------- | ---------------------------------------------- |
| `get_database_url` | `get_database_url() -> str`                                     | Builds database URL from environment variables. |                                                |
| `get_engine`       | `get_engine() -> Engine`                                        | Creates a SQLAlchemy engine.                    |                                                |
| `test_connection`  | `test_connection(engine: Engine) -> bool`                       | Tests database connectivity.                    |                                                |
| `read_sql`         | `read_sql(query: str, params: dict[str, Any]                    | None = None) -> pd.DataFrame`                   | Reads SQL query result into pandas dataframe.  |
| `execute_sql`      | `execute_sql(engine: Engine, query: str, params: dict[str, Any] | None = None) -> None`                           | Executes a SQL statement inside a transaction. |

#### Dependencies

```python
import os
from typing import Any
import pandas as pd
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
```

#### Calls Other Modules

This module is a utility layer and does not call other project modules.

---

### 4.6 Module: `tests/`

**Purpose:** Contains automated tests for data generation, ETL validation, SQL transformations, ML functions, and dashboard query helpers.

#### Test Files

| File Path                         | Purpose                                                                                     |
| --------------------------------- | ------------------------------------------------------------------------------------------- |
| `tests/test_generate_data.py`     | Tests synthetic data shape, required columns, date ranges, and reproducibility.             |
| `tests/test_etl_pipeline.py`      | Tests validation functions, idempotent load logic, and SQL execution helpers.               |
| `tests/test_ml_pipeline.py`       | Tests feature engineering, model training, prediction output schema, and anomaly detection. |
| `tests/test_db.py`                | Tests database URL generation and connection helper behavior.                               |
| `tests/test_dashboard_queries.py` | Tests dashboard query functions using mocked database responses.                            |

---

## 5. API Contracts — Internal

This section defines function contracts for all functions that cross module boundaries.

---

### 5.1 `src.utils.db.get_database_url`

```python
def get_database_url() -> str:
    ...
```

#### Inputs

None. Reads environment variables:

| Environment Variable | Type  | Required | Description                                 |
| -------------------- | ----- | -------: | ------------------------------------------- |
| `POSTGRES_HOST`      | `str` |       No | Database host. Default: `localhost`.        |
| `POSTGRES_PORT`      | `str` |       No | Database port. Default: `5432`.             |
| `POSTGRES_DB`        | `str` |       No | Database name. Default: `smartfactory`.     |
| `POSTGRES_USER`      | `str` |       No | Database username. Default: `smartfactory`. |
| `POSTGRES_PASSWORD`  | `str` |       No | Database password. Default: `smartfactory`. |

#### Output

| Type  | Description                                    |
| ----- | ---------------------------------------------- |
| `str` | SQLAlchemy-compatible PostgreSQL database URL. |

#### Exceptions

| Exception    | Condition                                            |
| ------------ | ---------------------------------------------------- |
| `ValueError` | Required database configuration is invalid or empty. |

---

### 5.2 `src.utils.db.get_engine`

```python
def get_engine() -> Engine:
    ...
```

#### Inputs

None.

#### Output

| Type                | Description                            |
| ------------------- | -------------------------------------- |
| `sqlalchemy.Engine` | Configured SQLAlchemy database engine. |

#### Exceptions

| Exception                        | Condition                               |
| -------------------------------- | --------------------------------------- |
| `sqlalchemy.exc.SQLAlchemyError` | Engine creation or configuration fails. |
| `ValueError`                     | Database URL is invalid.                |

---

### 5.3 `src.generate_data.generate_sensor_data`

```python
def generate_sensor_data(config: DataGenerationConfig) -> pd.DataFrame:
    ...
```

#### Inputs

| Name     | Type                   | Description               |
| -------- | ---------------------- | ------------------------- |
| `config` | `DataGenerationConfig` | Data generation settings. |

#### Output

| Type           | Description                                                |
| -------------- | ---------------------------------------------------------- |
| `pd.DataFrame` | Sensor dataset matching `raw.machine_sensors` load schema. |

#### Exceptions

| Exception      | Condition                                        |
| -------------- | ------------------------------------------------ |
| `ValueError`   | Invalid date range, machine count, or frequency. |
| `RuntimeError` | Unexpected data generation failure.              |

---

### 5.4 `src.generate_data.generate_breakdown_logs`

```python
def generate_breakdown_logs(
    config: DataGenerationConfig,
    sensors: pd.DataFrame
) -> pd.DataFrame:
    ...
```

#### Inputs

| Name      | Type                   | Description                           |
| --------- | ---------------------- | ------------------------------------- |
| `config`  | `DataGenerationConfig` | Data generation settings.             |
| `sensors` | `pd.DataFrame`         | Generated or loaded sensor dataframe. |

#### Output

| Type           | Description                                                 |
| -------------- | ----------------------------------------------------------- |
| `pd.DataFrame` | Breakdown events matching `raw.breakdown_logs` load schema. |

#### Exceptions

| Exception      | Condition                                              |
| -------------- | ------------------------------------------------------ |
| `ValueError`   | Sensor dataframe is empty or missing required columns. |
| `RuntimeError` | Breakdown generation fails.                            |

---

### 5.5 `src.generate_data.generate_production_data`

```python
def generate_production_data(
    config: DataGenerationConfig,
    breakdowns: pd.DataFrame
) -> pd.DataFrame:
    ...
```

#### Inputs

| Name         | Type                   | Description                                                     |
| ------------ | ---------------------- | --------------------------------------------------------------- |
| `config`     | `DataGenerationConfig` | Data generation settings.                                       |
| `breakdowns` | `pd.DataFrame`         | Breakdown records used to reduce runtime and production output. |

#### Output

| Type           | Description                                                    |
| -------------- | -------------------------------------------------------------- |
| `pd.DataFrame` | Production records matching `raw.production_data` load schema. |

#### Exceptions

| Exception      | Condition                                  |
| -------------- | ------------------------------------------ |
| `ValueError`   | Invalid shift configuration or date range. |
| `RuntimeError` | Production generation fails.               |

---

### 5.6 `src.etl_pipeline.load_raw_table`

```python
def load_raw_table(
    engine: Engine,
    df: pd.DataFrame,
    schema: str,
    table: str,
    unique_key: str
) -> int:
    ...
```

#### Inputs

| Name         | Type                | Description                                      |
| ------------ | ------------------- | ------------------------------------------------ |
| `engine`     | `sqlalchemy.Engine` | Database engine.                                 |
| `df`         | `pd.DataFrame`      | Dataframe to load.                               |
| `schema`     | `str`               | Target schema name, normally `raw`.              |
| `table`      | `str`               | Target table name.                               |
| `unique_key` | `str`               | Column used for idempotent upsert/deduplication. |

#### Output

| Type  | Description                         |
| ----- | ----------------------------------- |
| `int` | Number of inserted or updated rows. |

#### Exceptions

| Exception                        | Condition                                                   |
| -------------------------------- | ----------------------------------------------------------- |
| `ValueError`                     | Empty dataframe, missing unique key, or invalid table name. |
| `sqlalchemy.exc.SQLAlchemyError` | Database insert/upsert fails.                               |

---

### 5.7 `src.etl_pipeline.run_sql_file`

```python
def run_sql_file(engine: Engine, sql_path: Path) -> None:
    ...
```

#### Inputs

| Name       | Type                | Description       |
| ---------- | ------------------- | ----------------- |
| `engine`   | `sqlalchemy.Engine` | Database engine.  |
| `sql_path` | `Path`              | Path to SQL file. |

#### Output

None.

#### Exceptions

| Exception                        | Condition                |
| -------------------------------- | ------------------------ |
| `FileNotFoundError`              | SQL file does not exist. |
| `sqlalchemy.exc.SQLAlchemyError` | SQL execution fails.     |

---

### 5.8 `src.etl_pipeline.run_etl`

```python
def run_etl(input_dir: Path, sql_dir: Path) -> dict[str, int]:
    ...
```

#### Inputs

| Name        | Type   | Description                                    |
| ----------- | ------ | ---------------------------------------------- |
| `input_dir` | `Path` | Directory containing raw CSV files.            |
| `sql_dir`   | `Path` | Directory containing transformation SQL files. |

#### Output

| Type             | Description                      |
| ---------------- | -------------------------------- |
| `dict[str, int]` | Row counts loaded by table name. |

#### Exceptions

| Exception                        | Condition                                       |
| -------------------------------- | ----------------------------------------------- |
| `FileNotFoundError`              | Required input CSV or SQL directory is missing. |
| `ValueError`                     | Input data fails validation.                    |
| `sqlalchemy.exc.SQLAlchemyError` | Database operation fails.                       |

---

### 5.9 `src.ml_pipeline.load_training_data`

```python
def load_training_data(
    engine: Engine,
    start_date: date | None = None,
    end_date: date | None = None
) -> pd.DataFrame:
    ...
```

#### Inputs

| Name         | Type                | Description      |                             |
| ------------ | ------------------- | ---------------- | --------------------------- |
| `engine`     | `sqlalchemy.Engine` | Database engine. |                             |
| `start_date` | `date               | None`            | Optional start date filter. |
| `end_date`   | `date               | None`            | Optional end date filter.   |

#### Output

| Type           | Description                                        |
| -------------- | -------------------------------------------------- |
| `pd.DataFrame` | Training dataset with features and downtime label. |

#### Exceptions

| Exception                        | Condition                                                   |
| -------------------------------- | ----------------------------------------------------------- |
| `ValueError`                     | Date range is invalid or no training records are available. |
| `sqlalchemy.exc.SQLAlchemyError` | Query fails.                                                |

---

### 5.10 `src.ml_pipeline.build_features`

```python
def build_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    ...
```

#### Inputs

| Name | Type           | Description         |
| ---- | -------------- | ------------------- |
| `df` | `pd.DataFrame` | Training dataframe. |

#### Output

| Type                             | Description                               |
| -------------------------------- | ----------------------------------------- |
| `tuple[pd.DataFrame, pd.Series]` | Feature matrix `X` and target vector `y`. |

#### Exceptions

| Exception    | Condition                                       |
| ------------ | ----------------------------------------------- |
| `ValueError` | Required feature or target columns are missing. |

---

### 5.11 `src.ml_pipeline.train_downtime_model`

```python
def train_downtime_model(X: pd.DataFrame, y: pd.Series) -> Pipeline:
    ...
```

#### Inputs

| Name | Type           | Description             |
| ---- | -------------- | ----------------------- |
| `X`  | `pd.DataFrame` | Feature matrix.         |
| `y`  | `pd.Series`    | Binary downtime target. |

#### Output

| Type                        | Description                          |
| --------------------------- | ------------------------------------ |
| `sklearn.pipeline.Pipeline` | Trained Scikit-learn model pipeline. |

#### Exceptions

| Exception      | Condition                                                           |
| -------------- | ------------------------------------------------------------------- |
| `ValueError`   | Training data is empty, invalid, or contains only one target class. |
| `RuntimeError` | Model training fails unexpectedly.                                  |

---

### 5.12 `src.ml_pipeline.detect_sensor_anomalies`

```python
def detect_sensor_anomalies(sensor_df: pd.DataFrame) -> pd.DataFrame:
    ...
```

#### Inputs

| Name        | Type           | Description      |
| ----------- | -------------- | ---------------- |
| `sensor_df` | `pd.DataFrame` | Sensor readings. |

#### Output

| Type           | Description                                                    |
| -------------- | -------------------------------------------------------------- |
| `pd.DataFrame` | Sensor dataframe with `anomaly_score` and `is_sensor_anomaly`. |

#### Exceptions

| Exception      | Condition                            |
| -------------- | ------------------------------------ |
| `ValueError`   | Required sensor columns are missing. |
| `RuntimeError` | Anomaly detection fails.             |

---

### 5.13 `src.ml_pipeline.write_predictions`

```python
def write_predictions(engine: Engine, predictions: pd.DataFrame) -> int:
    ...
```

#### Inputs

| Name          | Type                | Description           |
| ------------- | ------------------- | --------------------- |
| `engine`      | `sqlalchemy.Engine` | Database engine.      |
| `predictions` | `pd.DataFrame`      | Prediction dataframe. |

#### Output

| Type  | Description                        |
| ----- | ---------------------------------- |
| `int` | Number of prediction rows written. |

#### Exceptions

| Exception                        | Condition                                                  |
| -------------------------------- | ---------------------------------------------------------- |
| `ValueError`                     | Prediction dataframe is empty or missing required columns. |
| `sqlalchemy.exc.SQLAlchemyError` | Database write fails.                                      |

---

### 5.14 `src.dashboard.app.load_kpi_data`

```python
def load_kpi_data(start_date: date, end_date: date) -> pd.DataFrame:
    ...
```

#### Inputs

| Name         | Type   | Description           |
| ------------ | ------ | --------------------- |
| `start_date` | `date` | Dashboard start date. |
| `end_date`   | `date` | Dashboard end date.   |

#### Output

| Type           | Description                                  |
| -------------- | -------------------------------------------- |
| `pd.DataFrame` | KPI data from `analytics.machine_daily_kpi`. |

#### Exceptions

| Exception                        | Condition              |
| -------------------------------- | ---------------------- |
| `ValueError`                     | Date range is invalid. |
| `sqlalchemy.exc.SQLAlchemyError` | Query fails.           |

---

### 5.15 `src.dashboard.app.load_prediction_data`

```python
def load_prediction_data(start_date: date, end_date: date) -> pd.DataFrame:
    ...
```

#### Inputs

| Name         | Type   | Description           |
| ------------ | ------ | --------------------- |
| `start_date` | `date` | Dashboard start date. |
| `end_date`   | `date` | Dashboard end date.   |

#### Output

| Type           | Description                                            |
| -------------- | ------------------------------------------------------ |
| `pd.DataFrame` | Prediction data from `analytics.downtime_predictions`. |

#### Exceptions

| Exception                        | Condition              |
| -------------------------------- | ---------------------- |
| `ValueError`                     | Date range is invalid. |
| `sqlalchemy.exc.SQLAlchemyError` | Query fails.           |

---

## 6. Development Phases

### 6.1 MVP — Week 1 to Week 2

Goal: Build a working end-to-end local demo with generated data, PostgreSQL storage, core KPIs, and basic dashboard pages.

#### Included

| Area                | Deliverables                                                                |
| ------------------- | --------------------------------------------------------------------------- |
| Repository Setup    | Project structure, README, `ARCHITECTURE.md`, `.gitignore`, `.env.example`. |
| Python Environment  | Python 3.11 setup, `requirements.txt` or `pyproject.toml`.                  |
| Docker Compose      | PostgreSQL and Streamlit services.                                          |
| Data Generation     | Synthetic sensor, production, breakdown, and maintenance data.              |
| Database            | Create `raw` and `analytics` schemas and core tables.                       |
| ETL                 | Load CSV data into raw tables idempotently.                                 |
| SQL Transformations | Build `analytics.machine_daily_kpi`.                                        |
| Dashboard           | Overview page and Machine KPI page.                                         |
| Testing             | Basic unit tests for data generation and validation.                        |
| Code Quality        | ruff, black, pytest in GitHub Actions.                                      |

#### MVP Success Criteria

* `docker compose up` starts PostgreSQL and Streamlit.
* Data can be generated and loaded from scratch.
* Dashboard displays OEE, downtime, production volume, and machine trends.
* CI pipeline passes on GitHub.

---

### 6.2 V2 — Week 3 to Week 4

Goal: Add reliability analytics, downtime Pareto, stronger SQL transformations, and improved dashboard quality.

#### Added

| Area              | Deliverables                                                                                          |
| ----------------- | ----------------------------------------------------------------------------------------------------- |
| Reliability Layer | Build `analytics.machine_reliability` with MTBF, MTTR, failure count, and maintenance compliance.     |
| Pareto Layer      | Build `analytics.downtime_pareto`.                                                                    |
| Dashboard         | Add Reliability page and Downtime Pareto page.                                                        |
| Data Quality      | Add validation for nulls, negative durations, impossible sensor values, and duplicate source records. |
| Logging           | Log row counts, durations, and failed validation checks.                                              |
| Tests             | Add ETL tests and SQL transformation tests.                                                           |
| Documentation     | Add data dictionary and pipeline usage guide.                                                         |

#### V2 Success Criteria

* Dashboard supports four completed pages.
* MTBF and MTTR are calculated correctly from breakdown data.
* Pareto chart clearly identifies top downtime contributors.
* ETL logs are understandable and recruiter-demo friendly.

---

### 6.3 V3 — Week 5 to Week 6

Goal: Add machine learning, anomaly detection, orchestration, and final portfolio polish.

#### Added

| Area              | Deliverables                                                             |
| ----------------- | ------------------------------------------------------------------------ |
| ML Pipeline       | Feature engineering, downtime risk classifier, model persistence.        |
| Anomaly Detection | Sensor anomaly scoring using statistical or Scikit-learn approach.       |
| Prediction Table  | Build and populate `analytics.downtime_predictions`.                     |
| Dashboard         | Add Predictive Downtime page.                                            |
| Airflow           | Optional DAGs for generation, ETL, analytics refresh, and ML prediction. |
| Observability     | Structured logs for all major pipeline stages.                           |
| Testing           | Increase test coverage to minimum 60%.                                   |
| Portfolio Polish  | Screenshots, demo GIF, architecture diagram, recruiter-friendly README.  |

#### V3 Success Criteria

* Dashboard includes five pages.
* Downtime risk predictions are visible and explainable at a basic level.
* Project can be demonstrated locally without confidential data.
* Documentation clearly explains that the dataset is public/synthetic and privacy-safe.

---

## 7. Non-Functional Requirements

### 7.1 Performance

| Requirement                 | Target                                                        |
| --------------------------- | ------------------------------------------------------------- |
| Dashboard initial load time | Under 3 seconds for default date range.                       |
| Dashboard filter response   | Under 2 seconds for common filters.                           |
| ETL load time               | Under 2 minutes for 2 years of demo data on a typical laptop. |
| SQL aggregation time        | Under 30 seconds for full analytics refresh.                  |
| Prediction generation       | Under 60 seconds for daily machine-level prediction batch.    |

#### Performance Design Choices

* Pre-aggregate dashboard-heavy metrics into `analytics` tables.
* Avoid querying raw sensor-level data directly from most dashboard pages.
* Add indexes on date, machine, line, risk class, and failure category.
* Use Streamlit caching for read-only query results.
* Limit default dashboard date range to recent 30 or 90 days.

---

### 7.2 Reliability

| Requirement        | Design                                                                    |
| ------------------ | ------------------------------------------------------------------------- |
| Idempotent ETL     | Use `source_record_id` unique constraints and upsert/deduplication logic. |
| Safe Re-runs       | ETL can be re-executed without duplicate rows.                            |
| Transaction Safety | SQL transformations run inside database transactions where practical.     |
| Failure Isolation  | Raw loading, analytics refresh, and ML prediction are separate steps.     |
| Reproducible Data  | Synthetic generation supports fixed random seed.                          |

---

### 7.3 Observability

All pipeline steps must log:

| Log Field          | Description                |
| ------------------ | -------------------------- |
| `step_name`        | Name of pipeline step.     |
| `started_at`       | Start timestamp.           |
| `finished_at`      | End timestamp.             |
| `duration_seconds` | Step runtime.              |
| `rows_read`        | Number of records read.    |
| `rows_written`     | Number of records written. |
| `status`           | Success or failure.        |
| `error_message`    | Error detail when failed.  |

Example log format:

```text
2026-05-01 10:15:22 INFO step=load_raw_table table=raw.machine_sensors rows_read=876000 rows_written=876000 duration_seconds=42.8 status=success
```

---

### 7.4 Testing

| Requirement           | Target                                                   |
| --------------------- | -------------------------------------------------------- |
| Minimum code coverage | 60%                                                      |
| Test framework        | pytest                                                   |
| Unit tests            | Data generation, utility functions, feature engineering. |
| Integration tests     | ETL loading and SQL transformation execution.            |
| Dashboard tests       | Query helpers and dataframe transformations.             |
| CI tests              | Run on every pull request and push to main.              |

---

### 7.5 Maintainability

| Requirement     | Design                                                       |
| --------------- | ------------------------------------------------------------ |
| Code formatting | black                                                        |
| Linting         | ruff                                                         |
| Modular design  | Separate data generation, ETL, ML, dashboard, and utilities. |
| Documentation   | Architecture, README, data dictionary, setup guide.          |
| Configuration   | `.env` and environment variables.                            |
| Type hints      | Required for public functions.                               |

---

### 7.6 Security and Data Privacy

| Requirement                  | Design                                                   |
| ---------------------------- | -------------------------------------------------------- |
| No confidential company data | Only public sample patterns and synthetic data are used. |
| No real machine names        | Use generic machine IDs such as `MCH-001`.               |
| No real employee data        | Technician teams are synthetic labels.                   |
| No real production volumes   | Production records are generated.                        |
| Safe portfolio sharing       | Repository can be public without exposing employer data. |

---

## 8. Folder Structure

```text
smartfactory-reliability-analytics/
│
├── README.md
│   └── Main project overview, screenshots, setup instructions, and portfolio explanation.
│
├── ARCHITECTURE.md
│   └── Professional architecture document describing system design and implementation plan.
│
├── DATA_DICTIONARY.md
│   └── Human-readable explanation of all datasets, tables, and business metrics.
│
├── LICENSE
│   └── Project license.
│
├── .gitignore
│   └── Excludes virtual environments, cache files, local data, model artifacts, and secrets.
│
├── .env.example
│   └── Example environment variables for local development.
│
├── docker-compose.yml
│   └── Defines PostgreSQL, Streamlit, ETL, and optional Airflow services.
│
├── Dockerfile
│   └── Python application image for ETL, ML, and dashboard execution.
│
├── pyproject.toml
│   └── Python dependencies, formatting, linting, and pytest configuration.
│
├── requirements.txt
│   └── Alternative dependency file for simple installation.
│
├── Makefile
│   └── Developer shortcuts for setup, format, lint, test, data generation, ETL, and dashboard.
│
│
├── .github/
│   └── workflows/
│       └── ci.yml
│           └── GitHub Actions workflow for ruff, black, pytest, and coverage.
│
├── data/
│   ├── README.md
│   │   └── Explains privacy-safe data strategy and how data is generated.
│   │
│   ├── raw/
│   │   └── Local generated CSV files before database loading.
│   │
│   ├── external/
│   │   └── Optional public sample files following Azure Predictive Maintenance data patterns.
│   │
│   └── processed/
│       └── Optional intermediate processed files for debugging or demos.
│
├── models/
│   ├── README.md
│   │   └── Explains model artifacts and versioning.
│   │
│   └── downtime_model.joblib
│       └── Trained Scikit-learn downtime risk model artifact.
│
├── logs/
│   └── .gitkeep
│       └── Placeholder for local pipeline logs.
│
├── sql/
│   ├── 00_create_schemas.sql
│   │   └── Creates `raw` and `analytics` schemas.
│   │
│   ├── 01_create_raw_tables.sql
│   │   └── Creates raw data tables and indexes.
│   │
│   ├── 02_create_analytics_tables.sql
│   │   └── Creates analytics tables and indexes.
│   │
│   ├── 10_transform_machine_daily_kpi.sql
│   │   └── Builds daily OEE and production KPI table.
│   │
│   ├── 20_transform_machine_reliability.sql
│   │   └── Builds MTBF, MTTR, failure count, and maintenance compliance table.
│   │
│   ├── 30_transform_downtime_pareto.sql
│   │   └── Builds downtime Pareto aggregation.
│   │
│   └── 40_ml_feature_view.sql
│       └── Creates SQL view or query foundation for ML feature generation.
│
├── airflow/
│   ├── README.md
│   │   └── Explains optional Airflow orchestration.
│   │
│   └── dags/
│       └── smartfactory_pipeline_dag.py
│           └── Optional DAG for generation, ETL, analytics refresh, and ML predictions.
│
├── src/
│   ├── __init__.py
│   │   └── Marks source directory as a Python package.
│   │
│   ├── generate_data.py
│   │   └── Generates privacy-safe synthetic and hybrid demo data.
│   │
│   ├── etl_pipeline.py
│   │   └── Loads raw data and refreshes analytics tables.
│   │
│   ├── ml_pipeline.py
│   │   └── Trains model, detects anomalies, and writes downtime predictions.
│   │
│   ├── dashboard/
│   │   ├── __init__.py
│   │   │   └── Marks dashboard directory as a Python package.
│   │   │
│   │   └── app.py
│   │       └── Streamlit five-page dashboard application.
│   │
│   └── utils/
│       ├── __init__.py
│       │   └── Marks utils directory as a Python package.
│       │
│       ├── db.py
│       │   └── Database connection and SQL execution helpers.
│       │
│       ├── logging_config.py
│       │   └── Central logging configuration.
│       │
│       └── paths.py
│           └── Shared project path utilities.
│
└── tests/
    ├── __init__.py
    │   └── Marks tests as a package.
    │
    ├── conftest.py
    │   └── Shared pytest fixtures.
    │
    ├── test_generate_data.py
    │   └── Tests synthetic data generation.
    │
    ├── test_etl_pipeline.py
    │   └── Tests ETL validation and loading behavior.
    │
    ├── test_ml_pipeline.py
    │   └── Tests feature engineering, anomaly detection, and predictions.
    │
    ├── test_db.py
    │   └── Tests database utility functions.
    │
    └── test_dashboard_queries.py
        └── Tests dashboard data loading and transformation helpers.
```

---

## 9. Local Development Setup

This setup assumes Ubuntu or macOS.

---

### 9.1 Prerequisites

Install the following:

| Tool           | Recommended Version      |
| -------------- | ------------------------ |
| Python         | 3.11                     |
| Docker         | Latest stable            |
| Docker Compose | v2                       |
| Git            | Latest stable            |
| Make           | Optional but recommended |

Check installed versions:

```bash
python3 --version
docker --version
docker compose version
git --version
```

---

### 9.2 Clone the Repository

```bash
git clone https://github.com/<your-github-username>/smartfactory-reliability-analytics.git
cd smartfactory-reliability-analytics
```

---

### 9.3 Create Environment File

```bash
cp .env.example .env
```

Example `.env`:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=smartfactory
POSTGRES_USER=smartfactory
POSTGRES_PASSWORD=smartfactory

DATA_START_DATE=2024-01-01
DATA_END_DATE=2025-12-31
MACHINE_COUNT=50
RANDOM_SEED=42
```

---

### 9.4 Start PostgreSQL

```bash
docker compose up -d postgres
```

Verify container status:

```bash
docker compose ps
```

---

### 9.5 Create Python Virtual Environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

Upgrade pip:

```bash
python -m pip install --upgrade pip
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Alternative with `pyproject.toml`:

```bash
pip install -e ".[dev]"
```

---

### 9.6 Initialize Database Schemas and Tables

```bash
python -m src.etl_pipeline --init-db
```

Alternative using SQL files manually:

```bash
psql postgresql://smartfactory:smartfactory@localhost:5432/smartfactory \
  -f sql/00_create_schemas.sql

psql postgresql://smartfactory:smartfactory@localhost:5432/smartfactory \
  -f sql/01_create_raw_tables.sql

psql postgresql://smartfactory:smartfactory@localhost:5432/smartfactory \
  -f sql/02_create_analytics_tables.sql
```

---

### 9.7 Generate Demo Data

```bash
python -m src.generate_data \
  --start-date 2024-01-01 \
  --end-date 2025-12-31 \
  --machine-count 50 \
  --output-dir data/raw
```

Expected output files:

```text
data/raw/machine_sensors.csv
data/raw/breakdown_logs.csv
data/raw/production_data.csv
data/raw/maintenance_schedule.csv
```

---

### 9.8 Run ETL Pipeline

```bash
python -m src.etl_pipeline \
  --input-dir data/raw \
  --sql-dir sql
```

Expected behavior:

* Load raw CSV files into `raw` schema.
* Deduplicate by `source_record_id`.
* Refresh analytics tables.
* Log row counts and execution duration.

---

### 9.9 Train Model and Generate Predictions

```bash
python -m src.ml_pipeline \
  --model-path models/downtime_model.joblib
```

Expected behavior:

* Load training data from PostgreSQL.
* Build features.
* Train downtime risk model.
* Detect sensor anomalies.
* Write prediction rows to `analytics.downtime_predictions`.

---

### 9.10 Run Streamlit Dashboard

```bash
streamlit run src/dashboard/app.py
```

Open browser:

```text
http://localhost:8501
```

---

### 9.11 Run with Docker Compose

Build and start all main services:

```bash
docker compose up --build
```

Run ETL inside Docker:

```bash
docker compose run --rm etl python -m src.etl_pipeline --input-dir data/raw --sql-dir sql
```

Run ML inside Docker:

```bash
docker compose run --rm etl python -m src.ml_pipeline --model-path models/downtime_model.joblib
```

Open Streamlit:

```text
http://localhost:8501
```

---

### 9.12 Run Tests

```bash
pytest
```

With coverage:

```bash
pytest --cov=src --cov-report=term-missing
```

Expected minimum:

```text
60% coverage
```

---

### 9.13 Format and Lint

Format code:

```bash
black src tests
```

Lint code:

```bash
ruff check src tests
```

Auto-fix lint issues where safe:

```bash
ruff check src tests --fix
```

---

## 10. Known Limitations

This project intentionally has several limitations. These are documented clearly to make the project credible and transparent for portfolio review.

---

### 10.1 Data Limitations

| Limitation                      | Explanation                                                                                                                             |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| No confidential industrial data | The project does not use real employer machine data, production data, breakdown logs, or maintenance records.                           |
| Synthetic production records    | Production quantities, scrap, shifts, and maintenance records are generated and not collected from a real MES.                          |
| Public sample pattern only      | Public predictive maintenance sample structures are used as inspiration or optional seed data, not as proof of real factory deployment. |
| Simplified machine behavior     | Sensor relationships are realistic enough for portfolio demonstration but do not represent exact physics of industrial equipment.       |
| No real operator comments       | Breakdown descriptions and maintenance notes are synthetic.                                                                             |
| Limited data volume             | Two years of generated data is suitable for local demo, not industrial-scale big data benchmarking.                                     |

---

### 10.2 Architecture Limitations

| Limitation                        | Explanation                                                                                           |
| --------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Batch processing only             | The system does not implement real-time streaming with Kafka, MQTT, or OPC UA.                        |
| No direct PLC integration         | The project does not connect to PLCs, SCADA, historians, or industrial gateways.                      |
| No enterprise MES/SAP integration | Data is simulated and loaded from CSV/local generation rather than live ERP or MES systems.           |
| Optional Airflow only             | Airflow is included as an optional orchestration layer, not required for MVP.                         |
| Single-node PostgreSQL            | The project uses local PostgreSQL and does not include clustering, replication, or high availability. |
| Limited role-based access         | The dashboard does not include authentication, authorization, or user roles.                          |

---

### 10.3 Machine Learning Limitations

| Limitation                  | Explanation                                                                                                                       |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Prediction is demonstrative | Downtime prediction is designed to show ML pipeline capability, not to make safety-critical maintenance decisions.                |
| Synthetic labels            | Downtime labels are partially generated and may not reflect true industrial failure distributions.                                |
| Basic explainability        | Feature importance may be shown, but the project does not include advanced model explainability such as SHAP in the base version. |
| No online learning          | The model is trained in batch mode and does not update continuously.                                                              |
| No model monitoring         | The project does not include production drift detection, model registry, or automated retraining triggers.                        |

---

### 10.4 Dashboard Limitations

| Limitation             | Explanation                                                                            |
| ---------------------- | -------------------------------------------------------------------------------------- |
| Local demo dashboard   | Streamlit is intended for local portfolio demonstration, not enterprise BI deployment. |
| Limited concurrency    | The app is not optimized for many simultaneous users.                                  |
| Basic export only      | Data export is limited to Streamlit table download features.                           |
| No mobile-first design | The dashboard is primarily designed for desktop review.                                |

---

### 10.5 Operational Limitations

| Limitation                          | Explanation                                                                           |
| ----------------------------------- | ------------------------------------------------------------------------------------- |
| No cloud deployment in base version | The base project runs locally with Docker Compose.                                    |
| No secrets manager                  | Local `.env` files are used for development configuration.                            |
| No production SLA                   | The system is a portfolio project and does not define production support commitments. |
| Manual data refresh in MVP          | MVP refreshes are manually triggered unless optional Airflow is enabled.              |

---

## 11. Data Privacy Statement

This project is designed to be safe for a public GitHub portfolio. It does not contain confidential information from any employer, customer, industrial plant, machine program, PLC, MES, SAP system, maintenance database, or production environment.

The dataset strategy is:

1. Use public predictive maintenance sample dataset structures as a reference pattern.
2. Generate synthetic factory data for production, maintenance, breakdown, and additional sensor signals.
3. Use generic machine identifiers such as `MCH-001`, `MCH-002`, and generic line identifiers such as `LINE-01`.
4. Avoid real machine names, real production volumes, real downtime causes, real employees, real plant layouts, and real company-specific terminology.

This makes the project suitable for public demonstration while still showing practical industrial analytics knowledge.

---

## 12. Key Engineering Decisions

| Decision                     | Reason                                                                                       |
| ---------------------------- | -------------------------------------------------------------------------------------------- |
| PostgreSQL instead of SQLite | Demonstrates production-style relational database skills expected in data engineering roles. |
| Raw and analytics schemas    | Shows separation between ingestion and curated analytics layers.                             |
| SQL transformations          | Keeps KPI logic transparent and easy to validate.                                            |
| Streamlit dashboard          | Fast to build, recruiter-friendly, and easy to run locally.                                  |
| Docker Compose               | Makes the project reproducible for reviewers.                                                |
| Scikit-learn                 | Suitable for portfolio-level predictive maintenance model without unnecessary complexity.    |
| Public/synthetic data        | Protects confidentiality and improves public portfolio credibility.                          |
| GitHub Actions               | Demonstrates professional CI workflow.                                                       |
| pytest, ruff, black          | Shows software engineering discipline beyond notebook-style analysis.                        |

---

## 13. Dashboard Page Design

### Page 1: Executive Overview

Main questions answered:

* Is the factory performance improving or declining?
* Which machines have the lowest OEE?
* How much downtime occurred in the selected period?
* How many machines are currently high risk?

Visuals:

| Component            | Description                                                        |
| -------------------- | ------------------------------------------------------------------ |
| KPI Cards            | Average OEE, total downtime, total production, high-risk machines. |
| OEE Trend            | Daily OEE trend across all machines.                               |
| Downtime Trend       | Daily downtime trend.                                              |
| Worst Machines Table | Machines ranked by low OEE or high downtime.                       |

---

### Page 2: Machine KPIs

Main questions answered:

* Which machines have poor availability, performance, or quality?
* How does OEE change by machine, shift, and date?
* Is poor OEE caused by downtime, speed loss, or scrap?

Visuals:

| Component        | Description                                         |
| ---------------- | --------------------------------------------------- |
| Machine Selector | Filter specific machine.                            |
| OEE Breakdown    | Availability, performance, and quality percentages. |
| Production Trend | Planned vs actual vs good quantity.                 |
| Scrap Trend      | Scrap quantity and quality percentage.              |

---

### Page 3: Reliability

Main questions answered:

* Which machines fail most frequently?
* Which machines take longest to repair?
* Is maintenance compliance related to reliability?

Visuals:

| Component                    | Description                                   |
| ---------------------------- | --------------------------------------------- |
| MTBF Chart                   | MTBF by machine.                              |
| MTTR Chart                   | MTTR by machine.                              |
| Failure Count Trend          | Monthly failure count.                        |
| Maintenance Compliance Table | Scheduled vs completed vs missed maintenance. |

---

### Page 4: Downtime Pareto

Main questions answered:

* What are the top causes of downtime?
* Which machine and failure category combinations create the largest losses?
* Which 20% of causes contribute most downtime?

Visuals:

| Component               | Description                           |
| ----------------------- | ------------------------------------- |
| Pareto Bar Chart        | Downtime minutes by failure category. |
| Cumulative Line         | Cumulative downtime percentage.       |
| Failure Category Table  | Ranked failure categories.            |
| Machine-Failure Heatmap | Downtime by machine and category.     |

---

### Page 5: Predictive Downtime

Main questions answered:

* Which machines have high downtime risk?
* Are sensor anomalies increasing?
* Which machines should maintenance review first?

Visuals:

| Component               | Description                                |
| ----------------------- | ------------------------------------------ |
| Risk Cards              | High, medium, and low risk machine counts. |
| Risk Trend              | Downtime risk score over time.             |
| High-Risk Machine Table | Machines needing attention.                |
| Anomaly Chart           | Sensor anomaly score trend.                |
| Feature Summary         | Top model features or risk drivers.        |

---

## 14. KPI Definitions

### 14.1 Availability

```text
Availability = Runtime Minutes / Planned Production Minutes
```

Where:

```text
Runtime Minutes = Planned Production Minutes - Downtime Minutes
```

---

### 14.2 Performance

```text
Performance = (Ideal Cycle Time × Actual Quantity) / Runtime Time
```

Runtime time must be converted into seconds when ideal cycle time is stored in seconds.

---

### 14.3 Quality

```text
Quality = Good Quantity / Actual Quantity
```

---

### 14.4 Overall Equipment Effectiveness

```text
OEE = Availability × Performance × Quality
```

OEE is stored as a percentage in `analytics.machine_daily_kpi`.

---

### 14.5 MTBF

```text
MTBF = Operating Time / Number of Failures
```

Only unplanned breakdowns are included in the failure count.

---

### 14.6 MTTR

```text
MTTR = Total Repair Time / Number of Failures
```

Repair time is represented by unplanned downtime duration.

---

### 14.7 Maintenance Compliance

```text
Maintenance Compliance = Completed Maintenance Events / Scheduled Maintenance Events
```

---

## 15. Example SQL Transformation Strategy

### 15.1 Daily KPI Transformation

```sql
INSERT INTO analytics.machine_daily_kpi (
    machine_id,
    line_id,
    kpi_date,
    planned_production_minutes,
    runtime_minutes,
    downtime_minutes,
    planned_quantity,
    actual_quantity,
    good_quantity,
    scrap_quantity,
    availability_pct,
    performance_pct,
    quality_pct,
    oee_pct,
    created_at
)
SELECT
    p.machine_id,
    p.line_id,
    p.production_date AS kpi_date,
    SUM(p.planned_production_minutes) AS planned_production_minutes,
    SUM(p.actual_runtime_minutes) AS runtime_minutes,
    COALESCE(SUM(b.downtime_minutes), 0) AS downtime_minutes,
    SUM(p.planned_quantity) AS planned_quantity,
    SUM(p.actual_quantity) AS actual_quantity,
    SUM(p.good_quantity) AS good_quantity,
    SUM(p.scrap_quantity) AS scrap_quantity,
    CASE
        WHEN SUM(p.planned_production_minutes) > 0
        THEN SUM(p.actual_runtime_minutes) / SUM(p.planned_production_minutes) * 100
        ELSE 0
    END AS availability_pct,
    CASE
        WHEN SUM(p.actual_runtime_minutes) > 0
        THEN (
            SUM(p.ideal_cycle_time_seconds * p.actual_quantity)
            / (SUM(p.actual_runtime_minutes) * 60)
        ) * 100
        ELSE 0
    END AS performance_pct,
    CASE
        WHEN SUM(p.actual_quantity) > 0
        THEN SUM(p.good_quantity)::NUMERIC / SUM(p.actual_quantity) * 100
        ELSE 0
    END AS quality_pct,
    0 AS oee_pct,
    NOW() AS created_at
FROM raw.production_data p
LEFT JOIN raw.breakdown_logs b
    ON p.machine_id = b.machine_id
    AND p.production_date = DATE(b.breakdown_start)
    AND b.is_planned_stop = FALSE
GROUP BY
    p.machine_id,
    p.line_id,
    p.production_date
ON CONFLICT (machine_id, kpi_date)
DO UPDATE SET
    planned_production_minutes = EXCLUDED.planned_production_minutes,
    runtime_minutes = EXCLUDED.runtime_minutes,
    downtime_minutes = EXCLUDED.downtime_minutes,
    planned_quantity = EXCLUDED.planned_quantity,
    actual_quantity = EXCLUDED.actual_quantity,
    good_quantity = EXCLUDED.good_quantity,
    scrap_quantity = EXCLUDED.scrap_quantity,
    availability_pct = EXCLUDED.availability_pct,
    performance_pct = EXCLUDED.performance_pct,
    quality_pct = EXCLUDED.quality_pct,
    oee_pct = (
        EXCLUDED.availability_pct
        * EXCLUDED.performance_pct
        * EXCLUDED.quality_pct
    ) / 10000,
    created_at = NOW();
```

---

## 16. CI/CD Design

### GitHub Actions Workflow

```yaml
name: CI

on:
  push:
    branches:
      - main
  pull_request:

jobs:
  quality:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: smartfactory
          POSTGRES_PASSWORD: smartfactory
          POSTGRES_DB: smartfactory
        ports:
          - 5432:5432
        options: >-
          --health-cmd="pg_isready -U smartfactory"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=5

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run black check
        run: black --check src tests

      - name: Run ruff
        run: ruff check src tests

      - name: Run tests
        env:
          POSTGRES_HOST: localhost
          POSTGRES_PORT: 5432
          POSTGRES_DB: smartfactory
          POSTGRES_USER: smartfactory
          POSTGRES_PASSWORD: smartfactory
        run: pytest --cov=src --cov-report=term-missing
```

---

## 17. Portfolio Positioning

This project should be presented as:

> A privacy-safe industrial analytics platform inspired by real maintenance engineering experience and implemented using public/synthetic data. It demonstrates the ability to design data pipelines, model relational databases, calculate manufacturing KPIs, apply Python-based machine learning, and build business-facing dashboards.

Recommended recruiter-facing highlights:

| Skill Area                  | Evidence in Project                                                      |
| --------------------------- | ------------------------------------------------------------------------ |
| Data Engineering            | Raw and analytics schemas, ETL, SQL transformations, idempotent loading. |
| Python Development          | Modular package design, type hints, tests, linting, formatting.          |
| Industrial Domain Knowledge | OEE, MTBF, MTTR, downtime Pareto, preventive maintenance logic.          |
| Analytics Engineering       | KPI tables, dashboard-ready models, data quality checks.                 |
| Machine Learning            | Downtime risk prediction and anomaly detection.                          |
| DevOps Basics               | Docker Compose and GitHub Actions CI.                                    |
| Data Privacy Awareness      | Public/synthetic hybrid data and explicit privacy statement.             |

---

```
```
