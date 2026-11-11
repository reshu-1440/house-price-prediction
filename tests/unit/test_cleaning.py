"""Unit tests for Phase 3 data cleaning and schema validation."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data.cleaning import (
    clean_pipeline,
    deduplicate_listings,
    parse_area_series,
    parse_car_parking,
    parse_count_series,
    parse_price_series,
    remove_outliers,
)
from src.data.load_data import REQUIRED_RAW_COLUMNS
from src.data.validators import (
    SchemaValidationError,
    assert_valid,
    validate_cleaned_data,
    validate_raw_schema,
)


def _make_raw_rows() -> pd.DataFrame:
    """Create synthetic raw DataFrame covering duplicates, units, leakage cols, and bad records."""
    rows = 8
    data = {col: [None] * rows for col in REQUIRED_RAW_COLUMNS}
    data["Index"] = list(range(rows))
    data["Title"] = [
        "2 BHK Flat",
        "3 BHK Flat",
        "2 BHK Flat",  # duplicate of row 0 excluding Index
        "1 BHK Flat",
        "4 BHK Villa",
        "3 BHK Apartment",
        "2 BHK Resale",
        "5 BHK Mansion",
    ]
    data["Amount(in rupees)"] = [
        "50 Lac",
        "1.25 Cr",
        "50 Lac",
        "Call for Price",
        "90 Lac",
        "75 Lac",
        "60 Lac",
        "500 Cr",  # extreme outlier
    ]
    data["Price (in rupees)"] = [5000.0, 8000.0, 5000.0, None, 6000.0, 5500.0, 4800.0, 99999.0]
    data["location"] = ["New-Delhi", "bangalore", "New-Delhi", "pune", "mumbai", "chennai", "kolkata", "mumbai"]
    data["Carpet Area"] = ["1000 sqft", None, "1000 sqft", "500 sqft", None, "1,200 sqft", "900 sqft", "100 acre"]
    data["Super Area"] = [None, "150 sqyrd", None, None, "100 sqm", None, None, None]
    data["Transaction"] = ["Resale", "New Property", "Resale", "Resale", "Rent/Lease", "Resale", "New Property", "Resale"]
    data["Bathroom"] = ["2", "3", "2", "1", "2", "> 10", None, "4"]
    data["Balcony"] = ["1", "2", "1", None, "1", "> 10", "2", "3"]
    data["Car Parking"] = ["1 Covered,", "2 Open", "1 Covered,", None, "1 Covered", "3 Covered", None, "5 Covered"]
    data["Status"] = ["Ready to Move"] * rows
    data["Furnishing"] = ["Unfurnished", "Semi-Furnished", "Unfurnished", None, "Furnished", "Unfurnished", "Semi-Furnished", "Furnished"]
    data["Ownership"] = ["Freehold", "Freehold", "Freehold", "Leasehold", None, "Freehold", "Freehold", "Freehold"]
    return pd.DataFrame(data)


def test_parse_price_series_handles_units_and_call_for_price() -> None:
    s = pd.Series(["42 Lac ", "1.40 Cr", "2.5 Crore", "15 Lakh", "Call for Price", None])
    out = parse_price_series(s)
    assert out.iloc[0] == pytest.approx(4_200_000.0)
    assert out.iloc[1] == pytest.approx(14_000_000.0)
    assert out.iloc[2] == pytest.approx(25_000_000.0)
    assert out.iloc[3] == pytest.approx(1_500_000.0)
    assert np.isnan(out.iloc[4])
    assert np.isnan(out.iloc[5])


def test_parse_area_series_handles_commas_and_units() -> None:
    s = pd.Series(["1,250 sqft", "100 sqyrd", "100 sqm", "1 acre", "0 sqft", None])
    out = parse_area_series(s)
    assert out.iloc[0] == pytest.approx(1250.0)
    assert out.iloc[1] == pytest.approx(900.0)
    assert out.iloc[2] == pytest.approx(1076.39)
    assert out.iloc[3] == pytest.approx(43560.0)
    assert np.isnan(out.iloc[4])
    assert np.isnan(out.iloc[5])


def test_parse_count_and_car_parking() -> None:
    counts = parse_count_series(pd.Series(["2", "> 10", ">10", None]))
    assert counts.iloc[0] == 2.0
    assert counts.iloc[1] == 11.0
    assert counts.iloc[2] == 11.0
    assert np.isnan(counts.iloc[3])

    df = pd.DataFrame({"Car Parking": ["1 Covered,", "2 Open", None]})
    parsed = parse_car_parking(df)
    assert parsed["parking_count"].tolist() == [1.0, 2.0, 0.0]
    assert parsed["parking_type"].tolist() == ["Covered", "Open", "Missing"]


def test_deduplicate_listings_ignores_index() -> None:
    df = pd.DataFrame({"Index": [0, 1, 2], "location": ["pune", "pune", "delhi"], "Title": ["A", "A", "B"]})
    deduped = deduplicate_listings(df)
    assert len(deduped) == 2


def test_clean_pipeline_and_validators_end_to_end() -> None:
    raw = _make_raw_rows()
    assert_valid(validate_raw_schema(raw))

    cleaned, meta = clean_pipeline(raw, apply_outlier_filter=True)
    report = validate_cleaned_data(cleaned)
    assert_valid(report)

    # Row 2 (duplicate of row 0), row 3 (Call for Price), row 4 (Rent/Lease),
    # and row 7 (500 Cr / 100 acre extreme outlier) should all be excluded.
    assert len(cleaned) == 4
    assert "Price (in rupees)" not in cleaned.columns
    assert "Index" not in cleaned.columns
    assert meta["initial_rows"] == 8
    assert meta["after_dedup_rows"] == 7
    assert cleaned["bathroom_count"].isna().sum() == 0


def test_validators_catch_leakage_and_invalid_values() -> None:
    bad_df = pd.DataFrame(
        {
            "Title": ["2 BHK"],
            "location": ["pune"],
            "Transaction": ["Rent/Lease"],
            "Status": ["Ready to Move"],
            "Furnishing": ["Unfurnished"],
            "Ownership": ["Freehold"],
            "Price_in_rupees": [-100.0],
            "effective_area_sqft": [500.0],
            "area_type": ["carpet"],
            "bathroom_count": [0.0],
            "balcony_count": [1.0],
            "parking_count": [1.0],
            "parking_type": ["Covered"],
            "Price (in rupees)": [5000.0],
        }
    )
    report = validate_cleaned_data(bad_df)
    assert not report.success
    with pytest.raises(SchemaValidationError):
        assert_valid(report)


def test_remove_outliers_respects_precomputed_bounds() -> None:
    df = pd.DataFrame(
        {
            "Price_in_rupees": [5e6, 6e6, 7e6, 8e6, 9e8],
            "effective_area_sqft": [1000.0, 1100.0, 1200.0, 1300.0, 50000.0],
        }
    )
    bounds = {"Price_in_rupees": (1e6, 5e7), "effective_area_sqft": (200.0, 5000.0)}
    filtered, used = remove_outliers(df, bounds=bounds)
    assert len(filtered) == 4
    assert used == bounds
