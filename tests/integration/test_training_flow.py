"""End-to-end integration test covering load -> clean -> split -> train -> save -> infer."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data.cleaning import clean_pipeline
from src.data.load_data import load_raw_data
from src.data.split import train_test_split_stratified, validate_no_leakage
from src.data.validators import assert_valid, validate_cleaned_data, validate_raw_schema
from src.pipeline.inference_pipeline import predict_from_raw
from src.pipeline.training_pipeline import build_training_pipeline, load_pipeline, save_pipeline

pytestmark = pytest.mark.integration


def test_end_to_end_training_and_inference_flow(sample_raw_df: pd.DataFrame, tmp_path: Path) -> None:
    # Expand synthetic raw dataset across 32 unique listings so split + CV + train run cleanly
    rng = np.random.default_rng(99)
    expanded_parts = []
    for copy_idx in range(4):
        part = sample_raw_df.copy()
        part["Index"] = np.arange(len(part)) + copy_idx * 100
        part["Title"] = part["Title"].astype(str) + f" Unit {copy_idx}"
        part["Carpet Area"] = np.where(
            part["Carpet Area"].notna(),
            (900 + copy_idx * 120 + rng.integers(10, 60, size=len(part))).astype(str) + " sqft",
            None,
        )
        expanded_parts.append(part)
    raw_df = pd.concat(expanded_parts, ignore_index=True)

    csv_path = tmp_path / "raw_sample.csv"
    raw_df.to_csv(csv_path, index=False)

    loaded = load_raw_data(data_path=csv_path)
    assert_valid(validate_raw_schema(loaded))

    cleaned, _ = clean_pipeline(loaded)
    assert_valid(validate_cleaned_data(cleaned))

    train_df, test_df = train_test_split_stratified(cleaned, test_size=0.25, random_state=42)
    validate_no_leakage(train_df, test_df, check_index_disjoint=True)

    pipe = build_training_pipeline(
        model_type="lightgbm",
        model_params={"n_estimators": 25, "learning_rate": 0.1, "num_leaves": 15, "min_child_samples": 2},
        random_state=42,
    )
    pipe.fit(train_df.drop(columns=["Price_in_rupees"]), train_df["Price_in_rupees"])

    model_path = tmp_path / "pipeline.joblib"
    save_pipeline(pipe, model_path, metadata={"model_name": "lightgbm"})
    reloaded = load_pipeline(model_path)

    preds = predict_from_raw(reloaded, test_df.drop(columns=["Price_in_rupees"]))
    assert len(preds) == len(test_df)
    assert (preds > 0).all()
    assert np.isfinite(preds).all()
