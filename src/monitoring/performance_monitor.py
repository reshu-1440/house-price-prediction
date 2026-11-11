"""Model performance tracking over time and degradation alerting."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.models.evaluate import compute_metrics
from src.utils.config import get_logger, load_config, resolve_path

logger = get_logger(__name__)


def load_monitoring_thresholds(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load monitoring thresholds YAML configuration."""
    target = (
        Path(config_path)
        if config_path is not None
        else resolve_path("config/monitoring_thresholds.yaml")
    )
    return load_config(target)


def track_performance(
    y_true: np.ndarray | pd.Series,
    y_pred: np.ndarray | pd.Series,
    timestamp: str | None = None,
    log_path: Path | None = None,
    n_features: int | None = None,
) -> dict[str, Any]:
    """Compute evaluation metrics and optionally append a timestamped JSONL entry."""
    metrics = compute_metrics(y_true, y_pred, n_features=n_features)
    record: dict[str, Any] = {
        "timestamp": timestamp or datetime.now(UTC).isoformat(),
        "sample_count": int(len(y_true)),
        "metrics": {k: round(float(v), 4) for k, v in metrics.items()},
    }
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
        logger.info("Appended performance metrics to %s", log_path)
    return record


def alert_on_degradation(
    metrics: dict[str, float],
    thresholds: dict[str, Any] | None = None,
    baseline_metrics: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Evaluate observed performance against configured thresholds and baseline R²."""
    cfg = thresholds if thresholds is not None else load_monitoring_thresholds().get("performance", {})
    reasons: list[str] = []

    min_r2 = float(cfg.get("min_r2", 0.70))
    max_mae = float(cfg.get("max_mae_inr", 3_000_000.0))
    max_mape = float(cfg.get("max_mape_pct", 30.0))
    max_drop = float(cfg.get("max_r2_drop_from_baseline", 0.08))

    r2 = float(metrics.get("r2", 0.0))
    mae = float(metrics.get("mae", float("inf")))
    mape = float(metrics.get("mape", float("inf")))

    if r2 < min_r2:
        reasons.append(f"R² ({r2:.4f}) dropped below minimum threshold ({min_r2:.4f})")
    if mae > max_mae:
        reasons.append(f"MAE (₹{mae:,.2f}) exceeded maximum threshold (₹{max_mae:,.2f})")
    if mape > max_mape:
        reasons.append(f"MAPE ({mape:.2f}%) exceeded maximum threshold ({max_mape:.2f}%)")

    if baseline_metrics is not None and "r2" in baseline_metrics:
        base_r2 = float(baseline_metrics["r2"])
        drop = base_r2 - r2
        if drop > max_drop:
            reasons.append(
                f"R² drop vs baseline ({drop:.4f}) exceeded allowed degradation ({max_drop:.4f})"
            )

    if reasons:
        logger.warning("Performance degradation alert triggered: %s", "; ".join(reasons))

    return {
        "alert_triggered": bool(reasons),
        "reasons": reasons,
        "evaluated_metrics": {k: round(float(v), 4) for k, v in metrics.items()},
    }
