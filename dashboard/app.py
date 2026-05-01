# dashboard/app.py
"""
SmartFactory Reliability Analytics — Hybrid MVP Dashboard

Hybrid data strategy:
1. Synthetic tyre factory data:
   - TBM, BA, CV, MX, QC machines
   - production, breakdown, maintenance, sensor data
   - main KPI and reliability dashboard source

2. Azure Predictive Maintenance sample-style data:
   - optional public reference dataset
   - used for telemetry/failure pattern comparison
   - displayed only if analytics Azure views/tables exist

Dashboard rule:
- All dashboard queries read from analytics schema only.
- No dashboard query reads directly from raw schema.

MVP pages:
1. Factory Overview
2. Downtime Analysis
3. Machine Health Monitoring
4. Hybrid Data Sources
"""

from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from plotly.subplots import make_subplots
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError


# ============================================================
# App setup
# ============================================================

st.set_page_config(
    layout="wide",
    page_title="SmartFactory Analytics",
    page_icon="🏭",
)

load_dotenv()


# ============================================================
# Color scheme
# ============================================================

PRIMARY_BLUE = "#1f77b4"
ALERT_RED = "#d62728"
SUCCESS_GREEN = "#2ca02c"
WARNING_YELLOW = "#ffbf00"
ORANGE = "#ff7f0e"
GRAY = "#7f7f7f"


# ============================================================
# Database connection
# ============================================================

@st.cache_resource
def get_database_engine() -> Engine:
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError(
            "DATABASE_URL is missing. Example: "
            "postgresql+psycopg://smartfactory:smartfactory@localhost:5432/smartfactory"
        )

    return create_engine(
        database_url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        future=True,
    )


