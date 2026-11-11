"""Automated retraining triggers, champion/challenger gating, and safe model swap."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import joblib

from src.pipeline.training_pipeline import run_training_pipeline
from src.retraining.versioning import version_model
from src.utils.config import get_logger, load_config, resolve_path

logger = get_logger(__name__)


def load_retraining_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load retraining configuration YAML."""
    target = Path(config_path) if config_path is not None else resolve_path("config/retraining.yaml")
    return load_config(target)


def check_retraining_trigger(
    drift_report: dict[str, Any] | None = None,
    performance_alert: dict[str, Any] | None = None,
    model_age_days: float | None = None,
    retraining_cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Determine whether retraining should run based on drift, performance, and model age."""
    cfg = retraining_cfg if retraining_cfg is not None else load_retraining_config()
    trig_cfg = cfg.get("triggers", {})
    reasons: list[str] = []

    if (
        trig_cfg.get("retrain_on_data_drift", True)
        and drift_report is not None
        and drift_report.get("overall_drift_detected")
    ):
        reasons.append(
            f"Data drift detected across {drift_report.get('drifted_feature_count', 0)} features"
        )

    if (
        trig_cfg.get("retrain_on_performance_alert", True)
        and performance_alert is not None
        and performance_alert.get("alert_triggered")
    ):
        reasons.append("Model performance degradation alert triggered")

    max_age = float(trig_cfg.get("max_model_age_days", 30))
    if model_age_days is not None and model_age_days >= max_age:
        reasons.append(f"Active model age ({model_age_days:.1f}d) reached max threshold ({max_age:.0f}d)")

    return {
        "should_retrain": bool(reasons),
        "reasons": reasons,
    }


def compare_models(
    champion_metrics: dict[str, float] | None,
    candidate_metrics: dict[str, float],
) -> dict[str, Any]:
    """Compute metric deltas between existing champion and newly trained challenger."""
    if not champion_metrics:
        return {
            "has_champion": False,
            "r2_delta": None,
            "mae_delta_pct": None,
            "candidate_metrics": candidate_metrics,
        }

    champ_r2 = float(champion_metrics.get("r2", 0.0))
    cand_r2 = float(candidate_metrics.get("r2", 0.0))
    champ_mae = float(champion_metrics.get("mae", float("inf")))
    cand_mae = float(candidate_metrics.get("mae", float("inf")))

    mae_delta_pct = (
        ((cand_mae - champ_mae) / champ_mae) * 100.0 if champ_mae > 0 and champ_mae < float("inf") else 0.0
    )
    return {
        "has_champion": True,
        "champion_r2": round(champ_r2, 4),
        "candidate_r2": round(cand_r2, 4),
        "r2_delta": round(cand_r2 - champ_r2, 4),
        "champion_mae": round(champ_mae, 2),
        "candidate_mae": round(cand_mae, 2),
        "mae_delta_pct": round(mae_delta_pct, 2),
    }


def approve_model(
    candidate_metrics: dict[str, float],
    champion_metrics: dict[str, float] | None = None,
    approval_criteria: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate challenger quality thresholds and champion/challenger non-regression gate."""
    criteria = (
        approval_criteria
        if approval_criteria is not None
        else load_retraining_config().get("approval", {})
    )
    reasons: list[str] = []

    min_r2 = float(criteria.get("min_r2", 0.75))
    max_mae = float(criteria.get("max_mae_inr", 2_800_000.0))
    min_r2_imp = float(criteria.get("min_r2_improvement_over_champion", -0.005))
    max_mae_reg = float(criteria.get("max_mae_regression_pct", 2.0))

    cand_r2 = float(candidate_metrics.get("r2", 0.0))
    cand_mae = float(candidate_metrics.get("mae", float("inf")))

    if cand_r2 < min_r2:
        reasons.append(f"Candidate R² ({cand_r2:.4f}) is below minimum threshold ({min_r2:.4f})")
    if cand_mae > max_mae:
        reasons.append(f"Candidate MAE (₹{cand_mae:,.2f}) exceeds maximum ({max_mae:,.2f})")

    comparison = compare_models(champion_metrics, candidate_metrics)
    if comparison["has_champion"]:
        r2_delta = float(comparison["r2_delta"])
        mae_delta_pct = float(comparison["mae_delta_pct"])
        if r2_delta < min_r2_imp:
            reasons.append(
                f"Candidate R² delta ({r2_delta:+.4f}) regressed beyond allowed ({min_r2_imp:+.4f})"
            )
        if mae_delta_pct > max_mae_reg:
            reasons.append(
                f"Candidate MAE regressed by {mae_delta_pct:+.2f}% (limit {max_mae_reg:.2f}%)"
            )

    approved = len(reasons) == 0
    return {
        "approved": approved,
        "reasons": reasons,
        "comparison": comparison,
    }


def replace_production_model(
    candidate_pipeline: Any,
    metadata: dict[str, Any],
    production_path: Path,
    versions_dir: Path | None = None,
    bump: str = "minor",
) -> dict[str, Any]:
    """Version the approved candidate and atomically swap it into ``production_path``."""
    production_path.parent.mkdir(parents=True, exist_ok=True)
    final_meta = dict(metadata)

    version_entry: dict[str, Any] | None = None
    if versions_dir is not None:
        version_entry = version_model(
            pipeline=candidate_pipeline,
            metadata=final_meta,
            versions_dir=versions_dir,
            bump=bump,
        )
        final_meta["model_version"] = version_entry["version"]

    tmp_model = production_path.with_suffix(".joblib.tmp")
    joblib.dump(candidate_pipeline, tmp_model, compress=3)
    os.replace(tmp_model, production_path)

    meta_path = production_path.parent / "metadata.json"
    tmp_meta = meta_path.with_suffix(".json.tmp")
    tmp_meta.write_text(json.dumps(final_meta, indent=2), encoding="utf-8")
    os.replace(tmp_meta, meta_path)

    logger.info("Promoted model v%s to production path %s", final_meta.get("model_version"), production_path)
    return {
        "production_path": str(production_path),
        "metadata_path": str(meta_path),
        "model_version": final_meta.get("model_version"),
        "version_entry": version_entry,
    }


def retrain_model(
    config_path: str | Path | None = None,
    retraining_config_path: str | Path | None = None,
    force: bool = False,
    drift_report: dict[str, Any] | None = None,
    performance_alert: dict[str, Any] | None = None,
    model_age_days: float | None = None,
) -> dict[str, Any]:
    """Execute retraining workflow with trigger checks, candidate training, and approval gate."""
    retrain_cfg = load_retraining_config(retraining_config_path)
    ver_cfg = retrain_cfg.get("versioning", {})

    prod_path = resolve_path(ver_cfg.get("production_path", "models/house_price_pipeline.joblib"))
    versions_dir = resolve_path(ver_cfg.get("versions_dir", "models/versions"))

    trigger = check_retraining_trigger(
        drift_report=drift_report,
        performance_alert=performance_alert,
        model_age_days=model_age_days,
        retraining_cfg=retrain_cfg,
    )
    if not force and not trigger["should_retrain"]:
        logger.info("Retraining skipped: no trigger condition met.")
        return {"status": "skipped", "trigger": trigger}

    # Snapshot existing champion metadata before training candidate into temp path
    prod_meta_path = prod_path.parent / "metadata.json"
    champion_metrics: dict[str, float] | None = None
    if prod_meta_path.exists():
        champ_meta = json.loads(prod_meta_path.read_text(encoding="utf-8"))
        champion_metrics = champ_meta.get("metrics")

    candidate_tmp_path = prod_path.parent / "candidate_pipeline.joblib"
    train_result = run_training_pipeline(config_path=config_path, output_path=candidate_tmp_path)
    candidate_meta = train_result["metadata"]
    candidate_pipeline = joblib.load(candidate_tmp_path)

    approval = approve_model(
        candidate_metrics=candidate_meta["metrics"],
        champion_metrics=champion_metrics,
        approval_criteria=retrain_cfg.get("approval"),
    )

    if not approval["approved"]:
        candidate_tmp_path.unlink(missing_ok=True)
        logger.warning("Candidate model rejected: %s", "; ".join(approval["reasons"]))
        return {
            "status": "rejected",
            "trigger": trigger,
            "approval": approval,
            "candidate_metrics": candidate_meta["metrics"],
        }

    swap_info = replace_production_model(
        candidate_pipeline=candidate_pipeline,
        metadata=candidate_meta,
        production_path=prod_path,
        versions_dir=versions_dir,
        bump="minor",
    )
    candidate_tmp_path.unlink(missing_ok=True)

    return {
        "status": "promoted",
        "trigger": trigger,
        "approval": approval,
        "promotion": swap_info,
        "candidate_metrics": candidate_meta["metrics"],
    }
