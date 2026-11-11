"""Cross-location model consistency and unseen-city robustness tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from src.pipeline.inference_pipeline import predict_from_raw
from src.pipeline.training_pipeline import load_pipeline

pytestmark = pytest.mark.model


def test_predictions_consistent_across_cities_and_unseen_city(fitted_sample_pipeline) -> None:
    artifact = Path("models/house_price_pipeline.joblib")
    pipe = load_pipeline(artifact) if artifact.exists() else fitted_sample_pipeline

    cities = [
        "mumbai",
        "new-delhi",
        "bangalore",
        "hyderabad",
        "chennai",
        "pune",
        "kolkata",
        "ahmedabad",
        "unseen-city-xyz",
    ]
    payloads = [
        {
            "location": city,
            "area_sqft": 1200.0,
            "bhk": 2,
            "bathroom": 2,
            "balcony": 1,
            "Transaction": "Resale",
            "Furnishing": "Semi-Furnished",
        }
        for city in cities
    ]
    preds = predict_from_raw(pipe, payloads)
    assert len(preds) == len(cities)
    assert np.isfinite(preds).all()
    assert (preds >= 300_000.0).all()
    assert (preds <= 200_000_000.0).all()

    # Metro Tier-1 markets should remain priced above smaller markets for identical 1200 sqft 2BHK
    pred_map = dict(zip(cities, preds, strict=True))
    assert pred_map["mumbai"] > pred_map["ahmedabad"]
