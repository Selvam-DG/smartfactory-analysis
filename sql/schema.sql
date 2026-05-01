CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS analytics;

-- ============================================================
-- RAW AZURE PREDICTIVE MAINTENANCE STYLE TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS raw.azure_telemetry (
    telemetry_id BIGSERIAL PRIMARY KEY,
    datetime TIMESTAMPTZ,
    machineid INTEGER,
    volt NUMERIC(12, 4),
    rotate NUMERIC(12, 4),
    pressure NUMERIC(12, 4),
    vibration NUMERIC(12, 4),
    data_source TEXT DEFAULT 'azure_predictive_maintenance_sample',
    source_file TEXT DEFAULT 'PdM_telemetry.csv',
    ingested_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE raw.azure_telemetry IS
'Azure Predictive Maintenance sample-style telemetry readings used as public reference data for voltage, rotation, pressure, and vibration patterns.';

CREATE INDEX IF NOT EXISTS idx_azure_telemetry_machineid
    ON raw.azure_telemetry (machineid);

CREATE INDEX IF NOT EXISTS idx_azure_telemetry_datetime
    ON raw.azure_telemetry (datetime);

CREATE INDEX IF NOT EXISTS idx_azure_telemetry_machine_datetime
    ON raw.azure_telemetry (machineid, datetime);


CREATE TABLE IF NOT EXISTS raw.azure_errors (
    error_id BIGSERIAL PRIMARY KEY,
    datetime TIMESTAMPTZ,
    machineid INTEGER,
    errorid TEXT,
    data_source TEXT DEFAULT 'azure_predictive_maintenance_sample',
    source_file TEXT DEFAULT 'PdM_errors.csv',
    ingested_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE raw.azure_errors IS
'Azure Predictive Maintenance sample-style machine error events used as reference patterns for machine event behavior.';

CREATE INDEX IF NOT EXISTS idx_azure_errors_machineid
    ON raw.azure_errors (machineid);

CREATE INDEX IF NOT EXISTS idx_azure_errors_datetime
    ON raw.azure_errors (datetime);

CREATE INDEX IF NOT EXISTS idx_azure_errors_machine_datetime
    ON raw.azure_errors (machineid, datetime);


CREATE TABLE IF NOT EXISTS raw.azure_failures (
    failure_id BIGSERIAL PRIMARY KEY,
    datetime TIMESTAMPTZ,
    machineid INTEGER,
    failure TEXT,
    data_source TEXT DEFAULT 'azure_predictive_maintenance_sample',
    source_file TEXT DEFAULT 'PdM_failures.csv',
    ingested_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE raw.azure_failures IS
'Azure Predictive Maintenance sample-style failure records used as public reference labels for predictive maintenance modeling.';

CREATE INDEX IF NOT EXISTS idx_azure_failures_machineid
    ON raw.azure_failures (machineid);

CREATE INDEX IF NOT EXISTS idx_azure_failures_datetime
    ON raw.azure_failures (datetime);

CREATE INDEX IF NOT EXISTS idx_azure_failures_machine_datetime
    ON raw.azure_failures (machineid, datetime);


CREATE TABLE IF NOT EXISTS raw.azure_maintenance (
    maintenance_id BIGSERIAL PRIMARY KEY,
    datetime TIMESTAMPTZ,
    machineid INTEGER,
    comp TEXT,
    data_source TEXT DEFAULT 'azure_predictive_maintenance_sample',
    source_file TEXT DEFAULT 'PdM_maint.csv',
    ingested_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE raw.azure_maintenance IS
'Azure Predictive Maintenance sample-style component maintenance events used as reference maintenance history.';

CREATE INDEX IF NOT EXISTS idx_azure_maintenance_machineid
    ON raw.azure_maintenance (machineid);

CREATE INDEX IF NOT EXISTS idx_azure_maintenance_datetime
    ON raw.azure_maintenance (datetime);

CREATE INDEX IF NOT EXISTS idx_azure_maintenance_machine_datetime
    ON raw.azure_maintenance (machineid, datetime);


CREATE TABLE IF NOT EXISTS raw.azure_machines (
    machineid INTEGER PRIMARY KEY,
    model TEXT,
    age INTEGER,
    data_source TEXT DEFAULT 'azure_predictive_maintenance_sample',
    source_file TEXT DEFAULT 'PdM_machines.csv',
    ingested_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE raw.azure_machines IS
'Azure Predictive Maintenance sample-style machine metadata containing model and machine age.';

CREATE INDEX IF NOT EXISTS idx_azure_machines_model
    ON raw.azure_machines (model);

CREATE INDEX IF NOT EXISTS idx_azure_machines_age
    ON raw.azure_machines (age);


-- ============================================================
-- RAW SYNTHETIC SMARTFACTORY TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS raw.machine_sensor_data (
    sensor_id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    machine_id TEXT NOT NULL,
    machine_type TEXT NOT NULL,
    shift TEXT NOT NULL CHECK (shift IN ('A', 'B', 'C')),
    temperature_c NUMERIC(10, 2) NOT NULL,
    vibration_mm_s NUMERIC(10, 3) NOT NULL,
    motor_current_a NUMERIC(10, 2) NOT NULL,
    pressure_bar NUMERIC(10, 2) NOT NULL,
    speed_rpm NUMERIC(10, 2) NOT NULL,
    production_count INTEGER NOT NULL CHECK (production_count >= 0),
    anomaly_flag BOOLEAN NOT NULL DEFAULT FALSE,
    data_source TEXT NOT NULL DEFAULT 'synthetic_tyre_factory',
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_machine_sensor_timestamp UNIQUE (machine_id, timestamp)
);

COMMENT ON TABLE raw.machine_sensor_data IS
'Synthetic tyre manufacturing machine sensor readings for TBM, BA, CV, MX, and QC machines. Used for dashboarding, anomaly detection, and downtime prediction.';

CREATE INDEX IF NOT EXISTS idx_sensor_machine_id
    ON raw.machine_sensor_data (machine_id);

CREATE INDEX IF NOT EXISTS idx_sensor_timestamp
    ON raw.machine_sensor_data (timestamp);

CREATE INDEX IF NOT EXISTS idx_sensor_machine_timestamp
    ON raw.machine_sensor_data (machine_id, timestamp);


CREATE TABLE IF NOT EXISTS raw.breakdown_logs (
    log_id TEXT PRIMARY KEY,
    machine_id TEXT NOT NULL,
    failure_type TEXT NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    downtime_hours NUMERIC(10, 2) NOT NULL CHECK (downtime_hours >= 0),
    shift TEXT NOT NULL CHECK (shift IN ('A', 'B', 'C')),
    root_cause TEXT NOT NULL,
    action_taken TEXT NOT NULL,
    technician TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('Low', 'Medium', 'High', 'Critical')),
    spare_part_cost_eur NUMERIC(12, 2) NOT NULL CHECK (spare_part_cost_eur >= 0),
    data_source TEXT NOT NULL DEFAULT 'synthetic_tyre_factory',
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_breakdown_time_order CHECK (end_time >= start_time)
);

COMMENT ON TABLE raw.breakdown_logs IS
'Synthetic tyre manufacturing breakdown logs with failure type, root cause, action taken, technician, downtime, severity, and spare part cost.';

CREATE INDEX IF NOT EXISTS idx_breakdown_machine_id
    ON raw.breakdown_logs (machine_id);

CREATE INDEX IF NOT EXISTS idx_breakdown_start_time
    ON raw.breakdown_logs (start_time);

CREATE INDEX IF NOT EXISTS idx_breakdown_machine_start_time
    ON raw.breakdown_logs (machine_id, start_time);

CREATE INDEX IF NOT EXISTS idx_breakdown_failure_type
    ON raw.breakdown_logs (failure_type);


CREATE TABLE IF NOT EXISTS raw.production_data (
    production_id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    shift TEXT NOT NULL CHECK (shift IN ('A', 'B', 'C')),
    machine_id TEXT NOT NULL,
    product_type TEXT NOT NULL,
    operator_id TEXT NOT NULL,
    planned_qty INTEGER NOT NULL CHECK (planned_qty >= 0),
    actual_qty INTEGER NOT NULL CHECK (actual_qty >= 0),
    rejected_qty INTEGER NOT NULL CHECK (rejected_qty >= 0),
    good_qty INTEGER NOT NULL CHECK (good_qty >= 0),
    efficiency_pct NUMERIC(6, 2) NOT NULL CHECK (efficiency_pct >= 0),
    data_source TEXT NOT NULL DEFAULT 'synthetic_tyre_factory',
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_production_machine_date_shift UNIQUE (machine_id, date, shift),
    CONSTRAINT chk_good_qty_valid CHECK (good_qty <= actual_qty),
    CONSTRAINT chk_rejected_qty_valid CHECK (rejected_qty <= actual_qty)
);

COMMENT ON TABLE raw.production_data IS
'Synthetic shift-level tyre production data with planned quantity, actual quantity, rejected quantity, good quantity, and efficiency.';

CREATE INDEX IF NOT EXISTS idx_production_machine_id
    ON raw.production_data (machine_id);

CREATE INDEX IF NOT EXISTS idx_production_date
    ON raw.production_data (date);

CREATE INDEX IF NOT EXISTS idx_production_machine_date
    ON raw.production_data (machine_id, date);


CREATE TABLE IF NOT EXISTS raw.maintenance_schedule (
    task_id TEXT PRIMARY KEY,
    machine_id TEXT NOT NULL,
    maintenance_type TEXT NOT NULL,
    planned_date DATE NOT NULL,
    actual_date DATE NULL,
    technician TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('Planned', 'Completed', 'Overdue')),
    delay_days INTEGER NULL CHECK (delay_days IS NULL OR delay_days >= 0),
    notes TEXT NOT NULL,
    data_source TEXT NOT NULL DEFAULT 'synthetic_tyre_factory',
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE raw.maintenance_schedule IS
'Synthetic tyre factory maintenance schedule containing preventive maintenance and overhaul activities.';

CREATE INDEX IF NOT EXISTS idx_maintenance_machine_id
    ON raw.maintenance_schedule (machine_id);

CREATE INDEX IF NOT EXISTS idx_maintenance_planned_date
    ON raw.maintenance_schedule (planned_date);

CREATE INDEX IF NOT EXISTS idx_maintenance_machine_planned_date
    ON raw.maintenance_schedule (machine_id, planned_date);


-- ============================================================
-- ANALYTICS TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS analytics.machine_daily_kpi (
    kpi_id BIGSERIAL PRIMARY KEY,
    kpi_date DATE NOT NULL,
    machine_id TEXT NOT NULL,
    machine_type TEXT,
    planned_qty INTEGER NOT NULL DEFAULT 0,
    actual_qty INTEGER NOT NULL DEFAULT 0,
    good_qty INTEGER NOT NULL DEFAULT 0,
    rejected_qty INTEGER NOT NULL DEFAULT 0,
    downtime_hours NUMERIC(10, 2) NOT NULL DEFAULT 0,
    availability_pct NUMERIC(6, 2),
    performance_pct NUMERIC(6, 2),
    quality_pct NUMERIC(6, 2),
    oee_pct NUMERIC(6, 2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_machine_daily_kpi UNIQUE (machine_id, kpi_date)
);

COMMENT ON TABLE analytics.machine_daily_kpi IS
'Daily machine-level KPI table for production, downtime, availability, performance, quality, and OEE.';

CREATE INDEX IF NOT EXISTS idx_kpi_machine_id
    ON analytics.machine_daily_kpi (machine_id);

CREATE INDEX IF NOT EXISTS idx_kpi_date
    ON analytics.machine_daily_kpi (kpi_date);

CREATE INDEX IF NOT EXISTS idx_kpi_machine_date
    ON analytics.machine_daily_kpi (machine_id, kpi_date);


CREATE TABLE IF NOT EXISTS analytics.machine_reliability (
    reliability_id BIGSERIAL PRIMARY KEY,
    machine_id TEXT NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    failure_count INTEGER NOT NULL DEFAULT 0,
    total_downtime_hours NUMERIC(10, 2) NOT NULL DEFAULT 0,
    mtbf_hours NUMERIC(10, 2),
    mttr_hours NUMERIC(10, 2),
    maintenance_completed_count INTEGER NOT NULL DEFAULT 0,
    maintenance_overdue_count INTEGER NOT NULL DEFAULT 0,
    maintenance_compliance_pct NUMERIC(6, 2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_machine_reliability_period UNIQUE (machine_id, period_start, period_end)
);

COMMENT ON TABLE analytics.machine_reliability IS
'Machine reliability analytics table containing failure count, downtime, MTBF, MTTR, and maintenance compliance.';

CREATE INDEX IF NOT EXISTS idx_reliability_machine_id
    ON analytics.machine_reliability (machine_id);

CREATE INDEX IF NOT EXISTS idx_reliability_period
    ON analytics.machine_reliability (period_start, period_end);


CREATE TABLE IF NOT EXISTS analytics.downtime_pareto (
    pareto_id BIGSERIAL PRIMARY KEY,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    machine_id TEXT,
    failure_type TEXT NOT NULL,
    failure_count INTEGER NOT NULL DEFAULT 0,
    downtime_hours NUMERIC(10, 2) NOT NULL DEFAULT 0,
    downtime_pct NUMERIC(6, 2),
    cumulative_downtime_pct NUMERIC(6, 2),
    pareto_rank INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE analytics.downtime_pareto IS
'Pareto analysis table for ranking downtime contribution by machine and failure type.';

CREATE INDEX IF NOT EXISTS idx_pareto_machine_id
    ON analytics.downtime_pareto (machine_id);

CREATE INDEX IF NOT EXISTS idx_pareto_period
    ON analytics.downtime_pareto (period_start, period_end);

CREATE INDEX IF NOT EXISTS idx_pareto_failure_type
    ON analytics.downtime_pareto (failure_type);


CREATE TABLE IF NOT EXISTS analytics.downtime_predictions (
    prediction_id BIGSERIAL PRIMARY KEY,
    prediction_timestamp TIMESTAMPTZ NOT NULL,
    prediction_date DATE NOT NULL,
    machine_id TEXT NOT NULL,
    risk_score NUMERIC(6, 5) NOT NULL CHECK (risk_score >= 0 AND risk_score <= 1),
    risk_class TEXT NOT NULL CHECK (risk_class IN ('Low', 'Medium', 'High')),
    predicted_downtime_next_24h BOOLEAN NOT NULL,
    anomaly_score NUMERIC(10, 5),
    is_sensor_anomaly BOOLEAN NOT NULL DEFAULT FALSE,
    top_feature_1 TEXT,
    top_feature_2 TEXT,
    model_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE analytics.downtime_predictions IS
'ML prediction output table containing machine downtime risk score, risk class, anomaly flags, and model metadata.';

CREATE INDEX IF NOT EXISTS idx_predictions_machine_id
    ON analytics.downtime_predictions (machine_id);

CREATE INDEX IF NOT EXISTS idx_predictions_timestamp
    ON analytics.downtime_predictions (prediction_timestamp);

CREATE INDEX IF NOT EXISTS idx_predictions_machine_timestamp
    ON analytics.downtime_predictions (machine_id, prediction_timestamp);

CREATE INDEX IF NOT EXISTS idx_predictions_risk_class
    ON analytics.downtime_predictions (risk_class);