"""
YRP Crime Data Analysis
=======================
Reads Occurrence_2021-2025.csv and produces per-year insights:
  1. Total incidents by municipality
  2. Total incidents by municipality × crime type
  3. All of the above with anomaly locations removed (500m radius)
  4. Per-capita rates, violent crime, clearance, and more

Every analysis is output in both UNFILTERED and FILTERED versions.
Results are saved to a results/ subfolder as CSVs.
"""

import os
import math
import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

CSV_PATH = os.path.join(os.path.dirname(__file__) or ".", "Occurrence_2021-2025.csv")
RESULTS_DIR = os.path.join(os.path.dirname(__file__) or ".", "results")

FILTER_RADIUS_M = 500  # metres

# 2021 Census populations (York Region municipalities)
POPULATION = {
    "Vaughan": 323_103,
    "Markham": 338_503,
    "Richmond Hill": 202_022,
    "Newmarket": 87_942,
    "Aurora": 62_057,
    "Georgina": 47_642,
    "East Gwillimbury": 34_637,
    "King": 27_333,
    "Whitchurch-Stouffville": 49_864,
}

# Anomaly locations – UTM Zone 17N coordinates (easting, northing)
ANOMALY_LOCATIONS = {
    # Shopping Malls
    "Upper Canada Mall (Newmarket)":          (625_755, 4_880_434),
    "Hillcrest Mall (Richmond Hill)":         (626_758, 4_855_529),
    "Markville Shopping Centre (Markham)":    (632_240, 4_856_580),
    "Pacific Mall (Markham)":                 (640_699, 4_856_967),
    "Vaughan Mills":                          (610_694, 4_848_826),
    "Promenade Mall (Vaughan)":               (618_010, 4_856_047),
    "CF Markham":                             (637_845, 4_858_551),
    # Attractions
    "Canada's Wonderland":                    (611_878, 4_853_354),
    # Hospitals
    "Mackenzie Health (Richmond Hill)":       (625_907, 4_858_873),
    "Cortellucci Vaughan Hospital":           (617_453, 4_853_953),
    "Markham Stouffville Hospital":           (639_166, 4_862_703),
    "Southlake Regional Health (Newmarket)":  (622_697, 4_879_547),
    # GO Transit Stations (approximate)
    "Newmarket GO":                           (623_248, 4_879_603),
    "Aurora GO":                              (622_464, 4_872_848),
    "Richmond Hill GO":                       (625_457, 4_856_942),
    "Markham GO":                             (633_393, 4_852_737),
    "Unionville GO":                          (634_008, 4_857_632),
    "Mount Joy GO":                           (636_311, 4_858_022),
}

# Crime-type groupings for summary
PROPERTY_TYPES = {
    "Theft Under $5000", "Theft Over $5000", "Theft of Motor Vehicle",
    "Break and Enter - Residential", "Break and Enter - Commercial",
    "Mischief", "Arson", "Fraud", "Other Property Crime",
}
PERSON_TYPES = {
    "Assaults", "Robbery", "Sexual Violations", "Other Persons Crime",
    "Attempt Murder", "Homicide",
}


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def euclidean_dist(x1, y1, x2, y2):
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


def is_near_anomaly(x, y):
    """Return True if (x, y) is within FILTER_RADIUS_M of any anomaly location."""
    if pd.isna(x) or pd.isna(y):
        return False
    for _, (ax, ay) in ANOMALY_LOCATIONS.items():
        if euclidean_dist(x, y, ax, ay) <= FILTER_RADIUS_M:
            return True
    return False


def per_1k(count, pop):
    if pop == 0:
        return 0.0
    return round(count / pop * 1000, 2)


