"""Prediction distribution drift and anomaly monitoring."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from src.monitoring.data_drift import compute_psi


def monitor_predictions(
    reference_preds: np.ndarray | pd.Series,
    current_preds: np.ndarray | pd.Series,
    ks_pvalue_threshold: float = 0.01,
    psi_threshold: float = 0.25,
) -> dict[str, Any]:
    """Compare live prediction distribution against reference distribution."""
    ref = np.asarray(reference_preds, dtype=np.float64)
    cur = np.asarray(current_preds, dtype=np.float64)
    ref = ref[np.isfinite(ref)]
    cur = cur[np.isfinite(cur)]

    if len(ref) < 2 or len(cur) < 2:
        raise ValueError("Need at least 2 finite predictions in both reference and current sets.")

    ks_res = stats.ks_2samp(ref, cur)
    psi_val = compute_psi(ref, cur)
    ref_mean = float(np.mean(ref))
    cur_mean = float(np.mean(cur))
    mean_shift_pct = ((cur_mean - ref_mean) / max(abs(ref_mean), 1.0)) * 100.0
    drifted = bool(ks_res.pvalue < ks_pvalue_threshold or psi_val >= psi_threshold)

    return {
        "prediction_drift_detected": drifted,
        "ks_statistic": round(float(ks_res.statistic), 5),
        "p_value": round(float(ks_res.pvalue), 6),
        "psi": psi_val,
        "reference_mean_inr": round(ref_mean, 2),
        "current_mean_inr": round(cur_mean, 2),
        "reference_median_inr": round(float(np.median(ref)), 2),
        "current_median_inr": round(float(np.median(cur)), 2),
        "mean_shift_pct": round(mean_shift_pct, 2),
    }


def detect_prediction_anomalies(
    predictions: np.ndarray | pd.Series,
    reference_preds: np.ndarray | pd.Series | None = None,
    min_price_inr: float = 100_000.0,
    max_price_inr: float = 250_000_000.0,
    z_threshold: float = 3.5,
) -> dict[str, Any]:
    """Flag non-finite, out-of-range, and robust log-z-score anomalous predictions."""
    preds = np.asarray(predictions, dtype=np.float64)
    invalid_mask = ~np.isfinite(preds) | (preds < min_price_inr) | (preds > max_price_inr)

    z_anomaly_mask = np.zeros(len(preds), dtype=bool)
    if reference_preds is not None and len(reference_preds) >= 4:
        ref = np.asarray(reference_preds, dtype=np.float64)
        ref_valid = ref[np.isfinite(ref) & (ref > 0)]
        if len(ref_valid) >= 4:
            ref_log = np.log10(ref_valid)
            med = float(np.median(ref_log))
            mad = float(np.median(np.abs(ref_log - med)))
            scale = max(1.4826 * mad, float(np.std(ref_log)), 1e-6)
            cur_log = np.log10(np.clip(np.where(np.isfinite(preds), preds, 1.0), 1.0, None))
            z_scores = np.abs(cur_log - med) / scale
            z_anomaly_mask = z_scores > z_threshold

    combined_mask = invalid_mask | z_anomaly_mask
    anomaly_indices = np.where(combined_mask)[0].tolist()
    return {
        "total_predictions": int(len(preds)),
        "anomaly_count": int(len(anomaly_indices)),
        "anomaly_rate_pct": round((len(anomaly_indices) / max(len(preds), 1)) * 100.0, 2),
        "anomaly_indices": anomaly_indices,
        "out_of_bounds_count": int(invalid_mask.sum()),
        "z_score_anomaly_count": int(z_anomaly_mask.sum()),
    }
