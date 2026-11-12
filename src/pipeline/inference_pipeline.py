"""Inference pipeline for predicting house prices from raw property payloads."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline


def load_pipeline(path: str | Path) -> Pipeline:
    """Load a serialized joblib pipeline artifact from disk."""
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"Pipeline artifact not found: {target}")
    return joblib.load(target)


def predict_from_raw(
    pipeline: Pipeline,
    raw_input: dict[str, Any] | list[dict[str, Any]] | pd.DataFrame,
) -> np.ndarray:
    """Predict non-negative house prices (INR) from raw dict, list of dicts, or DataFrame."""
    if isinstance(raw_input, dict):
        input_df = pd.DataFrame([raw_input])
    elif isinstance(raw_input, list):
        if not raw_input:
            raise ValueError("Input list for batch prediction must not be empty.")
        input_df = pd.DataFrame(raw_input)
    elif isinstance(raw_input, pd.DataFrame):
        if raw_input.empty:
            raise ValueError("Input DataFrame for prediction must not be empty.")
        input_df = raw_input.copy()
    else:
        raise TypeError(f"Unsupported input type for prediction: {type(raw_input).__name__}")

    preds = np.asarray(pipeline.predict(input_df), dtype=np.float64)
    return np.clip(preds, a_min=0.0, a_max=None)
