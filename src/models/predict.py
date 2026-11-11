"""Inference helpers for batch DataFrames and single raw property inputs."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.data.cleaning import handle_missing_values, parse_area_columns, parse_car_parking


def predict(model: Any, X: pd.DataFrame) -> np.ndarray:
    """Predict non-negative property prices in INR from an engineered feature DataFrame."""
    preds = np.asarray(model.predict(X), dtype=np.float64)
    return np.clip(preds, a_min=0.0, a_max=None)


def predict_single(
    model: Any,
    input_dict: dict[str, Any],
    transformers: dict[str, Any],
    feature_names: list[str],
    bathroom_median: float = 2.0,
) -> float:
    """Transform a single raw listing dictionary through fitted transformers and predict INR price."""
    raw_df = pd.DataFrame([input_dict])
    if "effective_area_sqft" not in raw_df.columns:
        raw_df = parse_area_columns(raw_df)
    if "parking_count" not in raw_df.columns:
        raw_df = parse_car_parking(raw_df)
    if "bathroom_count" not in raw_df.columns or "balcony_count" not in raw_df.columns:
        raw_df = handle_missing_values(raw_df, bathroom_median=bathroom_median)

    work = transformers["bhk_extractor"].transform(raw_df)
    work = transformers["floor_extractor"].transform(work)
    work = transformers["area_builder"].transform(work)
    work = transformers["location_encoder"].transform(work)
    work = transformers["categorical_encoder"].transform(work)

    for col in feature_names:
        if col not in work.columns:
            work[col] = 0.0

    X_single = work[feature_names].astype("float64")
    return float(predict(model, X_single)[0])
