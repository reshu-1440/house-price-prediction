"""Scheduled retraining runner for cron / CI execution."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.retraining.retrain import (
    check_retraining_trigger,
    load_retraining_config,
    retrain_model,
)
from src.utils.config import get_logger, resolve_path

logger = get_logger(__name__)


def compute_model_age_days(metadata_path: Path) -> float | None:
    """Compute elapsed days since ``trained_at_utc`` in ``metadata_path``."""
    if not metadata_path.exists():
        return None
    meta = json.loads(metadata_path.read_text(encoding="utf-8"))
    ts = meta.get("trained_at_utc")
    if not ts:
        return None
    trained_dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    if trained_dt.tzinfo is None:
        trained_dt = trained_dt.replace(tzinfo=UTC)
    delta = datetime.now(UTC) - trained_dt
    return max(0.0, delta.total_seconds() / 86400.0)


def evaluate_and_run_scheduled_retraining(
    config_path: str | Path | None = None,
    retraining_config_path: str | Path | None = None,
    drift_report: dict[str, Any] | None = None,
    performance_alert: dict[str, Any] | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Evaluate schedule/triggers and optionally run automated retraining."""
    retrain_cfg = load_retraining_config(retraining_config_path)
    prod_path = resolve_path(
        retrain_cfg.get("versioning", {}).get("production_path", "models/house_price_pipeline.joblib")
    )
    age_days = compute_model_age_days(prod_path.parent / "metadata.json")

    trigger = check_retraining_trigger(
        drift_report=drift_report,
        performance_alert=performance_alert,
        model_age_days=age_days,
        retraining_cfg=retrain_cfg,
    )

    if dry_run:
        return {
            "status": "dry_run",
            "cron_schedule": retrain_cfg.get("schedule", {}).get("cron"),
            "model_age_days": round(age_days, 3) if age_days is not None else None,
            "trigger": trigger,
            "would_retrain": bool(force or trigger["should_retrain"]),
        }

    return retrain_model(
        config_path=config_path,
        retraining_config_path=retraining_config_path,
        force=force,
        drift_report=drift_report,
        performance_alert=performance_alert,
        model_age_days=age_days,
    )


def main() -> None:
    """CLI entrypoint for scheduled retraining checks."""
    parser = argparse.ArgumentParser(description="Evaluate and run scheduled model retraining.")
    parser.add_argument("--force", action="store_true", help="Force retraining regardless of triggers.")
    parser.add_argument("--dry-run", action="store_true", help="Evaluate triggers without training.")
    args = parser.parse_args()

    result = evaluate_and_run_scheduled_retraining(force=args.force, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
