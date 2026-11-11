"""Unit tests for Phase 16 retraining triggers, champion/challenger approval, and rollback."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.pipeline.inference_pipeline import predict_from_raw
from src.pipeline.training_pipeline import build_training_pipeline, load_pipeline
from src.retraining.retrain import (
    approve_model,
    check_retraining_trigger,
    compare_models,
    replace_production_model,
)
from src.retraining.scheduler import evaluate_and_run_scheduled_retraining
from src.retraining.versioning import list_model_versions, rollback_model, version_model


def _fit_tiny_pipeline(n_estimators: int = 20):
    df = pd.DataFrame(
        {
            "location": ["new-delhi", "bangalore", "ahmedabad"] * 6,
            "area_sqft": [1000.0 + i * 50.0 for i in range(18)],
            "bhk": [(i % 3) + 1 for i in range(18)],
            "bathroom": [(i % 3) + 1 for i in range(18)],
            "Transaction": ["Resale"] * 18,
            "Price_in_rupees": [7_000_000.0 + i * 300_000.0 for i in range(18)],
        }
    )
    pipe = build_training_pipeline(
        model_type="lightgbm",
        model_params={"n_estimators": n_estimators, "learning_rate": 0.1, "num_leaves": 8, "min_child_samples": 2},
        random_state=42,
    )
    pipe.fit(df.drop(columns=["Price_in_rupees"]), df["Price_in_rupees"])
    return pipe


def test_retraining_triggers_and_approval_gate() -> None:
    idle = check_retraining_trigger(
        drift_report={"overall_drift_detected": False},
        performance_alert={"alert_triggered": False},
        model_age_days=5.0,
    )
    assert idle["should_retrain"] is False

    triggered = check_retraining_trigger(
        drift_report={"overall_drift_detected": True, "drifted_feature_count": 3},
        performance_alert={"alert_triggered": True},
        model_age_days=35.0,
    )
    assert triggered["should_retrain"] is True
    assert len(triggered["reasons"]) == 3

    champ = {"r2": 0.81, "mae": 2_200_000.0}
    better_cand = {"r2": 0.83, "mae": 2_050_000.0}
    worse_cand = {"r2": 0.72, "mae": 2_900_000.0}

    comp = compare_models(champ, better_cand)
    assert comp["r2_delta"] == 0.02

    ok = approve_model(better_cand, champ)
    assert ok["approved"] is True

    rejected = approve_model(worse_cand, champ)
    assert rejected["approved"] is False
    assert len(rejected["reasons"]) >= 2


def test_versioning_promotion_and_rollback(tmp_path: Path) -> None:
    versions_dir = tmp_path / "versions"
    prod_path = tmp_path / "house_price_pipeline.joblib"

    p1 = _fit_tiny_pipeline(n_estimators=15)
    p2 = _fit_tiny_pipeline(n_estimators=35)

    sample = {"location": "bangalore", "area_sqft": 1200.0, "bhk": 2, "bathroom": 2}
    pred_v1 = float(predict_from_raw(p1, sample)[0])
    pred_v2 = float(predict_from_raw(p2, sample)[0])

    v1_entry = version_model(
        p1,
        metadata={"model_name": "lightgbm", "metrics": {"r2": 0.80}},
        versions_dir=versions_dir,
        explicit_version="0.1.0",
    )
    assert v1_entry["version"] == "0.1.0"

    swap = replace_production_model(
        p2,
        metadata={"model_name": "lightgbm", "metrics": {"r2": 0.83}},
        production_path=prod_path,
        versions_dir=versions_dir,
        bump="minor",
    )
    assert swap["model_version"] == "0.2.0"
    assert np.isclose(float(predict_from_raw(load_pipeline(prod_path), sample)[0]), pred_v2)

    versions = list_model_versions(versions_dir)
    assert [v["version"] for v in versions] == ["0.1.0", "0.2.0"]

    rb = rollback_model("0.1.0", versions_dir=versions_dir, production_path=prod_path)
    assert rb["active_version"] == "0.1.0"
    assert np.isclose(float(predict_from_raw(load_pipeline(prod_path), sample)[0]), pred_v1)


def test_scheduler_dry_run() -> None:
    res = evaluate_and_run_scheduled_retraining(dry_run=True)
    assert res["status"] == "dry_run"
    assert res["cron_schedule"] == "0 2 * * 0"
    assert "would_retrain" in res
