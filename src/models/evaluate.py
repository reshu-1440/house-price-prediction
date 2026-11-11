"""Comprehensive model evaluation, residual diagnostics, and error segmentation."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import yaml
from scipy import stats
from sklearn.metrics import median_absolute_error

from src.features.build_features import feature_pipeline
from src.models.hyperparameter_tuning import _build_gb_regressor
from src.models.predict import predict
from src.models.train import compute_basic_metrics
from src.utils.config import get_logger, load_config, resolve_path

logger = get_logger(__name__)


def compute_metrics(
    y_true: np.ndarray | pd.Series,
    y_pred: np.ndarray | pd.Series,
    n_features: int | None = None,
) -> dict[str, float]:
    """Compute regression metrics including MAE, RMSE, R², Adjusted R², MAPE, Median AE, and ±20% acc."""
    y_t = np.asarray(y_true, dtype=np.float64)
    y_p = np.asarray(y_pred, dtype=np.float64)
    metrics = compute_basic_metrics(y_t, y_p)
    metrics["median_ae"] = float(median_absolute_error(y_t, y_p))

    rel_err = np.abs(y_t - y_p) / np.maximum(np.abs(y_t), 1e-8)
    metrics["within_20pct"] = float(np.mean(rel_err <= 0.20) * 100.0)

    n = len(y_t)
    if n_features is not None and n > n_features + 1:
        metrics["adjusted_r2"] = float(1.0 - (1.0 - metrics["r2"]) * (n - 1) / (n - n_features - 1))
    else:
        metrics["adjusted_r2"] = metrics["r2"]
    return metrics


def plot_residuals(
    y_true: np.ndarray | pd.Series,
    y_pred: np.ndarray | pd.Series,
    output_path: Path,
) -> Path:
    """Plot residual scatter, log-residual distribution, and normal QQ plot."""
    y_t = np.asarray(y_true, dtype=np.float64)
    y_p = np.asarray(y_pred, dtype=np.float64)
    log_residuals = np.log10(np.maximum(y_t, 1.0)) - np.log10(np.maximum(y_p, 1.0))
    log_pred = np.log10(np.maximum(y_p, 1.0))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8))

    axes[0].scatter(log_pred, log_residuals, alpha=0.25, s=10, color="#2b6cb0")
    axes[0].axhline(0.0, color="#e53e3e", linestyle="--", linewidth=1.2)
    axes[0].set_title("Log10 Residuals vs. Predicted")
    axes[0].set_xlabel("log10(Predicted Price)")
    axes[0].set_ylabel("log10(Actual) - log10(Predicted)")

    sns.histplot(log_residuals, bins=40, kde=True, ax=axes[1], color="#38a169")
    axes[1].axvline(0.0, color="#e53e3e", linestyle="--", linewidth=1.2)
    axes[1].set_title("Log10 Residual Distribution")
    axes[1].set_xlabel("Log10 Residual")

    stats.probplot(log_residuals, dist="norm", plot=axes[2])
    axes[2].set_title("Normal Q-Q Plot (Log10 Residuals)")

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_actual_vs_predicted(
    y_true: np.ndarray | pd.Series,
    y_pred: np.ndarray | pd.Series,
    output_path: Path,
) -> Path:
    """Plot log10 Actual vs. Predicted scatter against ideal parity line."""
    y_t = np.asarray(y_true, dtype=np.float64)
    y_p = np.asarray(y_pred, dtype=np.float64)
    metrics = compute_metrics(y_t, y_p)

    log_t = np.log10(np.maximum(y_t, 1.0))
    log_p = np.log10(np.maximum(y_p, 1.0))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(log_t, log_p, alpha=0.25, s=12, color="#3182ce")
    lims = [min(float(log_t.min()), float(log_p.min())), max(float(log_t.max()), float(log_p.max()))]
    ax.plot(lims, lims, "r--", linewidth=1.5, label="Ideal Parity (y = x)")
    ax.set_xlim(lims)
    ax.set_ylim(lims)
    ax.set_xlabel("log10(Actual Price INR)")
    ax.set_ylabel("log10(Predicted Price INR)")
    ax.set_title(
        f"Actual vs. Predicted | R²={metrics['r2']:.4f}, MAE=₹{metrics['mae']/1e5:.2f}L"
    )
    ax.legend()

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def _segment_metrics_table(frame: pd.DataFrame, group_col: str, top_n: int | None = None) -> pd.DataFrame:
    """Compute grouped MAE, RMSE, MAPE, R², and count across ``group_col``."""
    rows = []
    counts = frame[group_col].value_counts()
    groups = counts.head(top_n).index.tolist() if top_n is not None else counts.index.tolist()

    for grp in groups:
        sub = frame.loc[frame[group_col] == grp]
        y_t = np.asarray(sub["y_true"], dtype=np.float64)
        y_p = np.asarray(sub["y_pred"], dtype=np.float64)
        if len(sub) < 2:
            mae = float(np.mean(np.abs(y_t - y_p)))
            rmse = float(np.sqrt(np.mean((y_t - y_p) ** 2)))
            mape = float(np.mean(np.abs(y_t - y_p) / np.maximum(np.abs(y_t), 1e-8)) * 100.0)
            r2_val: float | None = None
        else:
            m = compute_basic_metrics(y_t, y_p)
            mae, rmse, mape = m["mae"], m["rmse"], m["mape"]
            r2_val = round(m["r2"], 4)
        rows.append(
            {
                group_col: str(grp),
                "count": int(len(sub)),
                "mae": round(mae, 2),
                "rmse": round(rmse, 2),
                "mape": round(mape, 2),
                "r2": r2_val,
            }
        )
    return pd.DataFrame(rows)


def error_segmentation(
    y_true: np.ndarray | pd.Series,
    y_pred: np.ndarray | pd.Series,
    df: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Segment evaluation errors by price tier, top cities, transaction type, and BHK bucket."""
    work = df.copy().reset_index(drop=True)
    work["y_true"] = np.asarray(y_true, dtype=np.float64)
    work["y_pred"] = np.asarray(y_pred, dtype=np.float64)

    work["price_tier"] = pd.cut(
        work["y_true"],
        bins=[0.0, 5_000_000.0, 10_000_000.0, 25_000_000.0, float("inf")],
        labels=["< 50 Lac", "50 Lac - 1 Cr", "1 Cr - 2.5 Cr", "> 2.5 Cr"],
    ).astype(str)

    segments: dict[str, pd.DataFrame] = {
        "by_price_tier": _segment_metrics_table(work, "price_tier"),
    }
    if "location" in work.columns:
        segments["by_top_locations"] = _segment_metrics_table(work, "location", top_n=15)
    if "Transaction" in work.columns:
        segments["by_transaction"] = _segment_metrics_table(work, "Transaction")
    if "Title" in work.columns:
        bhk_extracted = pd.to_numeric(
            work["Title"].astype("string").str.extract(r"(\d+)\s*BHK", flags=re.IGNORECASE)[0],
            errors="coerce",
        ).astype("float64")
        bhk_vals = bhk_extracted.to_numpy(dtype=np.float64, na_value=np.nan)
        work["bhk_bucket"] = np.where(
            np.isnan(bhk_vals),
            "Other",
            np.where(bhk_vals >= 4.0, "4+ BHK", np.nan_to_num(bhk_vals, nan=0).astype(int).astype(str) + " BHK"),
        )
        segments["by_bhk"] = _segment_metrics_table(work, "bhk_bucket")
    return segments


