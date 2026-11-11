"""Unit tests for Phase 8 model evaluation, residual plots, and error segmentation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.features.build_features import feature_pipeline
from src.models.evaluate import (
    compute_metrics,
    error_segmentation,
    generate_evaluation_report,
)
from src.models.train import train_gradient_boosting


def _make_eval_sample_df(n: int = 44) -> pd.DataFrame:
    """Create a synthetic dataset for evaluation diagnostics tests."""
    rng = np.random.default_rng(11)
    cities = ["new-delhi", "bangalore", "ahmedabad"]
    rows = []
    for i in range(n):
        city = cities[i % len(cities)]
        bhk = (i % 4) + 1
        area = 550.0 + bhk * 350.0 + float(rng.normal(0, 30))
        price = area * (10000.0 if city == "new-delhi" else 7500.0) + bhk * 250_000.0
        rows.append(
            {
                "Title": f"{bhk} BHK Flat",
                "Description": "desc",
                "location": city,
                "Status": "Ready to Move",
                "Floor": f"{(i % 5) + 1} out of 10",
                "Transaction": "Resale" if i % 2 == 0 else "New Property",
                "Furnishing": "Unfurnished",
                "facing": "East",
                "overlooking": "Garden/Park",
                "Society": "SocietyA",
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


def test_compute_metrics_and_segmentation() -> None:
    y_true = np.array([4_000_000.0, 8_000_000.0, 15_000_000.0, 30_000_000.0])
    y_pred = np.array([4_200_000.0, 7_500_000.0, 14_000_000.0, 29_000_000.0])
    metrics = compute_metrics(y_true, y_pred, n_features=2)
    assert metrics["r2"] > 0.98
    assert metrics["adjusted_r2"] <= metrics["r2"]
    assert metrics["within_20pct"] == 100.0

    raw_df = pd.DataFrame(
        {
            "location": ["new-delhi", "bangalore", "new-delhi", "mumbai"],
            "Transaction": ["Resale", "New Property", "Resale", "Resale"],
            "Title": ["2 BHK Flat", "Studio Apartment", "3 BHK Flat", "4 BHK Flat"],
        }
    )
    segments = error_segmentation(y_true, y_pred, raw_df)
    assert "by_price_tier" in segments
    assert "by_top_locations" in segments
    assert "by_transaction" in segments
    assert "by_bhk" in segments


def test_generate_evaluation_report_creates_files(tmp_path: Path) -> None:
    df = _make_eval_sample_df(44)
    train_df = df.iloc[:30].copy()
    test_df = df.iloc[30:].copy()

    bundle = feature_pipeline(train_df=train_df, test_df=test_df, random_state=42)
    models = train_gradient_boosting(bundle["X_train"], bundle["y_train"], random_state=42)
    model = models["LightGBM"]

    reports_dir = tmp_path / "reports"
    figures_dir = reports_dir / "figures"
    res = generate_evaluation_report(
        model=model,
        X_test=bundle["X_test"],
        y_test=bundle["y_test"],
        raw_test_df=test_df,
        feature_names=bundle["feature_names"],
        reports_dir=reports_dir,
        figures_dir=figures_dir,
        model_name="LightGBM_Test",
    )

    assert Path(res["report_path"]).exists()
    assert Path(res["metrics_json_path"]).exists()
    for fname in ("residuals.png", "actual_vs_predicted.png", "feature_importance.png"):
        fpath = figures_dir / fname
        assert fpath.exists() and fpath.stat().st_size > 0
