"""Statistical data drift detection (KS test, PSI, Chi-squared) and reporting."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from src.utils.config import get_logger

logger = get_logger(__name__)


def compute_psi(
    reference: np.ndarray | pd.Series,
    current: np.ndarray | pd.Series,
    bins: int = 10,
) -> float:
    """Compute Population Stability Index (PSI) between reference and current numeric samples."""
    ref = pd.to_numeric(pd.Series(reference), errors="coerce").dropna().to_numpy(dtype=np.float64)
    cur = pd.to_numeric(pd.Series(current), errors="coerce").dropna().to_numpy(dtype=np.float64)
    if len(ref) == 0 or len(cur) == 0:
        return 0.0

    quantiles = np.linspace(0.0, 1.0, bins + 1)
    edges = np.unique(np.quantile(ref, quantiles))
    if len(edges) < 2:
        return 0.0

    edges[0] = -np.inf
    edges[-1] = np.inf

    ref_counts, _ = np.histogram(ref, bins=edges)
    cur_counts, _ = np.histogram(cur, bins=edges)

    eps = 1e-4
    ref_pct = np.clip(ref_counts / max(len(ref), 1), eps, None)
    cur_pct = np.clip(cur_counts / max(len(cur), 1), eps, None)
    ref_pct /= ref_pct.sum()
    cur_pct /= cur_pct.sum()

    psi_val = float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))
    return max(0.0, round(psi_val, 5))


def detect_data_drift(
    reference_df: pd.DataFrame,
    current_df: pd.DataFrame,
    numeric_cols: Iterable[str] | None = None,
    categorical_cols: Iterable[str] | None = None,
    ks_pvalue_threshold: float = 0.01,
    psi_threshold: float = 0.25,
    max_drifted_share: float = 0.30,
) -> dict[str, Any]:
    """Detect covariate shift between ``reference_df`` and ``current_df``."""
    common_cols = [c for c in reference_df.columns if c in current_df.columns]
    if numeric_cols is None:
        num_cols = [c for c in common_cols if pd.api.types.is_numeric_dtype(reference_df[c])]
    else:
        num_cols = [c for c in numeric_cols if c in common_cols]

    if categorical_cols is None:
        cat_cols = [
            c
            for c in common_cols
            if c not in num_cols and not pd.api.types.is_numeric_dtype(reference_df[c])
        ]
    else:
        cat_cols = [c for c in categorical_cols if c in common_cols]

    feature_results: list[dict[str, Any]] = []

    for col in num_cols:
        ref_s = pd.to_numeric(reference_df[col], errors="coerce").dropna()
        cur_s = pd.to_numeric(current_df[col], errors="coerce").dropna()
        if len(ref_s) < 2 or len(cur_s) < 2:
            continue
        ks_res = stats.ks_2samp(ref_s, cur_s)
        psi_val = compute_psi(ref_s, cur_s)
        drifted = bool(ks_res.pvalue < ks_pvalue_threshold or psi_val >= psi_threshold)
        feature_results.append(
            {
                "feature": col,
                "kind": "numeric",
                "statistic": round(float(ks_res.statistic), 5),
                "p_value": round(float(ks_res.pvalue), 6),
                "psi": psi_val,
                "drifted": drifted,
            }
        )

    for col in cat_cols:
        ref_counts = reference_df[col].astype(str).fillna("Missing").value_counts()
        cur_counts = current_df[col].astype(str).fillna("Missing").value_counts()
        categories = sorted(set(ref_counts.index) | set(cur_counts.index))
        if len(categories) < 2:
            continue
        ref_vec = np.array([ref_counts.get(cat, 0) for cat in categories], dtype=np.float64) + 1.0
        cur_vec = np.array([cur_counts.get(cat, 0) for cat in categories], dtype=np.float64) + 1.0
        ref_probs = ref_vec / ref_vec.sum()
        expected = ref_probs * cur_vec.sum()
        chi2_stat, p_val = stats.chisquare(f_obs=cur_vec, f_exp=expected)
        cur_probs = cur_vec / cur_vec.sum()
        cat_psi = float(np.sum((cur_probs - ref_probs) * np.log(cur_probs / ref_probs)))
        drifted = bool(p_val < ks_pvalue_threshold or cat_psi >= psi_threshold)
        feature_results.append(
            {
                "feature": col,
                "kind": "categorical",
                "statistic": round(float(chi2_stat), 4),
                "p_value": round(float(p_val), 6),
                "psi": round(max(0.0, cat_psi), 5),
                "drifted": drifted,
            }
        )

    total_checked = len(feature_results)
    drifted_count = sum(1 for r in feature_results if r["drifted"])
    drifted_share = round(drifted_count / total_checked, 4) if total_checked > 0 else 0.0
    overall_drift = bool(drifted_share >= max_drifted_share and drifted_count > 0)

    return {
        "overall_drift_detected": overall_drift,
        "drifted_feature_count": drifted_count,
        "total_features_checked": total_checked,
        "drifted_feature_share": drifted_share,
        "drifted_features": [r["feature"] for r in feature_results if r["drifted"]],
        "feature_results": feature_results,
    }


def generate_drift_report(
    drift_results: dict[str, Any],
    output_dir: Path,
) -> dict[str, str]:
    """Save JSON, Markdown, and PSI bar chart reports for data drift."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "data_drift_report.json"
    md_path = output_dir / "data_drift_report.md"
    fig_path = output_dir / "data_drift_psi.png"

    json_path.write_text(json.dumps(drift_results, indent=2), encoding="utf-8")

    lines = [
        "# Data Drift Monitoring Report",
        "",
        f"- **Overall Drift Detected**: `{drift_results['overall_drift_detected']}`",
        f"- **Drifted Features**: {drift_results['drifted_feature_count']} / {drift_results['total_features_checked']} "
        f"({drift_results['drifted_feature_share'] * 100:.1f}%)",
        "",
        "| Feature | Type | Statistic | p-value | PSI | Drifted |",
        "|---------|------|-----------|---------|-----|---------|",
    ]
    for r in drift_results.get("feature_results", []):
        lines.append(
            f"| `{r['feature']}` | {r['kind']} | {r['statistic']:.4f} | "
            f"{r['p_value']:.6f} | {r['psi']:.4f} | {r['drifted']} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    results_list = drift_results.get("feature_results", [])
    fig, ax = plt.subplots(figsize=(10, 5))
    if results_list:
        sorted_res = sorted(results_list, key=lambda x: x["psi"])[-15:]
        feats = [r["feature"] for r in sorted_res]
        psis = [r["psi"] for r in sorted_res]
        colors = ["#e53e3e" if r["drifted"] else "#3182ce" for r in sorted_res]
        ax.barh(feats, psis, color=colors)
        ax.axvline(0.25, color="#e53e3e", linestyle="--", label="Critical PSI (0.25)")
        ax.set_xlabel("Population Stability Index (PSI)")
        ax.set_title("Feature Drift Profile (PSI)")
        ax.legend()
    else:
        ax.text(0.5, 0.5, "No features evaluated", ha="center", va="center")
    fig.tight_layout()
    fig.savefig(fig_path, dpi=150)
    plt.close(fig)

    logger.info("Saved data drift reports to %s", output_dir)
    return {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
        "figure_path": str(fig_path),
    }
