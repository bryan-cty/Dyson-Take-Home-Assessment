# Telemetry & Product Data Analysis

Take-home assessment for Dyson's **Data Analytics & Insights Engineer** role.

This project compares Normal and Return/Repair machines using cleaning sessions, fault records, battery readings and motor readings.

## Dashboard

Download [telemetry_dashboard.html](outputs/telemetry_dashboard.html) and open it in a browser. It works offline and includes four interactive charts:

- Cleaning duration
- Recorded faults
- Battery power mix
- Motor power mix

Use the group selector to compare both groups or view one group. Hover over the charts for values and sample sizes.

## Project files

- [fr.ipynb](fr.ipynb): notebook with data checks, session preparation and fault analysis.
- `inputs/`: input CSV files.
- `outputs/`: prepared data and the HTML dashboard.
- `dashboard/`: dashboard template, build script and checks.

## Rebuild the dashboard

From the project folder, run:

```bash
python -m pip install pandas numpy plotly
python dashboard/build_dashboard.py
```

The build reads the prepared `sessions.csv`, `battery_changes.csv` and `motor_changes.csv` files in `outputs/`. It checks the report figures and generates the HTML without running the notebook or changing the source data.

Optional interaction checks require Node.js:

```bash
node dashboard/check_dashboard.cjs
```

## Key findings

| Measure | Normal | Return/Repair |
|---|---:|---:|
| Eligible sessions lasting 10–60 minutes | 12.90% | 16.27% |
| Sessions with recorded blockage | 1.43% | 3.72% |
| Battery usage increase in Power 3 | 2.51% | 18.87% |
| Motor usage increase at 300–400 W | 9.26% | 16.04% |
