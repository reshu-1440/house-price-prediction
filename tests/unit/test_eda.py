"""Unit tests for Phase 2 EDA and data quality reporting."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.data.eda import (
    generate_data_quality_report,
    generate_summary_statistics,
    run_eda,
)
from src.data.load_data import REQUIRED_RAW_COLUMNS


def _make_eda_sample_df() -> pd.DataFrame:
    """Build a small synthetic DataFrame covering mixed price/area/category formats."""
    rows = 6
    data = {col: [None] * rows for col in REQUIRED_RAW_COLUMNS}
    data["Index"] = list(range(rows))
    data["Title"] = [
        "2 BHK Flat in Delhi",
        "3 BHK Flat in Bangalore",
        "1 BHK Studio",
        "4 BHK Villa",
        "2 BHK Flat in Delhi",
        "3 BHK Flat",
    ]
    data["Amount(in rupees)"] = [
        "50 Lac",
        "1.50 Cr",
        "Call for Price",
        "2.25 Cr",
        "50 Lac",
        "85 Lac",
    ]
    data["Price (in rupees)"] = [5000.0, 9500.0, None, 12000.0, 5000.0, 7000.0]
    data["location"] = ["new-delhi", "bangalore", "pune", "mumbai", "new-delhi", "bangalore"]
    data["Carpet Area"] = ["1000 sqft", "1,500 sqft", None, "200 sqyrd", "1000 sqft", "100 sqm"]
    data["Super Area"] = [None, "1,800 sqft", "600 sqft", None, None, None]
    data["Status"] = ["Ready to Move"] * rows
    data["Transaction"] = ["Resale", "New Property", "Resale", "Rent/Lease", "Resale", "New Property"]
    data["Furnishing"] = ["Unfurnished", "Semi-Furnished", "Furnished", "Unfurnished", "Unfurnished", None]
    data["Ownership"] = ["Freehold", "Freehold", None, "Leasehold", "Freehold", "Freehold"]
    data["Bathroom"] = ["2", "3", "1", "> 10", "2", "3"]
    data["Balcony"] = ["1", "2", None, "> 10", "1", "2"]
    return pd.DataFrame(data)


def test_generate_summary_statistics() -> None:
    df = _make_eda_sample_df()
    summary = generate_summary_statistics(df)
    assert summary["rows"] == 6
    assert summary["columns"] == len(REQUIRED_RAW_COLUMNS)
    assert summary["numeric_summary"]["_price_in_rupees"]["count"] == 5.0
    assert summary["numeric_summary"]["_price_in_rupees"]["min"] == 5_000_000.0
    assert summary["numeric_summary"]["_price_in_rupees"]["max"] == 22_500_000.0


def test_generate_data_quality_report(tmp_path: Path) -> None:
    df = _make_eda_sample_df()
    json_path = tmp_path / "dq.json"
    report = generate_data_quality_report(df, output_path=json_path)

    assert report["total_rows"] == 6
    assert report["exact_duplicates_all_columns"] == 0
    assert report["duplicates_excluding_index"] == 1
    assert report["call_for_price_count"] == 1
    assert set(report["all_null_columns"]) >= {"Dimensions", "Plot Area"}
    assert report["gt10_string_counts"]["bathroom"] == 1
    assert report["gt10_string_counts"]["balcony"] == 1
    assert json_path.exists()
    loaded = json.loads(json_path.read_text(encoding="utf-8"))
    assert loaded["total_rows"] == 6


def test_run_eda_creates_all_artifacts(tmp_path: Path) -> None:
    df = _make_eda_sample_df()
    reports_dir = tmp_path / "reports"
    figures_dir = reports_dir / "figures"

    result = run_eda(df, reports_dir=reports_dir, figures_dir=figures_dir)

    assert Path(result["markdown_report"]).exists()
    assert (reports_dir / "data_quality_report.json").exists()
    assert len(result["figures"]) == 6
    for fig in result["figures"]:
        fig_path = Path(fig)
        assert fig_path.exists()
        assert fig_path.stat().st_size > 0
