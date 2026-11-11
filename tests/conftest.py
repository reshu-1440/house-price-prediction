"""Shared pytest fixtures across unit, integration, and model tests."""

from __future__ import annotations

from collections.abc import Iterator

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.dependencies import model_state
from src.data.load_data import REQUIRED_RAW_COLUMNS
from src.pipeline.training_pipeline import build_training_pipeline


@pytest.fixture
def sample_raw_df() -> pd.DataFrame:
    """Deterministic raw-schema DataFrame covering duplicates, units, and edge cases."""
    rows = 10
    data = {col: [None] * rows for col in REQUIRED_RAW_COLUMNS}
    data["Index"] = list(range(rows))
    data["Title"] = [
        "2 BHK Flat in Delhi",
        "3 BHK Flat in Bangalore",
        "2 BHK Flat in Delhi",  # duplicate of row 0 excluding Index
        "1 BHK Studio",
        "4 BHK Villa",
        "3 BHK Apartment",
        "2 BHK Resale",
        "3 BHK New Flat",
        "2 BHK Flat",
        "3 BHK Penthouse",
    ]
    data["Amount(in rupees)"] = [
        "65 Lac",
        "1.35 Cr",
        "65 Lac",
        "Call for Price",
        "2.10 Cr",
        "85 Lac",
        "58 Lac",
        "1.10 Cr",
        "72 Lac",
        "1.45 Cr",
    ]
    data["Price (in rupees)"] = [6500.0, 9000.0, 6500.0, None, 11000.0, 7200.0, 5800.0, 8200.0, 6100.0, 9500.0]
    data["location"] = [
        "new-delhi",
        "bangalore",
        "new-delhi",
        "pune",
        "mumbai",
        "ahmedabad",
        "kolkata",
        "hyderabad",
        "chennai",
        "bangalore",
    ]
    data["Carpet Area"] = [
        "1000 sqft",
        None,
        "1000 sqft",
        "500 sqft",
        None,
        "1,200 sqft",
        "980 sqft",
        None,
        "1,150 sqft",
        "1,500 sqft",
    ]
    data["Super Area"] = [None, "150 sqyrd", None, None, "180 sqm", None, None, "1,350 sqft", None, None]
    data["Transaction"] = [
        "Resale",
        "New Property",
        "Resale",
        "Resale",
        "Resale",
        "New Property",
        "Resale",
        "New Property",
        "Resale",
        "New Property",
    ]
    data["Status"] = ["Ready to Move"] * rows
    data["Floor"] = [
        "3 out of 10",
        "5 out of 12",
        "3 out of 10",
        "Ground out of 4",
        "2 out of 3",
        "4 out of 8",
        "1 out of 5",
        "7 out of 14",
        "2 out of 6",
        "12 out of 12",
    ]
    data["Furnishing"] = [
        "Unfurnished",
        "Semi-Furnished",
        "Unfurnished",
        "Furnished",
        "Furnished",
        "Semi-Furnished",
        "Unfurnished",
        "Semi-Furnished",
        "Unfurnished",
        "Furnished",
    ]
    data["Ownership"] = ["Freehold"] * rows
    data["facing"] = ["East", "North - East", "East", "West", "South", "East", "North", "South -West", "East", "North - East"]
    data["Bathroom"] = ["2", "3", "2", "1", "4", "3", "2", "3", "2", "3"]
    data["Balcony"] = ["1", "2", "1", "1", "3", "2", "1", "2", "1", "2"]
    data["Car Parking"] = ["1 Covered", "2 Covered", "1 Covered", None, "2 Open", "1 Covered", "1 Open", "1 Covered", None, "2 Covered"]
    return pd.DataFrame(data)


@pytest.fixture(scope="session")
def fitted_sample_pipeline():
    """Session-scoped fast trained pipeline independent of serialized local artifacts."""
    rng = np.random.default_rng(42)
    cities = ["new-delhi", "bangalore", "ahmedabad", "mumbai", "pune", "hyderabad", "chennai", "kolkata"]
    rows = []
    city_rate = {
        "mumbai": 15000.0,
        "new-delhi": 11500.0,
        "bangalore": 9500.0,
        "hyderabad": 8000.0,
        "chennai": 8200.0,
        "pune": 7800.0,
        "kolkata": 6500.0,
        "ahmedabad": 6000.0,
    }
    for i in range(64):
        city = cities[i % len(cities)]
        bhk = (i % 4) + 1
        area = 500.0 + bhk * 350.0 + float(rng.normal(0, 25))
        price = area * city_rate[city] + bhk * 250_000.0
        rows.append(
            {
                "Title": f"{bhk} BHK Property",
                "location": city,
                "Status": "Ready to Move",
                "Floor": f"{(i % 6) + 1} out of 12",
                "Transaction": "Resale" if i % 2 == 0 else "New Property",
                "Furnishing": "Unfurnished" if i % 2 == 0 else "Semi-Furnished",
                "facing": "East",
                "overlooking": "Garden/Park",
                "Society": "Sample Society",
                "Ownership": "Freehold",
                "effective_area_sqft": max(area, 300.0),
                "area_type": "carpet",
                "Bathroom": str(bhk),
                "Balcony": "1",
                "Car Parking": "1 Covered",
                "Price_in_rupees": max(price, 600_000.0),
            }
        )
    df = pd.DataFrame(rows)
    pipe = build_training_pipeline(
        model_type="lightgbm",
        model_params={"n_estimators": 40, "learning_rate": 0.1, "num_leaves": 15, "min_child_samples": 3},
        random_state=42,
    )
    pipe.fit(df.drop(columns=["Price_in_rupees"]), df["Price_in_rupees"])
    return pipe


@pytest.fixture
def api_client(fitted_sample_pipeline) -> Iterator[TestClient]:
    """Provide a FastAPI TestClient injected with ``fitted_sample_pipeline``."""
    model_state.set_model(
        fitted_sample_pipeline,
        metadata={
            "model_name": "lightgbm",
            "model_version": "0.1.0-test",
            "trained_at_utc": "2026-11-12T00:00:00+00:00",
            "feature_count": 50,
            "known_locations_count": 8,
            "metrics": {"r2": 0.8128, "mae": 2206793.51},
        },
    )
    with TestClient(app) as client:
        yield client
    model_state.clear()
