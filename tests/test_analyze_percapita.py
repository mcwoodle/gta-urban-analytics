"""Regression test for audit F-15: the per-capita 'Total' column is a cumulative
multi-year rate and must be labelled so, not presented as an annual rate."""

import pandas as pd

from gta_urban_analytics.analyze.analyze import _per_capita_table, per_1k, POPULATION


def test_per_capita_table_renames_cumulative_total_and_computes_rates():
    muni = "Markham"
    pivot = pd.DataFrame({2024: [100], "Total": [250]}, index=pd.Index([muni], name="Municipality"))

    rates = _per_capita_table(pivot)

    assert "Total (cumulative)" in rates.columns
    assert "Total" not in rates.columns
    assert rates.loc[muni, 2024] == per_1k(100, POPULATION[muni])
    assert rates.loc[muni, "Total (cumulative)"] == per_1k(250, POPULATION[muni])
