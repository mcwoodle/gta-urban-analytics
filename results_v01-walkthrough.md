# YRP Crime Data Analysis — Walkthrough

## What Was Done

Created [analyze_crime_data.py](file:///c:/Users/woodl/workspace/crime-data/analyze_crime_data.py) that processes **177,331** crime occurrence records (2021–2025) and produces **23 CSV files** in [results/](file:///c:/Users/woodl/workspace/crime-data/results/).

Every analysis is output in two versions:
- **`all_*`** — unfiltered (all incidents)
- **`filtered_*`** — anomaly locations removed (500m radius around 18 locations: malls, hospitals, GO stations, Canada's Wonderland)

## Key Findings

### Total Incidents by Municipality (Unfiltered)

| Municipality | 2021 | 2022 | 2023 | 2024 | Total |
|---|---|---|---|---|---|
| Vaughan | 11,825 | 14,493 | 16,839 | 15,724 | 58,958 |
| Markham | 8,262 | 9,874 | 11,561 | 10,509 | 40,266 |
| Richmond Hill | 5,864 | 6,997 | 8,425 | 8,173 | 29,496 |
| Newmarket | 3,346 | 3,871 | 4,626 | 4,651 | 16,507 |
| Georgina | 2,196 | 2,141 | 2,511 | 2,413 | 9,273 |

> [!IMPORTANT]
> 2025 data is minimal (only 77–13 records per municipality), suggesting early-year partial data.

### Per-Capita Rates Tell a Different Story (incidents per 1,000 residents)

| Municipality | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|
| **Georgina** | **46.1** | **44.9** | **52.7** | **50.7** |
| Newmarket | 38.1 | 44.0 | 52.6 | 52.9 |
| Vaughan | 36.6 | 44.9 | 52.1 | 48.7 |
| King | 35.4 | 37.1 | 40.4 | 42.1 |
| East Gwillimbury | 32.3 | 31.9 | 42.6 | 44.5 |
| Richmond Hill | 29.0 | 34.6 | 41.7 | 40.5 |
| Aurora | 28.0 | 30.3 | 36.7 | 37.8 |
| Markham | 24.4 | 29.2 | 34.2 | 31.1 |
| **Whitchurch-Stouffville** | **23.7** | **25.1** | **28.6** | **24.6** |

Georgina has the **highest** per-capita rate. Whitchurch-Stouffville has the **lowest**. Markham and Vaughan, despite having the most raw incidents, are mid-range per-capita.

### Violent Crime Rate per 1,000 (filtered)

| Municipality | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|
| **Georgina** | **2.94** | **3.63** | **5.54** | **4.51** |
| Newmarket | 1.75 | 2.40 | 3.45 | 2.80 |
| Vaughan | 1.86 | 2.49 | 2.71 | 2.54 |
| East Gwillimbury | 1.67 | 1.93 | 2.28 | 3.55 |
| W-Stouffville | 1.14 | 1.42 | 1.46 | 1.60 |

### Anomaly Location Impact

| Municipality | Incidents Removed | % of Total |
|---|---|---|
| Newmarket | 2,684 | **16.3%** |
| Markham | 5,098 | 12.7% |
| Richmond Hill | 2,964 | 10.0% |
| Vaughan | 5,735 | 9.7% |
| Aurora | 542 | 6.6% |

> [!NOTE]
> Georgina, King, East Gwillimbury, and Whitchurch-Stouffville had no anomaly-adjacent incidents flagged (no major malls/hospitals in their areas within this dataset).

### Clearance Rates (Solved %)

| Municipality | Solved% |
|---|---|
| **Georgina** | **50.7%** |
| Newmarket | 43.3% |
| East Gwillimbury | 42.8% |
| King | 38.4% |
| Aurora | 37.8% |
| Richmond Hill | 34.0% |
| Markham | 33.2% |
| Vaughan | 33.0% |
| Whitchurch-Stouffville | 32.2% |

## Output Files

All CSVs in `results/`:

| # | Analysis | Files |
|---|---|---|
| 1 | Incidents by municipality | `all_1_*` / `filtered_1_*` |
| 2 | Incidents by municipality × crime type | `all_2_*` / `filtered_2_*` |
| 3 | Per-capita rate (per 1,000) | `all_3_*` / `filtered_3_*` |
| 4 | Violent crime counts + rate | `all_4a_*`, `all_4b_*` / `filtered_4a_*`, `filtered_4b_*` |
| 5 | Property vs Person breakdown | `all_5_*` / `filtered_5_*` |
| 6 | Year-over-year % change | `all_6_*` / `filtered_6_*` |
| 7 | Status/clearance breakdown | `all_7_*` / `filtered_7_*` |
| 8 | Location type distribution | `all_8_*` / `filtered_8_*` |
| 9 | Shootings + Hate crimes | `all_9a_*`, `all_9b_*` / `filtered_9a_*`, `filtered_9b_*` |
| 10 | Anomaly-adjacent summary | `all_10_*` (unfiltered only) |

## How to Re-Run

```powershell
$env:PYTHONIOENCODING='utf-8'; python analyze_crime_data.py
```
