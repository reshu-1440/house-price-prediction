"""Unit tests for Phase 7 hyperparameter optimization and cross-validation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from src.features.build_features import feature_pipeline
from src.models.hyperparameter_tuning import (
    cross_validate_model,
    save_best_params,
    tune_gradient_boosting,
    tune_random_forest,
)
from src.models.train import train_baseline


def _make_tuning_sample_df(n: int = 40) -> pd.DataFrame:
    """Create a self-contained synthetic cleaned property DataFrame for tuning tests."""
    rng = np.random.default_rng(7)
    cities = ["new-delhi", "bangalore", "ahmedabad"]
    rows = []
    for i in range(n):
        city = cities[i % len(cities)]
        bhk = (i % 3) + 1
        area = 650.0 + bhk * 320.0 + float(rng.normal(0, 35))
        price = area * (9000.0 if city == "new-delhi" else 7000.0) + bhk * 150_000.0
        rows.append(
            {
                "Title": f"{bhk} BHK Flat",
                "Description": "desc",
                "location": city,
                "Status": "Ready to Move",
                "Floor": f"{(i % 4) + 1} out of 8",
                "Transaction": "Resale" if i % 2 == 0 else "New Property",
                "Furnishing": "Unfurnished",
                "facing": "East",
                "overlooking": "Garden/Park",
                "Society": "SocietyA",
                "Ownership": "Freehold",
                "Price_in_rupees": max(price, 400_000.0),
                "effective_area_sqft": max(area, 300.0),
                "area_type": "carpet",
                "parking_count": 1.0,
                "parking_type": "Covered",
                "bathroom_count": float(bhk),
                "balcony_count": 1.0,
            }
        )
    return pd.DataFrame(rows)


def test_cross_validate_and_tuning_on_synthetic_data(tmp_path: Path) -> None:
    df = _make_tuning_sample_df(40)
    bundle = feature_pipeline(train_df=df, random_state=42)
    X, y = bundle["X_train"], bundle["y_train"]

    baseline = train_baseline(X, y)
    cv_res = cross_validate_model(baseline, X, y, cv=3)
    assert "cv_r2_mean" in cv_res
    assert "cv_mae_mean" in cv_res
    assert "cv_rmse_mean" in cv_res

    rf_tuned = tune_random_forest(X, y, n_iter=2, cv=2, random_state=42)
    assert "model" in rf_tuned and "best_params" in rf_tuned

    xgb_tuned = tune_gradient_boosting(X, y, model_type="xgboost", n_trials=2, cv=2, random_state=42)
    assert "model" in xgb_tuned and "best_params" in xgb_tuned

    lgb_tuned = tune_gradient_boosting(X, y, model_type="lightgbm", n_trials=2, cv=2, random_state=42)
    assert "model" in lgb_tuned and "best_params" in lgb_tuned

    yaml_path = tmp_path / "hyperparameters.yaml"
    save_best_params(
        {
            "xgboost": {"params": xgb_tuned["best_params"], "cv_r2": xgb_tuned["best_cv_r2"]},
            "lightgbm": {"params": lgb_tuned["best_params"], "cv_r2": lgb_tuned["best_cv_r2"]},
        },
        yaml_path,
    )
    loaded = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    assert "xgboost" in loaded and "lightgbm" in loaded