def run_query(query: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
    engine = get_database_engine()

    try:
        with engine.connect() as connection:
            return pd.read_sql(text(query), connection, params=params or {})
    except SQLAlchemyError as exc:
        st.warning(f"Query skipped or failed: {exc}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def analytics_object_exists(object_name: str) -> bool:
    """
    Checks whether analytics.<object_name> exists as a table or view.
    """
    query = """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'analytics'
              AND table_name = :object_name
        ) AS exists_flag;
    """

    df = run_query(query, {"object_name": object_name})

    if df.empty:
        return False

    return bool(df.loc[0, "exists_flag"])


# ============================================================
# Common helpers
# ============================================================

def apply_plotly_layout(fig: go.Figure, title: str | None = None) -> go.Figure:
    fig.update_layout(
        title=title,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(size=13),
        margin=dict(l=20, r=20, t=60, b=40),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridcolor="#eeeeee")
    fig.update_yaxes(showgrid=True, gridcolor="#eeeeee")
    return fig


def machine_filter_sql(machine_ids: list[str]) -> tuple[str, dict[str, Any]]:
    if not machine_ids:
        return "", {}

    placeholders = ", ".join([f":machine_{idx}" for idx in range(len(machine_ids))])
    params = {f"machine_{idx}": machine_id for idx, machine_id in enumerate(machine_ids)}

    return f" AND machine_id IN ({placeholders}) ", params


def health_score_style(value: Any) -> str:
    if pd.isna(value):
        return ""

    if value < 60:
        return "background-color: #f8d7da; color: #721c24;"
    if value < 80:
        return "background-color: #fff3cd; color: #856404;"

    return "background-color: #d4edda; color: #155724;"


# ============================================================
# Cached query functions — SmartFactory synthetic analytics
# ============================================================

@st.cache_data(ttl=300)
def load_available_machines() -> list[str]:
    query = """
        SELECT DISTINCT machine_id
        FROM analytics.machine_daily_kpi
        ORDER BY machine_id;
    """

    df = run_query(query)

    if df.empty:
        return []

    return df["machine_id"].dropna().tolist()


@st.cache_data(ttl=300)
def load_date_bounds() -> tuple[date, date]:
    query = """
        SELECT
            MIN(kpi_date) AS min_date,
            MAX(kpi_date) AS max_date
        FROM analytics.machine_daily_kpi;
    """

    df = run_query(query)

    if df.empty or pd.isna(df.loc[0, "min_date"]) or pd.isna(df.loc[0, "max_date"]):
        today = date.today()
        return today - timedelta(days=30), today

    return (
        pd.to_datetime(df.loc[0, "min_date"]).date(),
        pd.to_datetime(df.loc[0, "max_date"]).date(),
    )


@st.cache_data(ttl=300)
def load_kpi_data(
    start_date: date,
    end_date: date,
    machine_ids: list[str],
) -> pd.DataFrame:
    filter_sql, machine_params = machine_filter_sql(machine_ids)

    query = f"""
        SELECT
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
            anomaly_count
        FROM analytics.machine_daily_kpi
        WHERE kpi_date BETWEEN :start_date AND :end_date
        {filter_sql}
        ORDER BY kpi_date, machine_id;
    """

    params = {
        "start_date": start_date,
        "end_date": end_date,
        **machine_params,
    }

    return run_query(query, params)


@st.cache_data(ttl=300)
def load_reliability_data(machine_ids: list[str]) -> pd.DataFrame:
    filter_sql, machine_params = machine_filter_sql(machine_ids)

    query = f"""
        SELECT
            machine_id,
            period_start,
            period_end,
            COALESCE(total_failures, failure_count) AS total_failures,
            total_downtime_hours,
            total_operating_hours,
            mtbf_hours,
            mttr_hours,
            availability_pct,
            health_score,
            maintenance_completed_count,
            maintenance_overdue_count,
            maintenance_compliance_pct
        FROM analytics.machine_reliability
        WHERE 1 = 1
        {filter_sql}
        ORDER BY health_score ASC NULLS LAST, total_downtime_hours DESC;
    """

    return run_query(query, machine_params)


@st.cache_data(ttl=300)
def load_pareto_data() -> pd.DataFrame:
    query = """
        SELECT
            failure_type,
            failure_count,
            downtime_hours,
            downtime_pct,
            cumulative_downtime_pct,
            pareto_rank
        FROM analytics.downtime_pareto
        ORDER BY pareto_rank;
    """

    return run_query(query)


@st.cache_data(ttl=300)
def load_sensor_monitoring_data(
    machine_id: str,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """
    Preferred analytics source for Page 3.

    Expected optional analytics view/table:
        analytics.machine_sensor_monitoring

    If it does not exist, fallback uses daily sensor averages from:
        analytics.machine_daily_kpi
    """
    if analytics_object_exists("machine_sensor_monitoring"):
        query = """
            SELECT
                timestamp,
                machine_id,
                temperature_c,
                vibration_mm_s,
                motor_current_a,
                anomaly_flag
            FROM analytics.machine_sensor_monitoring
            WHERE machine_id = :machine_id
              AND DATE(timestamp) BETWEEN :start_date AND :end_date
            ORDER BY timestamp;
        """

        return run_query(
            query,
            {
                "machine_id": machine_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

    query = """
        SELECT
            kpi_date AS timestamp,
            machine_id,
            avg_temperature_c AS temperature_c,
            avg_vibration_mm_s AS vibration_mm_s,
            avg_motor_current_a AS motor_current_a,
            CASE WHEN COALESCE(anomaly_count, 0) > 0 THEN TRUE ELSE FALSE END AS anomaly_flag
        FROM analytics.machine_daily_kpi
        WHERE machine_id = :machine_id
          AND kpi_date BETWEEN :start_date AND :end_date
        ORDER BY kpi_date;
    """

    return run_query(
        query,
        {
            "machine_id": machine_id,
            "start_date": start_date,
            "end_date": end_date,
        },
    )


@st.cache_data(ttl=300)
def load_downtime_by_shift(
    start_date: date,
    end_date: date,
    machine_ids: list[str],
) -> pd.DataFrame:
    """
    Optional analytics source:
        analytics.downtime_by_shift

    If unavailable, the dashboard shows a friendly message.
    """
    if not analytics_object_exists("downtime_by_shift"):
        return pd.DataFrame()

    filter_sql, machine_params = machine_filter_sql(machine_ids)

    query = f"""
        SELECT
            shift,
            SUM(downtime_hours) AS downtime_hours
        FROM analytics.downtime_by_shift
        WHERE downtime_date BETWEEN :start_date AND :end_date
        {filter_sql}
        GROUP BY shift
        ORDER BY shift;
    """

    params = {
        "start_date": start_date,
        "end_date": end_date,
        **machine_params,
    }

    return run_query(query, params)


# ============================================================
# Cached query functions — Azure PM reference analytics
# ============================================================

@st.cache_data(ttl=300)
def load_azure_telemetry_daily() -> pd.DataFrame:
    """
    Optional Azure PM analytics source.

    Expected table/view:
        analytics.azure_telemetry_daily

    Suggested columns:
        telemetry_date,
        machineid,
        avg_volt,
        avg_rotate,
        avg_pressure,
        avg_vibration
    """
    if not analytics_object_exists("azure_telemetry_daily"):
        return pd.DataFrame()

    query = """
        SELECT
            telemetry_date,
            machineid,
            avg_volt,
            avg_rotate,
            avg_pressure,
            avg_vibration
        FROM analytics.azure_telemetry_daily
        ORDER BY telemetry_date, machineid;
    """

    return run_query(query)


@st.cache_data(ttl=300)
def load_azure_failure_summary() -> pd.DataFrame:
    """
    Optional Azure PM analytics source.

    Expected table/view:
        analytics.azure_failure_summary

    Suggested columns:
        failure,
        failure_count
    """
    if not analytics_object_exists("azure_failure_summary"):
        return pd.DataFrame()

    query = """
        SELECT
            failure,
            failure_count
        FROM analytics.azure_failure_summary
        ORDER BY failure_count DESC;
    """

    return run_query(query)


@st.cache_data(ttl=300)
def load_hybrid_data_inventory() -> pd.DataFrame:
    """
    Optional hybrid inventory view.

    Expected table/view:
        analytics.hybrid_data_inventory

    Suggested columns:
        layer,
        dataset_name,
        data_source,
        row_count
    """
    if not analytics_object_exists("hybrid_data_inventory"):
        return pd.DataFrame()

    query = """
        SELECT
            layer,
            dataset_name,
            data_source,
            row_count
        FROM analytics.hybrid_data_inventory
        ORDER BY layer, dataset_name;
    """

    return run_query(query)


# ============================================================
# Sidebar
# ============================================================

def render_sidebar() -> tuple[str, date, date, list[str]]:
    st.sidebar.title("🏭 SmartFactory")
    st.sidebar.caption("Hybrid Reliability Analytics")

    page = st.sidebar.radio(
        "Page",
        [
            "1 — Factory Overview",
            "2 — Downtime Analysis",
            "3 — Machine Health Monitoring",
            "4 — Hybrid Data Sources",
        ],
    )

    min_date, max_date = load_date_bounds()

    selected_range = st.sidebar.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    if isinstance(selected_range, tuple) and len(selected_range) == 2:
        start_date, end_date = selected_range
    else:
        start_date, end_date = min_date, max_date

    machines = load_available_machines()

    selected_machines = st.sidebar.multiselect(
        "Machines",
        options=machines,
        default=machines,
    )

    st.sidebar.divider()
    st.sidebar.markdown("### Data strategy")
    st.sidebar.caption("Synthetic tyre-factory data: main MVP analytics")
    st.sidebar.caption("Azure PM sample-style data: optional public reference")
    st.sidebar.caption("Dashboard reads analytics schema only")

    return page, start_date, end_date, selected_machines


# ============================================================
# Page 1 — Factory Overview
# ============================================================

def render_metric_cards(kpi_df: pd.DataFrame) -> None:
    if kpi_df.empty:
        st.warning("No KPI data available for the selected filters.")
        return

    avg_oee = kpi_df["oee_pct"].mean()
    avg_availability = kpi_df["availability_pct"].mean()
    avg_quality = kpi_df["quality_pct"].mean()
    total_production = kpi_df["good_qty"].sum()
    total_downtime = kpi_df["downtime_hours"].sum()
    active_machines = kpi_df["machine_id"].nunique()

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    col1.metric("OEE %", f"{avg_oee:.1f}%")
    col2.metric("Availability %", f"{avg_availability:.1f}%")
    col3.metric("Quality Rate %", f"{avg_quality:.1f}%")
    col4.metric("Total Production", f"{total_production:,.0f}")
    col5.metric("Total Downtime", f"{total_downtime:,.1f} h")
    col6.metric("Active Machines", f"{active_machines}")


def render_daily_oee_trend(kpi_df: pd.DataFrame) -> None:
    daily_df = (
        kpi_df.groupby("kpi_date", as_index=False)
        .agg(oee_pct=("oee_pct", "mean"))
        .sort_values("kpi_date")
    )

    fig = px.line(
        daily_df,
        x="kpi_date",
        y="oee_pct",
        markers=True,
        title="Daily OEE — Target: 85%",
    )

    fig.update_traces(line=dict(color=PRIMARY_BLUE, width=3))

    fig.add_hline(
        y=85,
        line_dash="dash",
        line_color=SUCCESS_GREEN,
        annotation_text="85% target",
        annotation_position="top left",
    )

    fig.update_yaxes(title="OEE %", range=[0, 110])
    fig.update_xaxes(title="Date")

    st.plotly_chart(apply_plotly_layout(fig), use_container_width=True)


def render_top_downtime_machines(kpi_df: pd.DataFrame) -> None:
    downtime_df = (
        kpi_df.groupby("machine_id", as_index=False)
        .agg(downtime_hours=("downtime_hours", "sum"))
        .sort_values("downtime_hours", ascending=False)
        .head(5)
    )

    fig = px.bar(
        downtime_df,
        x="downtime_hours",
        y="machine_id",
        orientation="h",
        color="downtime_hours",
        color_continuous_scale="Reds",
        title="Top 5 Machines by Downtime Hours",
    )

    fig.update_layout(yaxis=dict(autorange="reversed"))
    fig.update_xaxes(title="Downtime Hours")
    fig.update_yaxes(title="Machine")

    st.plotly_chart(apply_plotly_layout(fig), use_container_width=True)


def render_machine_health_table(reliability_df: pd.DataFrame) -> None:
    st.subheader("Machine Health Table")

    if reliability_df.empty:
        st.warning("No machine reliability data available.")
        return

    display_cols = [
        "machine_id",
        "total_failures",
        "total_downtime_hours",
        "mtbf_hours",
        "mttr_hours",
        "availability_pct",
        "maintenance_compliance_pct",
        "health_score",
    ]

    existing_cols = [col for col in display_cols if col in reliability_df.columns]

    styled_df = (
        reliability_df[existing_cols]
        .style
        .format(
            {
                "total_downtime_hours": "{:.1f}",
                "mtbf_hours": "{:.1f}",
                "mttr_hours": "{:.1f}",
                "availability_pct": "{:.1f}",
                "maintenance_compliance_pct": "{:.1f}",
                "health_score": "{:.1f}",
            },
            na_rep="N/A",
        )
        .map(health_score_style, subset=["health_score"])
    )

    st.dataframe(styled_df, use_container_width=True, hide_index=True)


def render_factory_overview(
    start_date: date,
    end_date: date,
    selected_machines: list[str],
) -> None:
    st.title("🏭 Factory Overview")
    st.caption("Synthetic tyre-factory KPI layer with public Azure PM data available as optional reference.")

    kpi_df = load_kpi_data(start_date, end_date, selected_machines)
    reliability_df = load_reliability_data(selected_machines)

    render_metric_cards(kpi_df)

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        if not kpi_df.empty:
            render_daily_oee_trend(kpi_df)

    with col2:
        if not kpi_df.empty:
            render_top_downtime_machines(kpi_df)

    st.divider()

    render_machine_health_table(reliability_df)


# ============================================================
# Page 2 — Downtime Analysis
# ============================================================

def render_mtbf_chart(reliability_df: pd.DataFrame) -> None:
    if reliability_df.empty:
        st.warning("No MTBF data available.")
        return

    df = reliability_df.sort_values("mtbf_hours", ascending=False)

    fig = px.bar(
        df,
        x="machine_id",
        y="mtbf_hours",
        title="MTBF per Machine — Higher is Better",
    )

    fig.update_traces(marker_color=SUCCESS_GREEN)
    fig.update_xaxes(title="Machine")
    fig.update_yaxes(title="MTBF Hours")

    st.plotly_chart(apply_plotly_layout(fig), use_container_width=True)


def render_mttr_chart(reliability_df: pd.DataFrame) -> None:
    if reliability_df.empty:
        st.warning("No MTTR data available.")
        return

    df = reliability_df.sort_values("mttr_hours", ascending=True)

    fig = px.bar(
        df,
        x="machine_id",
        y="mttr_hours",
        title="MTTR per Machine — Lower is Better",
    )

    fig.update_traces(marker_color=ALERT_RED)
    fig.update_xaxes(title="Machine")
    fig.update_yaxes(title="MTTR Hours")

    st.plotly_chart(apply_plotly_layout(fig), use_container_width=True)


def render_pareto_chart(pareto_df: pd.DataFrame) -> None:
    st.subheader("Downtime Pareto by Failure Type")

    if pareto_df.empty:
        st.warning("No Pareto data available.")
        return

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=pareto_df["failure_type"],
            y=pareto_df["downtime_hours"],
            name="Downtime Hours",
            marker_color=PRIMARY_BLUE,
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=pareto_df["failure_type"],
            y=pareto_df["cumulative_downtime_pct"],
            name="Cumulative %",
            mode="lines+markers",
            line=dict(color=ORANGE, width=3),
            marker=dict(size=8),
        ),
        secondary_y=True,
    )

    fig.add_hline(
        y=80,
        line_dash="dash",
        line_color=ORANGE,
        annotation_text="80%",
        annotation_position="top left",
        secondary_y=True,
    )

    fig.update_xaxes(title="Failure Type")
    fig.update_yaxes(title="Downtime Hours", secondary_y=False)
    fig.update_yaxes(title="Cumulative %", range=[0, 110], secondary_y=True)

    fig.update_layout(
        title="Pareto Chart — Downtime Hours and Cumulative %",
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=20, r=20, t=60, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )

    st.plotly_chart(fig, use_container_width=True)


def render_downtime_shift_pie(
    start_date: date,
    end_date: date,
    selected_machines: list[str],
) -> None:
    shift_df = load_downtime_by_shift(start_date, end_date, selected_machines)

    if shift_df.empty:
        st.info(
            "Shift-level downtime analytics are not available yet. "
            "Create analytics.downtime_by_shift in V2 to enable this chart."
        )
        return

    fig = px.pie(
        shift_df,
        names="shift",
        values="downtime_hours",
        title="Downtime distribution by shift",
        color_discrete_sequence=[PRIMARY_BLUE, ORANGE, ALERT_RED],
    )

    st.plotly_chart(apply_plotly_layout(fig), use_container_width=True)


def render_downtime_analysis(
    start_date: date,
    end_date: date,
    selected_machines: list[str],
) -> None:
    st.title("🛠️ Downtime Analysis")
    st.caption("Reliability, repair time, and failure concentration from the analytics layer.")

    reliability_df = load_reliability_data(selected_machines)
    pareto_df = load_pareto_data()

    col1, col2 = st.columns(2)

    with col1:
        render_mtbf_chart(reliability_df)

    with col2:
        render_mttr_chart(reliability_df)

    st.divider()

    render_pareto_chart(pareto_df)

    st.divider()

    render_downtime_shift_pie(start_date, end_date, selected_machines)


# ============================================================
# Page 3 — Machine Health Monitoring
# ============================================================

def render_latest_sensor_metrics(sensor_df: pd.DataFrame) -> None:
    if sensor_df.empty:
        st.warning("No sensor monitoring data available.")
        return

    latest = sensor_df.sort_values("timestamp").iloc[-1]

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Latest Temperature",
        f"{latest['temperature_c']:.1f} °C" if pd.notna(latest["temperature_c"]) else "N/A",
    )
    col2.metric(
        "Latest Vibration",
        f"{latest['vibration_mm_s']:.2f} mm/s" if pd.notna(latest["vibration_mm_s"]) else "N/A",
    )
    col3.metric(
        "Latest Motor Current",
        f"{latest['motor_current_a']:.1f} A" if pd.notna(latest["motor_current_a"]) else "N/A",
    )


def add_trend_with_anomalies(
    fig: go.Figure,
    df: pd.DataFrame,
    y_col: str,
    row: int,
    name: str,
    y_title: str,
) -> None:
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df[y_col],
            mode="lines",
            name=name,
            line=dict(color=PRIMARY_BLUE, width=2),
        ),
        row=row,
        col=1,
    )

    anomaly_df = df[df["anomaly_flag"] == True]  # noqa: E712

    if not anomaly_df.empty:
        fig.add_trace(
            go.Scatter(
                x=anomaly_df["timestamp"],
                y=anomaly_df[y_col],
                mode="markers",
                name=f"{name} anomaly",
                marker=dict(color=ALERT_RED, size=8),
            ),
            row=row,
            col=1,
        )

    fig.update_yaxes(title_text=y_title, row=row, col=1)


