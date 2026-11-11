"""Unit tests for Phase 9 MLflow experiment tracking and model registry."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.features.build_features import feature_pipeline
from src.models.mlflow_tracking import (
    load_production_model,
    log_experiment,
    register_model,
    setup_mlflow,
    transition_model_stage,
)
from src.models.predict import predict
from src.models.train import train_gradient_boosting


def _make_mlflow_sample_df(n: int = 36) -> pd.DataFrame:
    """Create a synthetic dataset for MLflow tracking and registry tests."""
    rng = np.random.default_rng(19)
    cities = ["new-delhi", "bangalore", "ahmedabad"]
    rows = []
    for i in range(n):
        city = cities[i % len(cities)]
        bhk = (i % 3) + 1
        area = 600.0 + bhk * 340.0 + float(rng.normal(0, 30))
        price = area * 8500.0 + bhk * 200_000.0
        rows.append(
            {
                "Title": f"{bhk} BHK Flat",
                "Description": "desc",
                "location": city,
                "Status": "Ready to Move",
                "Floor": "2 out of 5",
                "Transaction": "Resale",
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


def test_mlflow_log_register_promote_and_reload(tmp_path: Path) -> None:
    db_uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"
    artifact_uri = (tmp_path / "artifacts").as_uri()
    exp_id = setup_mlflow(
        experiment_name="test_house_price",
        tracking_uri=db_uri,
        artifact_location=artifact_uri,
    )
    assert exp_id

    df = _make_mlflow_sample_df(36)
    bundle = feature_pipeline(train_df=df.iloc[:24], test_df=df.iloc[24:], random_state=42)
    model = train_gradient_boosting(bundle["X_train"], bundle["y_train"])["LightGBM"]
    expected_preds = predict(model, bundle["X_test"])

    note_file = tmp_path / "note.txt"
    note_file.write_text("experiment artifact", encoding="utf-8")

    run_info = log_experiment(
        model=model,
        metrics={"r2": 0.91, "mae": 250000.0},
        params={"n_estimators": 300, "algorithm": "lightgbm"},
        run_name="unit_test_run",
        artifacts=[note_file],
        input_example=bundle["X_test"].head(3),
    )
    assert run_info["run_id"]

    version = register_model("test_house_model", run_info["model_uri"])
    assert version == "1"

    transition_model_stage("test_house_model", version=version, stage="production")
    loaded = load_production_model("test_house_model", alias_or_version="production")
    loaded_preds = predict(loaded, bundle["X_test"])
    assert np.allclose(expected_preds, loaded_preds)
