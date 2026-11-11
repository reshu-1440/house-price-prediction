"""Unit tests for Phase 15 data drift, prediction drift, performance monitor, and dashboard."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.monitoring.dashboard import generate_monitoring_dashboard
from src.monitoring.data_drift import compute_psi, detect_data_drift, generate_drift_report
from src.monitoring.performance_monitor import alert_on_degradation, track_performance
from src.monitoring.prediction_drift import detect_prediction_anomalies, monitor_predictions


def test_data_drift_detects_shift_and_passes_stable(tmp_path: Path) -> None:
    rng = np.random.default_rng(42)
    ref = pd.DataFrame(
        {
            "effective_area_sqft": rng.normal(1200.0, 200.0, size=300),
            "bhk": rng.choice([2, 3], size=300, p=[0.6, 0.4]),
            "Transaction": rng.choice(["Resale", "New Property"], size=300, p=[0.75, 0.25]),
        }
    )
    stable = pd.DataFrame(
        {
            "effective_area_sqft": rng.normal(1205.0, 195.0, size=300),
            "bhk": rng.choice([2, 3], size=300, p=[0.6, 0.4]),
            "Transaction": rng.choice(["Resale", "New Property"], size=300, p=[0.74, 0.26]),
        }
    )
    shifted = pd.DataFrame(
        {
            "effective_area_sqft": rng.normal(2400.0, 300.0, size=300),
            "bhk": rng.choice([4, 5], size=300),
            "Transaction": rng.choice(["Resale", "New Property"], size=300, p=[0.20, 0.80]),
        }
    )

    assert compute_psi(ref["effective_area_sqft"], stable["effective_area_sqft"]) < 0.1
    stable_res = detect_data_drift(ref, stable)
    assert stable_res["overall_drift_detected"] is False

    shifted_res = detect_data_drift(ref, shifted)
    assert shifted_res["overall_drift_detected"] is True
    assert shifted_res["drifted_feature_count"] >= 2

    files = generate_drift_report(shifted_res, tmp_path / "drift")
    assert Path(files["json_path"]).exists()
    assert Path(files["markdown_path"]).exists()
    assert Path(files["figure_path"]).exists()


def test_prediction_drift_anomalies_and_performance_alerts(tmp_path: Path) -> None:
    rng = np.random.default_rng(7)
    ref_preds = rng.normal(8_000_000.0, 1_200_000.0, size=200)
    shifted_preds = rng.normal(15_000_000.0, 2_000_000.0, size=200)

    pred_report = monitor_predictions(ref_preds, shifted_preds)
    assert pred_report["prediction_drift_detected"] is True
    assert pred_report["mean_shift_pct"] > 50.0

    anomalies = detect_prediction_anomalies(
        np.append(ref_preds[:20], [-500.0, 900_000_000.0]),
        reference_preds=ref_preds,
    )
    assert anomalies["anomaly_count"] >= 2

    y_true = np.array([5e6, 7e6, 9e6, 1.1e7, 1.3e7])
    good_pred = np.array([5.1e6, 6.9e6, 9.2e6, 1.08e7, 1.29e7])
    bad_pred = np.array([1.2e7, 2.0e6, 1.8e7, 4.0e6, 2.5e7])

    log_file = tmp_path / "perf.jsonl"
    good_rec = track_performance(y_true, good_pred, log_path=log_file)
    bad_rec = track_performance(y_true, bad_pred, log_path=log_file)
    assert len(log_file.read_text(encoding="utf-8").splitlines()) == 2

    ok_alert = alert_on_degradation(good_rec["metrics"])
    assert ok_alert["alert_triggered"] is False

    bad_alert = alert_on_degradation(
        bad_rec["metrics"],
        baseline_metrics=good_rec["metrics"],
    )
    assert bad_alert["alert_triggered"] is True
    assert len(bad_alert["reasons"]) >= 2

    dash_path = generate_monitoring_dashboard(
        drift_report={"overall_drift_detected": True, "drifted_feature_count": 2, "total_features_checked": 3, "feature_results": []},
        prediction_report=pred_report,
        performance_alert=bad_alert,
        output_path=tmp_path / "dashboard.html",
    )
    assert dash_path.exists()
    assert "ALERT TRIGGERED" in dash_path.read_text(encoding="utf-8")