def render_sensor_subplot(sensor_df: pd.DataFrame, machine_id: str) -> None:
    if sensor_df.empty:
        return

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=[
            "Temperature Trend",
            "Vibration Trend",
            "Motor Current Trend",
        ],
    )

    add_trend_with_anomalies(fig, sensor_df, "temperature_c", 1, "Temperature", "°C")
    add_trend_with_anomalies(fig, sensor_df, "vibration_mm_s", 2, "Vibration", "mm/s")
    add_trend_with_anomalies(fig, sensor_df, "motor_current_a", 3, "Motor Current", "A")

    fig.update_layout(
        title=f"Machine Health Trends — {machine_id}",
        height=800,
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=20, r=20, t=80, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )

    fig.update_xaxes(showgrid=True, gridcolor="#eeeeee")
    fig.update_yaxes(showgrid=True, gridcolor="#eeeeee")

    st.plotly_chart(fig, use_container_width=True)


def render_last_24_hours_table(sensor_df: pd.DataFrame) -> None:
    st.subheader("Last 24 Hours Sensor Data")

    if sensor_df.empty:
        st.warning("No sensor data available.")
        return

    sensor_df["timestamp"] = pd.to_datetime(sensor_df["timestamp"])
    max_timestamp = sensor_df["timestamp"].max()
    cutoff = max_timestamp - pd.Timedelta(hours=24)

    last_24h_df = sensor_df[sensor_df["timestamp"] >= cutoff].copy()

    if last_24h_df.empty:
        last_24h_df = sensor_df.tail(24).copy()

    display_cols = [
        "timestamp",
        "machine_id",
        "temperature_c",
        "vibration_mm_s",
        "motor_current_a",
        "anomaly_flag",
    ]

    st.dataframe(
        last_24h_df[display_cols].sort_values("timestamp", ascending=False),
        use_container_width=True,
        hide_index=True,
    )