def save(df, name):
    path = os.path.join(RESULTS_DIR, f"{name}.csv")
    df.to_csv(path)
    print(f"  → Saved {path}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    # ── Load & prepare ─────────────────────────────────────────────────────
    print("Loading data …")
    df = pd.read_csv(CSV_PATH)
    print(f"  Total rows: {len(df):,}")

    # Extract year from Occurrence Date
    df["Occurrence Date"] = pd.to_datetime(df["Occurrence Date"], errors="coerce")
    df["Year"] = df["Occurrence Date"].dt.year.astype("Int64")

    # Standardise municipality
    df["Municipality"] = df["Municipality"].str.strip()

    # ── Mark anomaly-adjacent records ──────────────────────────────────────
    print("Flagging anomaly-adjacent incidents (500 m radius) …")
    df["near_anomaly"] = df.apply(lambda r: is_near_anomaly(r["x"], r["y"]), axis=1)
    n_flagged = df["near_anomaly"].sum()
    print(f"  Flagged {n_flagged:,} incidents near anomaly locations")

    df_filtered = df[~df["near_anomaly"]].copy()

    # ── Helper: run all analyses on a given dataframe ──────────────────────
    def run_analyses(data: pd.DataFrame, tag: str):
        label = "UNFILTERED" if tag == "all" else "FILTERED (anomalies removed)"
        print(f"\n{'='*70}")
        print(f"  {label}  ({len(data):,} records)")
        print(f"{'='*70}")

        # 1 ─ Total Incidents by Municipality per Year
        print("\n── 1. Total Incidents by Municipality ──")
        t1 = data.groupby(["Year", "Municipality"]).size().reset_index(name="Incidents")
        t1_pivot = t1.pivot_table(index="Municipality", columns="Year",
                                  values="Incidents", fill_value=0, aggfunc="sum")
        t1_pivot["Total"] = t1_pivot.sum(axis=1)
        t1_pivot = t1_pivot.sort_values("Total", ascending=False)
        print(t1_pivot.to_string())
        save(t1_pivot, f"{tag}_1_incidents_by_municipality")

        # 2 ─ Total Incidents by Municipality × Crime Type per Year
        print("\n── 2. Total Incidents by Municipality × Crime Type ──")
        t2 = data.groupby(["Year", "Municipality", "Occurrence Type"]).size() \
                  .reset_index(name="Incidents")
        t2_pivot = t2.pivot_table(index=["Municipality", "Occurrence Type"],
                                  columns="Year", values="Incidents",
                                  fill_value=0, aggfunc="sum")
        t2_pivot["Total"] = t2_pivot.sum(axis=1)
        t2_pivot = t2_pivot.sort_values(["Municipality", "Total"], ascending=[True, False])
        print(t2_pivot.head(40).to_string())
        print(f"  … ({len(t2_pivot)} rows total, see CSV)")
        save(t2_pivot, f"{tag}_2_incidents_by_municipality_crime_type")

        # 3 ─ Per-Capita Rates
        print("\n── 3. Incidents per 1,000 Residents ──")
        t3 = t1_pivot.copy()
        for col in t3.columns:
            t3[col] = t3.apply(
                lambda r: per_1k(r[col], POPULATION.get(r.name, 0)), axis=1
            )
        print(t3.to_string())
        save(t3, f"{tag}_3_per_capita_rate")

        # 4 ─ Violent Crime Rate per 1,000 Residents
        print("\n── 4. Violent Crime Rate per 1,000 Residents ──")
        violent = data[data["Special Grouping"] == "Violent Crime"]
        t4 = violent.groupby(["Year", "Municipality"]).size().reset_index(name="Violent")
        t4_pivot = t4.pivot_table(index="Municipality", columns="Year",
                                  values="Violent", fill_value=0, aggfunc="sum")
        t4_pivot["Total"] = t4_pivot.sum(axis=1)
        t4_rate = t4_pivot.copy()
        for col in t4_rate.columns:
            t4_rate[col] = t4_rate.apply(
                lambda r: per_1k(r[col], POPULATION.get(r.name, 0)), axis=1
            )
        print(t4_rate.sort_values("Total", ascending=False).to_string())
        save(t4_pivot, f"{tag}_4a_violent_crime_counts")
        save(t4_rate, f"{tag}_4b_violent_crime_per_1k")

        # 5 ─ Property vs Person Crime Breakdown
        print("\n── 5. Property vs Person Crime Breakdown ──")
        data_cat = data.copy()
        data_cat["Crime Category"] = data_cat["Occurrence Type"].apply(
            lambda t: "Property" if t in PROPERTY_TYPES
                      else ("Person" if t in PERSON_TYPES else "Other")
        )
        t5 = data_cat.groupby(["Year", "Municipality", "Crime Category"]).size() \
                      .reset_index(name="Incidents")
        t5_pivot = t5.pivot_table(index=["Municipality", "Crime Category"],
                                  columns="Year", values="Incidents",
                                  fill_value=0, aggfunc="sum")
        t5_pivot["Total"] = t5_pivot.sum(axis=1)
        print(t5_pivot.to_string())
        save(t5_pivot, f"{tag}_5_property_vs_person")

        # 6 ─ Year-over-Year % Change by Municipality
        print("\n── 6. Year-over-Year % Change ──")
        t6 = t1_pivot.drop(columns=["Total"], errors="ignore").copy()
        years = sorted([c for c in t6.columns if isinstance(c, (int, np.integer))])
        yoy = pd.DataFrame(index=t6.index)
        for i in range(1, len(years)):
            prev, curr = years[i - 1], years[i]
            col_name = f"{prev}→{curr}"
            yoy[col_name] = ((t6[curr] - t6[prev]) / t6[prev].replace(0, np.nan) * 100).round(1)
        print(yoy.to_string())
        save(yoy, f"{tag}_6_yoy_change")

        # 7 ─ Clearance / Status Rate
        print("\n── 7. Status Breakdown (Solved / Closed / Open) ──")
        t7 = data.groupby(["Municipality", "Status"]).size().reset_index(name="Count")
        t7_pivot = t7.pivot_table(index="Municipality", columns="Status",
                                  values="Count", fill_value=0, aggfunc="sum")
        t7_pivot["Total"] = t7_pivot.sum(axis=1)
        if "Solved" in t7_pivot.columns:
            t7_pivot["Solved%"] = (t7_pivot["Solved"] / t7_pivot["Total"] * 100).round(1)
        print(t7_pivot.to_string())
        save(t7_pivot, f"{tag}_7_status_breakdown")

        # 8 ─ Location Type Distribution
        print("\n── 8. Location Type Distribution ──")
        t8 = data.groupby(["Municipality", "Location Code"]).size() \
                  .reset_index(name="Count")
        t8_pivot = t8.pivot_table(index="Municipality", columns="Location Code",
                                  values="Count", fill_value=0, aggfunc="sum")
        t8_pivot["Total"] = t8_pivot.sum(axis=1)
        print(t8_pivot.to_string())
        save(t8_pivot, f"{tag}_8_location_type")

        # 9 ─ Shootings & Hate Crimes
        print("\n── 9. Shootings & Hate Crimes per Municipality per Year ──")
        shootings = data[data["Shooting"] == "Shootings"]
        t9s = shootings.groupby(["Year", "Municipality"]).size().reset_index(name="Shootings")
        t9s_pivot = t9s.pivot_table(index="Municipality", columns="Year",
                                    values="Shootings", fill_value=0, aggfunc="sum")
        t9s_pivot["Total"] = t9s_pivot.sum(axis=1)
        print("Shootings:")
        print(t9s_pivot.to_string())
        save(t9s_pivot, f"{tag}_9a_shootings")

        hate = data[data["Hate Crime"] == "Hate Crime"]
        t9h = hate.groupby(["Year", "Municipality"]).size().reset_index(name="Hate Crimes")
        t9h_pivot = t9h.pivot_table(index="Municipality", columns="Year",
                                    values="Hate Crimes", fill_value=0, aggfunc="sum")
        t9h_pivot["Total"] = t9h_pivot.sum(axis=1)
        print("\nHate Crimes:")
        print(t9h_pivot.to_string())
        save(t9h_pivot, f"{tag}_9b_hate_crimes")

        # 10 ─ Anomaly-adjacent summary (only meaningful for unfiltered)
        if tag == "all":
            print("\n── 10. Incidents Near Anomaly Locations (breakdown) ──")
            anomaly_data = data[data.get("near_anomaly", False) == True] if "near_anomaly" in data.columns else pd.DataFrame()
            if not anomaly_data.empty:
                t10 = anomaly_data.groupby(["Year", "Municipality"]).size() \
                                  .reset_index(name="Near-Anomaly Incidents")
                t10_pivot = t10.pivot_table(index="Municipality", columns="Year",
                                            values="Near-Anomaly Incidents",
                                            fill_value=0, aggfunc="sum")
                t10_pivot["Total"] = t10_pivot.sum(axis=1)
                t10_pivot["% of All"] = (
                    t10_pivot["Total"] / t1_pivot["Total"] * 100
                ).round(1)
                print(t10_pivot.to_string())
                save(t10_pivot, f"{tag}_10_anomaly_adjacent_summary")

    # ── Run both versions ──────────────────────────────────────────────────
    run_analyses(df, "all")
    run_analyses(df_filtered, "filtered")

    print(f"\n✅ Done — all CSVs saved to {RESULTS_DIR}/")


if __name__ == "__main__":
    main()
