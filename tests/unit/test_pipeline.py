"""Unit tests for Phase 10 reproducible training and inference pipelines."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.pipeline.inference_pipeline import predict_from_raw
from src.pipeline.training_pipeline import (
    build_training_pipeline,
    load_pipeline,
    save_pipeline,
)


def _make_raw_pipeline_df(n: int = 36) -> pd.DataFrame:
    """Create a synthetic raw property DataFrame (pre-cleaning format)."""
    rng = np.random.default_rng(23)
    cities = ["new-delhi", "bangalore", "ahmedabad"]
    rows = []
    for i in range(n):
        city = cities[i % len(cities)]
        bhk = (i % 3) + 1
        area = 600.0 + bhk * 350.0 + float(rng.normal(0, 30))
        price = area * (10000.0 if city == "new-delhi" else 7500.0) + bhk * 200_000.0
        rows.append(
            {
                "Title": f"{bhk} BHK Flat in {city}",
                "location": city,
                "Status": "Ready to Move",
                "Floor": f"{(i % 5) + 1} out of 10",
                "Transaction": "Resale" if i % 2 == 0 else "New Property",
                "Furnishing": "Unfurnished" if i % 2 == 0 else "Semi-Furnished",
                "facing": "East",
                "overlooking": "Garden/Park",
                "Society": "Sample Society",
                "Ownership": "Freehold",
                "Carpet Area": f"{int(area)} sqft" if i % 2 == 0 else None,
                "Super Area": None if i % 2 == 0 else f"{int(area)} sqft",
                "Bathroom": str(bhk),
                "Balcony": "1",
                "Car Parking": "1 Covered",
                "Price_in_rupees": max(price, 500_000.0),
            }
        )
    return pd.DataFrame(rows)


def test_training_pipeline_save_load_and_raw_inference(tmp_path: Path) -> None:
    df = _make_raw_pipeline_df(36)
    train = df.iloc[:28].copy()
    test = df.iloc[28:].copy()

    X_tr = train.drop(columns=["Price_in_rupees"])
    y_tr = train["Price_in_rupees"]
    X_te = test.drop(columns=["Price_in_rupees"])

    pipeline = build_training_pipeline(
        model_type="lightgbm",
        model_params={"n_estimators": 30, "learning_rate": 0.1, "num_leaves": 15, "min_child_samples": 3},
        random_state=42,
    )
    pipeline.fit(X_tr, y_tr)
    expected = predict_from_raw(pipeline, X_te)

    artifact_path = tmp_path / "house_price_pipeline.joblib"
    save_pipeline(pipeline, artifact_path, metadata={"model_name": "lightgbm"})
    assert artifact_path.exists()
    assert json.loads((tmp_path / "metadata.json").read_text(encoding="utf-8"))["model_name"] == "lightgbm"

    reloaded = load_pipeline(artifact_path)
    reloaded_preds = predict_from_raw(reloaded, X_te)
    assert np.allclose(expected, reloaded_preds)

    # Raw API-like single dictionary (with area_sqft + bhk instead of raw CSV strings)
    single_pred = predict_from_raw(
        reloaded,
        {
            "location": "bangalore",
            "area_sqft": 1450.0,
            "bhk": 3,
            "bathroom": 3,
            "balcony": 2,
            "Transaction": "Resale",
            "Furnishing": "Semi-Furnished",
        },
    )
    assert len(single_pred) == 1 and single_pred[0] > 0

    # Batch list of raw dicts with unseen city
    batch_preds = predict_from_raw(
        reloaded,
        [
            {"location": "new-delhi", "Carpet Area": "1,200 sqft", "Title": "3 BHK Flat", "Bathroom": "2"},
            {"location": "unseen-city", "area_sqft": 950.0, "bhk": 2},
        ],
    )
    assert len(batch_preds) == 2 and (batch_preds > 0).all()