def render_machine_health_monitoring(
    start_date: date,
    end_date: date,
    selected_machines: list[str],
) -> None:
    st.title("📈 Machine Health Monitoring")
    st.caption("Synthetic machine condition monitoring from analytics-level sensor features.")

    if not selected_machines:
        st.warning("Select at least one machine in the sidebar.")
        return

    machine_id = st.selectbox("Select machine", selected_machines)

    sensor_df = load_sensor_monitoring_data(machine_id, start_date, end_date)

    if not analytics_object_exists("machine_sensor_monitoring"):
        st.info(
            "Using daily sensor averages from analytics.machine_daily_kpi. "
            "For true hourly monitoring, create analytics.machine_sensor_monitoring."
        )

    if not sensor_df.empty:
        sensor_df["timestamp"] = pd.to_datetime(sensor_df["timestamp"])

    render_latest_sensor_metrics(sensor_df)

    st.divider()

    render_sensor_subplot(sensor_df, machine_id)

    st.divider()

    render_last_24_hours_table(sensor_df)


# ============================================================
# Page 4 — Hybrid Data Sources
# ============================================================

def render_hybrid_inventory() -> None:
    st.subheader("Hybrid Data Inventory")

    inventory_df = load_hybrid_data_inventory()

    if inventory_df.empty:
        st.info(
            "analytics.hybrid_data_inventory is not available yet. "
            "This optional view can summarize row counts for Azure PM and synthetic datasets."
        )

        fallback = pd.DataFrame(
            [
                {
                    "layer": "analytics",
                    "dataset_name": "machine_daily_kpi",
                    "data_source": "synthetic_tyre_factory",
                    "status": "required MVP table",
                },
                {
                    "layer": "analytics",
                    "dataset_name": "machine_reliability",
                    "data_source": "synthetic_tyre_factory",
                    "status": "required MVP table",
                },
                {
                    "layer": "analytics",
                    "dataset_name": "downtime_pareto",
                    "data_source": "synthetic_tyre_factory",
                    "status": "required MVP table",
                },
                {
                    "layer": "analytics",
                    "dataset_name": "azure_telemetry_daily",
                    "data_source": "azure_predictive_maintenance_sample",
                    "status": "optional reference view",
                },
                {
                    "layer": "analytics",
                    "dataset_name": "azure_failure_summary",
                    "data_source": "azure_predictive_maintenance_sample",
                    "status": "optional reference view",
                },
            ]
        )

        st.dataframe(fallback, use_container_width=True, hide_index=True)
        return

    st.dataframe(inventory_df, use_container_width=True, hide_index=True)


