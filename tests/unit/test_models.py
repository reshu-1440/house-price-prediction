"""Unit tests for Phase 6 model training, comparison, and prediction helpers."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.features.build_features import feature_pipeline
from src.models.predict import predict, predict_single
from src.models.train import (
    compare_models,
    train_baseline,
    train_decision_tree,
    train_gradient_boosting,
    train_linear_models,
    train_random_forest,
)


def _make_model_sample_df(n: int = 40) -> pd.DataFrame:
    """Generate a synthetic cleaned property dataset with learnable signal."""
    rng = np.random.default_rng(42)
    cities = ["new-delhi", "bangalore", "ahmedabad"]
    rows = []
    for i in range(n):
        city = cities[i % len(cities)]
        bhk = (i % 3) + 1
        area = 600.0 + bhk * 350.0 + float(rng.normal(0, 40))
        city_mult = {"new-delhi": 11000.0, "bangalore": 9000.0, "ahmedabad": 6000.0}[city]
        price = area * city_mult + bhk * 200_000.0
        rows.append(
            {
                "Title": f"{bhk} BHK Flat",
                "Description": "nice flat",
                "location": city,
                "Status": "Ready to Move",
                "Floor": f"{(i % 5) + 1} out of 10",
                "Transaction": "Resale" if i % 2 == 0 else "New Property",
                "Furnishing": "Unfurnished" if i % 2 == 0 else "Semi-Furnished",
                "facing": "East",
                "overlooking": "Garden/Park",
                "Society": "Sample Society",
                "Ownership": "Freehold",
                "Price_in_rupees": max(price, 500_000.0),
                "effective_area_sqft": max(area, 300.0),
                "area_type": "carpet",
                "parking_count": 1.0,
                "parking_type": "Covered",
                "bathroom_count": float(bhk),
                "balcony_count": 1.0,
            }
        )
    return pd.DataFrame(rows)


def test_models_train_compare_and_beat_baseline(tmp_path: Path) -> None:
    df = _make_model_sample_df(48)
    train_df = df.iloc[:36].copy()
    test_df = df.iloc[36:].copy()

    bundle = feature_pipeline(train_df=train_df, test_df=test_df, random_state=42)
    X_tr, y_tr = bundle["X_train"], bundle["y_train"]
    X_te, y_te = bundle["X_test"], bundle["y_test"]

    factories = {"Baseline": train_baseline(X_tr, y_tr)}
    factories.update(train_linear_models(X_tr, y_tr))
    factories["DecisionTree"] = train_decision_tree(X_tr, y_tr, max_depth=6, min_samples_leaf=2)
    factories["RandomForest"] = train_random_forest(
        X_tr, y_tr, n_estimators=20, max_depth=8, min_samples_leaf=2, n_jobs=1
    )
    factories.update(train_gradient_boosting(X_tr, y_tr))

    md_path = tmp_path / "model_comparison.md"
    fig_path = tmp_path / "model_comparison.png"
    results_df, fitted = compare_models(
        factories, X_tr, y_tr, X_te, y_te, output_md_path=md_path, output_fig_path=fig_path
    )

    assert md_path.exists()
    assert fig_path.exists()
    assert len(results_df) >= 6
    baseline_r2 = float(results_df.loc[results_df["model"] == "Baseline", "test_r2"].iloc[0])
    top_r2 = float(results_df["test_r2"].iloc[0])
    assert top_r2 > baseline_r2

    preds = predict(fitted["RandomForest"], X_te)
    assert len(preds) == len(X_te)
    assert (preds >= 0).all()

    single_pred = predict_single(
        fitted["RandomForest"],
        {
            "Title": "3 BHK Flat",
            "location": "bangalore",
            "Status": "Ready to Move",
            "Floor": "4 out of 10",
            "Transaction": "Resale",
            "Furnishing": "Semi-Furnished",
            "facing": "East",
            "overlooking": "Garden/Park",
            "Society": "Sample Society",
            "Ownership": "Freehold",
            "Carpet Area": "1500 sqft",
            "Bathroom": "3",
            "Balcony": "2",
            "Car Parking": "1 Covered",
        },
        transformers=bundle["transformers"],
        feature_names=bundle["feature_names"],
    )
    assert single_pred > 0
