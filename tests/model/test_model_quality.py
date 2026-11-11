"""Model quality threshold and monotonic domain behavior tests."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from src.pipeline.inference_pipeline import predict_from_raw
from src.pipeline.training_pipeline import load_pipeline

pytestmark = pytest.mark.model


def test_saved_evaluation_metrics_meet_quality_thresholds() -> None:
    metrics_path = Path("reports/evaluation_metrics.json")
    if not metrics_path.exists():
        pytest.skip("reports/evaluation_metrics.json not generated yet.")

    payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    metrics = payload["metrics"]
    assert metrics["r2"] >= 0.75
    assert metrics["mape"] <= 30.0
    assert metrics["within_20pct"] >= 50.0


def test_model_monotonicity_with_area_and_bhk(fitted_sample_pipeline) -> None:
    artifact = Path("models/house_price_pipeline.joblib")
    pipe = load_pipeline(artifact) if artifact.exists() else fitted_sample_pipeline

    small = {
        "location": "bangalore",
        "area_sqft": 750.0,
        "bhk": 2,
        "bathroom": 2,
        "balcony": 1,
        "Transaction": "Resale",
    }
    large = {
        "location": "bangalore",
        "area_sqft": 2400.0,
        "bhk": 4,
        "bathroom": 4,
        "balcony": 2,
        "Transaction": "Resale",
    }
    p_small = float(predict_from_raw(pipe, small)[0])
    p_large = float(predict_from_raw(pipe, large)[0])

    assert p_small > 0 and np.isfinite(p_small)
    assert p_large > p_small