def render_azure_telemetry_reference() -> None:
    st.subheader("Azure PM Telemetry Reference")

    azure_df = load_azure_telemetry_daily()

    if azure_df.empty:
        st.info(
            "No analytics.azure_telemetry_daily view/table found. "
            "Add this analytics view if you want to visualize public Azure PM telemetry patterns."
        )
        return

    metric = st.selectbox(
        "Azure telemetry metric",
        ["avg_volt", "avg_rotate", "avg_pressure", "avg_vibration"],
    )

    fig = px.line(
        azure_df,
        x="telemetry_date",
        y=metric,
        color="machineid",
        title=f"Azure PM Daily Telemetry Reference — {metric}",
    )

    st.plotly_chart(apply_plotly_layout(fig), use_container_width=True)


def render_azure_failure_reference() -> None:
    st.subheader("Azure PM Failure Reference")

    failure_df = load_azure_failure_summary()

    if failure_df.empty:
        st.info(
            "No analytics.azure_failure_summary view/table found. "
            "Add this analytics view if you want to compare public sample failure patterns."
        )
        return

    fig = px.bar(
        failure_df,
        x="failure",
        y="failure_count",
        title="Azure PM Failure Summary",
    )

    fig.update_traces(marker_color=ORANGE)
    fig.update_xaxes(title="Failure")
    fig.update_yaxes(title="Failure Count")

    st.plotly_chart(apply_plotly_layout(fig), use_container_width=True)


def render_hybrid_data_sources() -> None:
    st.title("🔗 Hybrid Data Sources")
    st.caption(
        "This project combines public Azure Predictive Maintenance sample-style data "
        "with synthetic tyre-factory data inspired by industrial automation experience."
    )

    col1, col2, col3 = st.columns(3)

    col1.metric("Synthetic source", "Tyre factory")
    col2.metric("Public reference", "Azure PM")
    col3.metric("Dashboard layer", "analytics schema")

    st.divider()

    render_hybrid_inventory()

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        render_azure_telemetry_reference()

    with col2:
        render_azure_failure_reference()


# ============================================================
# Main
# ============================================================

def main() -> None:
    page, start_date, end_date, selected_machines = render_sidebar()

    if start_date > end_date:
        st.error("Start date must be before end date.")
        return

    if page == "1 — Factory Overview":
        render_factory_overview(start_date, end_date, selected_machines)

    elif page == "2 — Downtime Analysis":
        render_downtime_analysis(start_date, end_date, selected_machines)

    elif page == "3 — Machine Health Monitoring":
        render_machine_health_monitoring(start_date, end_date, selected_machines)

    elif page == "4 — Hybrid Data Sources":
        render_hybrid_data_sources()


if __name__ == "__main__":
    main()