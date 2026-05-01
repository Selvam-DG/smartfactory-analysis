# SmartFactory Reliability Analytics 

![Python](https://img.shields.io/badge/Python-3.11-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-red)
![Docker](https://img.shields.io/badge/Docker-Compose-blue)

SmartFactory Reliability Analytics is a privacy-safe industrial data engineering and analytics portfolio project. It combines Azure Predictive Maintenance sample-style public data patterns with synthetic tyre manufacturing data inspired by real automation experience on TBM, Bead Apexing, Curing, Mixing, and Quality machines. The project demonstrates Python ETL, PostgreSQL analytics modeling, reliability KPIs, OEE, downtime analysis, and a Streamlit dashboard for Data Engineer / Python Developer roles.

---

## Architecture

```mermaid
flowchart LR
    A[Azure PM Sample-Style Data] --> C[Raw PostgreSQL Schema]
    B[Synthetic Tyre Factory Data] --> C
    C --> D[ETL + Validation]
    D --> E[Analytics PostgreSQL Schema]
    E --> F[Streamlit Dashboard]
    E --> G[Future ML Pipeline]
````

---

## Quick Start

```bash
git clone https://github.com/Selvam-DG/smartfactory-analysis.git
cd smartfactory-reliability-analytics
cp .env.example .env
make db-start
make db-init
make etl
make dashboard
```

---

## Tech Stack

| Area             | Tools                                                                 |
| ---------------- | --------------------------------------------------------------------- |
| Language         | Python 3.11                                                           |
| Database         | PostgreSQL 15                                                         |
| Database Access  | SQLAlchemy, psycopg2                                                  |
| Data Processing  | pandas, NumPy                                                         |
| Dashboard        | Streamlit, Plotly                                                     |
| Containerization | Docker, Docker Compose                                                |
| Testing          | pytest, pytest-cov                                                    |
| Code Quality     | ruff, black                                                           |
| CI               | GitHub Actions                                                        |
| Data Strategy    | Azure PM sample-style public data + synthetic tyre manufacturing data |

---

## MVP Features

| Feature                              | Status  |
| ------------------------------------ | ------- |
| Synthetic industrial data generator  | Done    |
| Azure PM sample-style data support   | Done    |
| PostgreSQL raw schema                | Done    |
| ETL validation and loading           | Done    |
| Analytics KPI tables                 | Done    |
| 3-page Streamlit dashboard           | Done    |
| Automated tests                      | Done    |
| GitHub Actions CI                    | Done    |
| ML downtime prediction               | Planned |
| Advanced Pareto and prediction pages | Planned |

---

## Screenshots

Screenshots coming soon.

```text
docs/screenshots/
├── factory_overview.png
├── downtime_analysis.png
└── machine_health_monitoring.png
```

---

## Data Privacy

This project does not use confidential employer, customer, machine, PLC, MES, SAP, or production data. The dataset is built using public Azure Predictive Maintenance sample-style structures and synthetic tyre factory data generated for portfolio demonstration.

---

## Portfolio Positioning

This project is designed to show practical capability in:

* Industrial data engineering
* Python backend/data pipeline development
* PostgreSQL schema design
* Manufacturing KPI modeling
* Reliability analytics
* Streamlit dashboarding
* Testing, linting, CI, and Docker-based local development


---