def plot_feature_importance(
    model: Any,
    feature_names: list[str],
    output_path: Path,
    top_n: int = 20,
) -> pd.DataFrame:
    """Extract and plot top-N feature importances or linear coefficient magnitudes."""
    inner = getattr(model, "regressor_", model)
    if hasattr(inner, "named_steps") and "reg" in inner.named_steps:
        inner = inner.named_steps["reg"]

    if hasattr(inner, "feature_importances_"):
        importances = np.asarray(inner.feature_importances_, dtype=np.float64)
    elif hasattr(inner, "coef_"):
        importances = np.abs(np.asarray(inner.coef_, dtype=np.float64)).ravel()
    else:
        importances = np.zeros(len(feature_names), dtype=np.float64)

    imp_df = (
        pd.DataFrame({"feature": feature_names, "importance": importances})
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )
    top_df = imp_df.head(top_n).sort_values("importance", ascending=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(top_df["feature"], top_df["importance"], color="#2f855a")
    ax.set_title(f"Top {len(top_df)} Feature Importances")
    ax.set_xlabel("Importance")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return imp_df


def generate_evaluation_report(
    model: Any,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    raw_test_df: pd.DataFrame,
    feature_names: list[str],
    reports_dir: Path,
    figures_dir: Path,
    model_name: str = "lightgbm",
) -> dict[str, Any]:
    """Generate evaluation metrics JSON, Markdown report, diagnostic plots, and segmentation."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    y_pred = predict(model, X_test)
    metrics = compute_metrics(y_test, y_pred, n_features=len(feature_names))

    residuals_path = plot_residuals(y_test, y_pred, figures_dir / "residuals.png")
    parity_path = plot_actual_vs_predicted(y_test, y_pred, figures_dir / "actual_vs_predicted.png")
    imp_df = plot_feature_importance(model, feature_names, figures_dir / "feature_importance.png")
    segments = error_segmentation(y_test, y_pred, raw_test_df)

    metrics_payload = {
        "model": model_name,
        "test_samples": int(len(y_test)),
        "feature_count": int(len(feature_names)),
        "metrics": {k: round(float(v), 4) for k, v in metrics.items()},
        "top_10_features": imp_df.head(10).to_dict(orient="records"),
    }
    metrics_json_path = reports_dir / "evaluation_metrics.json"
    metrics_json_path.write_text(json.dumps(metrics_payload, indent=2), encoding="utf-8")

    lines = [
        f"# Model Evaluation Report — `{model_name}`",
        "",
        f"- **Held-out Test Samples**: {len(y_test):,}",
        f"- **Feature Count**: {len(feature_names)}",
        "",
        "## 1. Overall Test Metrics",
        f"- **R²**: {metrics['r2']:.4f}",
        f"- **Adjusted R²**: {metrics['adjusted_r2']:.4f}",
        f"- **MAE**: ₹{metrics['mae']:,.2f}",
        f"- **Median AE**: ₹{metrics['median_ae']:,.2f}",
        f"- **RMSE**: ₹{metrics['rmse']:,.2f}",
        f"- **MAPE**: {metrics['mape']:.2f}%",
        f"- **Predictions within ±20%**: {metrics['within_20pct']:.2f}%",
        "",
        "## 2. Error Segmentation by Price Tier",
        "",
        "| Price Tier | Count | MAE (INR) | RMSE (INR) | MAPE (%) | R² |",
        "|------------|-------|-----------|------------|----------|----|",
    ]
    for _, r in segments["by_price_tier"].iterrows():
        r2_str = f"{r['r2']:.4f}" if pd.notna(r["r2"]) else "N/A"
        lines.append(
            f"| {r['price_tier']} | {r['count']:,} | {r['mae']:,.2f} | {r['rmse']:,.2f} | {r['mape']:.2f}% | {r2_str} |"
        )

    if "by_top_locations" in segments:
        lines.extend(
            [
                "",
                "## 3. Error Segmentation Across Top 15 Cities",
                "",
                "| City | Count | MAE (INR) | RMSE (INR) | MAPE (%) | R² |",
                "|------|-------|-----------|------------|----------|----|",
            ]
        )
        for _, r in segments["by_top_locations"].iterrows():
            r2_str = f"{r['r2']:.4f}" if pd.notna(r["r2"]) else "N/A"
            lines.append(
                f"| {r['location']} | {r['count']:,} | {r['mae']:,.2f} | {r['rmse']:,.2f} | {r['mape']:.2f}% | {r2_str} |"
            )

    if "by_transaction" in segments:
        lines.extend(
            [
                "",
                "## 4. Error Segmentation by Transaction Type",
                "",
                "| Transaction | Count | MAE (INR) | RMSE (INR) | MAPE (%) | R² |",
                "|-------------|-------|-----------|------------|----------|----|",
            ]
        )
        for _, r in segments["by_transaction"].iterrows():
            r2_str = f"{r['r2']:.4f}" if pd.notna(r["r2"]) else "N/A"
            lines.append(
                f"| {r['Transaction']} | {r['count']:,} | {r['mae']:,.2f} | {r['rmse']:,.2f} | {r['mape']:.2f}% | {r2_str} |"
            )

    lines.extend(
        [
            "",
            "## 5. Top 10 Features by Importance",
            "",
            "| Feature | Importance |",
            "|---------|------------|",
        ]
    )
    for _, r in imp_df.head(10).iterrows():
        lines.append(f"| `{r['feature']}` | {r['importance']:.2f} |")

    lines.extend(
        [
            "",
            "## 6. Diagnostic Figures",
            f"- `{residuals_path.name}`",
            f"- `{parity_path.name}`",
            "- `feature_importance.png`",
        ]
    )

    report_md_path = reports_dir / "model_evaluation.md"
    report_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Saved evaluation report to %s", report_md_path)

    return {
        "metrics": metrics,
        "segments": segments,
        "feature_importance": imp_df,
        "report_path": str(report_md_path),
        "metrics_json_path": str(metrics_json_path),
    }


def run_model_evaluation(config_path: str | Path | None = None) -> dict[str, Any]:
    """Train the champion tuned model on processed splits and generate full evaluation report."""
    config = load_config(config_path)
    processed_dir = resolve_path(config["data"]["processed_dir"])
    reports_dir = resolve_path(config["paths"]["reports_dir"])
    figures_dir = resolve_path(config["paths"]["figures_dir"])
    seed = int(config["project"]["random_seed"])

    hp_path = resolve_path("config/hyperparameters.yaml")
    with hp_path.open("r", encoding="utf-8") as fh:
        hp_cfg = yaml.safe_load(fh)
    best_name = str(hp_cfg.get("best_model", "lightgbm"))
    best_params = dict(hp_cfg[best_name]["params"])

    train_df = pd.read_csv(processed_dir / "train.csv")
    test_df = pd.read_csv(processed_dir / "test.csv")

    bundle = feature_pipeline(train_df=train_df, test_df=test_df, random_state=seed)
    X_train, y_train = bundle["X_train"], bundle["y_train"]
    X_test, y_test = bundle["X_test"], bundle["y_test"]

    model = _build_gb_regressor(best_name, best_params, random_state=seed)
    model.fit(X_train, y_train)

    return generate_evaluation_report(
        model=model,
        X_test=X_test,
        y_test=y_test,
        raw_test_df=test_df,
        feature_names=bundle["feature_names"],
        reports_dir=reports_dir,
        figures_dir=figures_dir,
        model_name=f"{best_name}_tuned",
    )


if __name__ == "__main__":
    res = run_model_evaluation()
    print(json.dumps({k: round(v, 4) for k, v in res["metrics"].items()}, indent=2))
