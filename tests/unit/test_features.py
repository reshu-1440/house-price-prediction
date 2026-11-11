"""Unit tests for Phase 4 feature engineering and sklearn transformers."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.base import clone

from src.features.build_features import feature_pipeline
from src.features.transformers import (
    AreaFeatureBuilder,
    BHKExtractor,
    CategoricalEncoder,
    FloorExtractor,
    LocationEncoder,
)


def _make_cleaned_sample(n: int = 8) -> pd.DataFrame:
    """Create a minimal cleaned-schema DataFrame for feature engineering tests."""
    return pd.DataFrame(
        {
            "Title": [
                "2 BHK Flat",
                "3 BHK Apartment",
                "Studio Apartment for sale",
                "4 BHK Penthouse",
                "2 BHK Flat",
                "3 BHK Flat",
                "Apartment for sale",
                "1 BHK Flat",
            ][:n],
            "Description": ["desc"] * n,
            "location": [
                "new-delhi",
                "bangalore",
                "new-delhi",
                "mumbai",
                "bangalore",
                "mumbai",
                "pune",
                "new-delhi",
            ][:n],
            "Status": ["Ready to Move"] * n,
            "Floor": [
                "3 out of 10",
                "Ground out of 5",
                "Lower Basement out of 4",
                "10 out of 10",
                "2",
                None,
                "1 out of 3",
                "Upper Basement out of 2",
            ][:n],
            "Transaction": ["Resale", "New Property", "Resale", "Resale", "New Property", "Resale", "Resale", "New Property"][:n],
            "Furnishing": ["Unfurnished", "Semi-Furnished", "Furnished", "Unfurnished", "Missing", "Semi-Furnished", "Furnished", "Unfurnished"][:n],
            "facing": ["East", "South -West", "North - East", "Missing", "West", "South", "East", "North"][:n],
            "overlooking": ["Garden/Park", "Missing", "Main Road", "Missing", "Garden/Park", "Missing", "Missing", "Main Road"][:n],
            "Society": ["Alpha", "Missing", "Beta", "Gamma", "Missing", "Alpha", "Missing", "Delta"][:n],
            "Ownership": ["Freehold", "Freehold", "Leasehold", "Freehold", "Missing", "Freehold", "Freehold", "Freehold"][:n],
            "Price_in_rupees": [6e6, 9e6, 3.5e6, 2.5e7, 8e6, 1.8e7, 5e6, 4e6][:n],
            "effective_area_sqft": [1000.0, 1450.0, 480.0, 2600.0, 1200.0, 1600.0, 950.0, 620.0][:n],
            "area_type": ["carpet", "super", "carpet", "super", "carpet", "carpet", "super", "carpet"][:n],
            "parking_count": [1.0, 1.0, 0.0, 2.0, 1.0, 2.0, 1.0, 0.0][:n],
            "parking_type": ["Covered", "Open", "Missing", "Covered", "Covered", "Covered", "Open", "Missing"][:n],
            "bathroom_count": [2.0, 3.0, 1.0, 4.0, 2.0, 3.0, 2.0, 1.0][:n],
            "balcony_count": [1.0, 2.0, 0.0, 3.0, 1.0, 2.0, 1.0, 1.0][:n],
        }
    )


def test_bhk_extractor_and_clone() -> None:
    df = _make_cleaned_sample()
    ext = BHKExtractor()
    cloned = clone(ext)
    out = cloned.fit_transform(df)
    assert out["bhk"].iloc[0] == 2.0
    assert out["bhk"].iloc[2] == 1.0  # Studio
    assert out["is_studio"].iloc[2] == 1.0
    assert out["is_penthouse"].iloc[3] == 1.0
    assert out["bhk"].isna().sum() == 0


def test_floor_extractor_handles_ground_basement_and_missing() -> None:
    df = _make_cleaned_sample()
    out = FloorExtractor().fit_transform(df)
    assert out["floor_number"].iloc[0] == 3.0
    assert out["total_floors"].iloc[0] == 10.0
    assert out["floor_number"].iloc[1] == 0.0
    assert out["is_ground_floor"].iloc[1] == 1.0
    assert out["floor_number"].iloc[2] == -2.0
    assert out["is_top_floor"].iloc[3] == 1.0
    assert out["floor_number"].iloc[7] == -1.0
    assert out[["floor_number", "total_floors", "floor_ratio"]].isna().sum().sum() == 0


def test_area_feature_builder_normalizes_facing_and_creates_ratios() -> None:
    df = BHKExtractor().fit_transform(_make_cleaned_sample())
    out = AreaFeatureBuilder().fit_transform(df)
    assert out["facing"].iloc[1] == "South-West"
    assert out["facing"].iloc[2] == "North-East"
    assert out["area_per_bhk"].iloc[0] == pytest.approx(500.0)
    assert out["is_carpet_area"].iloc[0] == 1.0
    assert out["is_carpet_area"].iloc[1] == 0.0


def test_location_encoder_handles_unseen_city_without_leakage() -> None:
    train = _make_cleaned_sample(n=6)
    test = _make_cleaned_sample(n=2)
    test.loc[0, "location"] = "unseen-city"

    enc = LocationEncoder(smoothing=10.0, n_splits=3, use_oof_in_fit_transform=True)
    tr_out = enc.fit_transform(train, train["Price_in_rupees"])
    te_out = enc.transform(test)

    assert te_out["location_target_enc"].iloc[0] == pytest.approx(enc.global_mean_)
    assert te_out["location_freq"].iloc[0] == 0.0
    assert tr_out["location_target_enc"].isna().sum() == 0


def test_categorical_encoder_handles_unseen_categories() -> None:
    train = _make_cleaned_sample(n=6)
    test = _make_cleaned_sample(n=2)
    test.loc[0, "Furnishing"] = "BrandNewUnseenCategory"

    enc = CategoricalEncoder()
    tr_out = enc.fit_transform(train)
    te_out = enc.transform(test)
    assert list(tr_out.columns) == list(te_out.columns)
    assert not te_out.isna().any().any()


def test_feature_pipeline_end_to_end_train_and_test() -> None:
    full = _make_cleaned_sample(n=8)
    train = full.iloc[:6].copy()
    test = full.iloc[6:].copy()

    res = feature_pipeline(train_df=train, test_df=test, random_state=42)
    X_train, y_train = res["X_train"], res["y_train"]
    X_test, y_test = res["X_test"], res["y_test"]

    assert list(X_train.columns) == list(X_test.columns)
    assert len(X_train) == 6 and len(y_train) == 6
    assert len(X_test) == 2 and len(y_test) == 2
    assert not X_train.isna().any().any()
    assert not X_test.isna().any().any()
    assert np.isfinite(X_train.to_numpy()).all()
    assert np.isfinite(X_test.to_numpy()).all()
