"""Baseline and regression model training and benchmark comparison."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import TransformedTargetRegressor
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.exceptions import NotFittedError
from sklearn.linear_model import Lasso, LinearRegression, Ridge
from sklearn.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    r2_score,
    root_mean_squared_error,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeRegressor
from sklearn.utils.validation import check_is_fitted

from src.features.build_features import feature_pipeline
from src.utils.config import get_logger, load_config, resolve_path

logger = get_logger(__name__)

try:
    from xgboost import XGBRegressor
except ImportError:  # pragma: no cover - optional runtime dependency guard
    XGBRegressor = None  # type: ignore[assignment]

try:
    from lightgbm import LGBMRegressor
except ImportError:  # pragma: no cover - optional runtime dependency guard
    LGBMRegressor = None  # type: ignore[assignment]


def _wrap_log_target(estimator: Any, use_log_target: bool) -> Any:
    """Optionally wrap a regressor to fit in log1p target space and invert via expm1."""
    if not use_log_target:
        return estimator
    return TransformedTargetRegressor(
        regressor=estimator,
        func=np.log1p,
        inverse_func=np.expm1,
    )


def compute_basic_metrics(y_true: np.ndarray | pd.Series, y_pred: np.ndarray | pd.Series) -> dict[str, float]:
    """Compute MAE, RMSE, R², and MAPE (%) between ground truth and predictions."""
    y_t = np.asarray(y_true, dtype=np.float64)
    y_p = np.asarray(y_pred, dtype=np.float64)
    return {
        "mae": float(mean_absolute_error(y_t, y_p)),
        "rmse": float(root_mean_squared_error(y_t, y_p)),
        "r2": float(r2_score(y_t, y_p)),
        "mape": float(mean_absolute_percentage_error(y_t, y_p) * 100.0),
    }


def train_baseline(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    strategy: str = "median",
) -> DummyRegressor:
    """Train a constant baseline regressor (median by default)."""
    model = DummyRegressor(strategy=strategy)
    model.fit(X_train, y_train)
    return model


def train_linear_models(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    random_state: int = 42,
    use_log_target: bool = True,
) -> dict[str, Any]:
    """Train scaled Linear Regression, Ridge, and Lasso models."""
    specs = {
        "LinearRegression": LinearRegression(),
        "Ridge": Ridge(alpha=10.0, random_state=random_state),
        "Lasso": Lasso(alpha=0.001, max_iter=5000, random_state=random_state),
    }
    trained: dict[str, Any] = {}
    for name, est in specs.items():
        pipe = Pipeline([("scaler", StandardScaler()), ("reg", est)])
        model = _wrap_log_target(pipe, use_log_target=use_log_target)
        model.fit(X_train, y_train)
        trained[name] = model
    return trained


def train_decision_tree(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    max_depth: int = 12,
    min_samples_leaf: int = 10,
    random_state: int = 42,
    use_log_target: bool = True,
) -> Any:
    """Train a regularized Decision Tree regressor."""
    tree = DecisionTreeRegressor(
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        random_state=random_state,
    )
    model = _wrap_log_target(tree, use_log_target=use_log_target)
    model.fit(X_train, y_train)
    return model


def train_random_forest(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    n_estimators: int = 120,
    max_depth: int = 18,
    min_samples_leaf: int = 4,
    random_state: int = 42,
    n_jobs: int = -1,
    use_log_target: bool = True,
) -> Any:
    """Train a Random Forest regressor."""
    rf = RandomForestRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        random_state=random_state,
        n_jobs=n_jobs,
    )
    model = _wrap_log_target(rf, use_log_target=use_log_target)
    model.fit(X_train, y_train)
    return model


def train_gradient_boosting(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    random_state: int = 42,
    use_log_target: bool = True,
) -> dict[str, Any]:
    """Train HistGradientBoosting, XGBoost, and LightGBM regressors."""
    estimators: dict[str, Any] = {
        "HistGradientBoosting": HistGradientBoostingRegressor(
            max_iter=250,
            learning_rate=0.06,
            max_leaf_nodes=63,
            min_samples_leaf=20,
            random_state=random_state,
        )
    }
    if XGBRegressor is not None:
        estimators["XGBoost"] = XGBRegressor(
            n_estimators=300,
            learning_rate=0.06,
            max_depth=7,
            subsample=0.85,
            colsample_bytree=0.85,
            random_state=random_state,
            n_jobs=-1,
            tree_method="hist",
            verbosity=0,
        )
    if LGBMRegressor is not None:
        estimators["LightGBM"] = LGBMRegressor(
            n_estimators=300,
            learning_rate=0.06,
            num_leaves=63,
            subsample=0.85,
            colsample_bytree=0.85,
            random_state=random_state,
            n_jobs=-1,
            verbose=-1,
        )

    trained: dict[str, Any] = {}
    for name, est in estimators.items():
        model = _wrap_log_target(est, use_log_target=use_log_target)
        model.fit(X_train, y_train)
        trained[name] = model
    return trained


def compare_models(
    model_factories: dict[str, Any],
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    output_md_path: Path | None = None,
    output_fig_path: Path | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Train or evaluate models in ``model_factories``, rank by test R², and save report."""
    rows: list[dict[str, Any]] = []
    fitted_models: dict[str, Any] = {}

    for name, model_or_fn in model_factories.items():
        t0 = time.perf_counter()
        if callable(model_or_fn) and not hasattr(model_or_fn, "predict"):
            model = model_or_fn()
        else:
            model = model_or_fn
            try:
                check_is_fitted(model)
            except NotFittedError:
                model.fit(X_train, y_train)
        fit_secs = time.perf_counter() - t0

        tr_pred = np.clip(model.predict(X_train), a_min=0.0, a_max=None)
        te_pred = np.clip(model.predict(X_test), a_min=0.0, a_max=None)

        tr_m = compute_basic_metrics(y_train, tr_pred)
        te_m = compute_basic_metrics(y_test, te_pred)
        fitted_models[name] = model

        rows.append(
            {
                "model": name,
                "train_r2": round(tr_m["r2"], 4),
                "test_r2": round(te_m["r2"], 4),
                "test_mae": round(te_m["mae"], 2),
                "test_rmse": round(te_m["rmse"], 2),
                "test_mape": round(te_m["mape"], 2),
                "fit_time_sec": round(fit_secs, 3),
            }
        )

    results_df = pd.DataFrame(rows).sort_values("test_r2", ascending=False).reset_index(drop=True)

    if output_md_path is not None:
        output_md_path.parent.mkdir(parents=True, exist_ok=True)
        md_lines = [
            "# Model Comparison Benchmark",
            "",
            "| Rank | Model | Train R² | Test R² | Test MAE (INR) | Test RMSE (INR) | Test MAPE (%) | Fit Time (s) |",
            "|------|-------|----------|---------|----------------|-----------------|---------------|--------------|",
        ]
        for idx, r in results_df.iterrows():
            md_lines.append(
                f"| {idx + 1} | {r['model']} | {r['train_r2']:.4f} | {r['test_r2']:.4f} | "
                f"{r['test_mae']:,.2f} | {r['test_rmse']:,.2f} | {r['test_mape']:.2f}% | {r['fit_time_sec']:.3f} |"
            )
        output_md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
        logger.info("Saved model comparison report to %s", output_md_path)

    if output_fig_path is not None:
        output_fig_path.parent.mkdir(parents=True, exist_ok=True)
        fig, axes = plt.subplots(1, 2, figsize=(13, 5))

        ordered = results_df.sort_values("test_r2", ascending=True)
        axes[0].barh(ordered["model"], ordered["test_r2"], color="#2b6cb0")
        axes[0].set_title("Model Test R² Comparison")
        axes[0].set_xlabel("Test R²")

        axes[1].barh(ordered["model"], ordered["test_mae"] / 1e5, color="#38a169")
        axes[1].set_title("Model Test MAE (INR Lakhs)")
        axes[1].set_xlabel("Test MAE (INR Lakhs)")

        fig.tight_layout()
        fig.savefig(output_fig_path, dpi=150)
        plt.close(fig)
        logger.info("Saved model comparison plot to %s", output_fig_path)

    return results_df, fitted_models


def get_candidate_models(
    random_state: int = 42,
    use_log_target: bool = True,
) -> dict[str, Any]:
    """Build unfitted candidate regressors for fair timed benchmarking."""
    candidates: dict[str, Any] = {
        "Baseline_Median": DummyRegressor(strategy="median"),
        "LinearRegression": _wrap_log_target(
            Pipeline([("scaler", StandardScaler()), ("reg", LinearRegression())]),
            use_log_target=use_log_target,
        ),
        "Ridge": _wrap_log_target(
            Pipeline([("scaler", StandardScaler()), ("reg", Ridge(alpha=10.0, random_state=random_state))]),
            use_log_target=use_log_target,
        ),
        "Lasso": _wrap_log_target(
            Pipeline([("scaler", StandardScaler()), ("reg", Lasso(alpha=0.001, max_iter=5000, random_state=random_state))]),
            use_log_target=use_log_target,
        ),
        "DecisionTree": _wrap_log_target(
            DecisionTreeRegressor(max_depth=12, min_samples_leaf=10, random_state=random_state),
            use_log_target=use_log_target,
        ),
        "RandomForest": _wrap_log_target(
            RandomForestRegressor(
                n_estimators=120,
                max_depth=18,
                min_samples_leaf=4,
                random_state=random_state,
                n_jobs=-1,
            ),
            use_log_target=use_log_target,
        ),
        "HistGradientBoosting": _wrap_log_target(
            HistGradientBoostingRegressor(
                max_iter=250,
                learning_rate=0.06,
                max_leaf_nodes=63,
                min_samples_leaf=20,
                random_state=random_state,
            ),
            use_log_target=use_log_target,
        ),
    }
    if XGBRegressor is not None:
        candidates["XGBoost"] = _wrap_log_target(
            XGBRegressor(
                n_estimators=300,
                learning_rate=0.06,
                max_depth=7,
                subsample=0.85,
                colsample_bytree=0.85,
                random_state=random_state,
                n_jobs=-1,
                tree_method="hist",
                verbosity=0,
            ),
            use_log_target=use_log_target,
        )
    if LGBMRegressor is not None:
        candidates["LightGBM"] = _wrap_log_target(
            LGBMRegressor(
                n_estimators=300,
                learning_rate=0.06,
                num_leaves=63,
                subsample=0.85,
                colsample_bytree=0.85,
                random_state=random_state,
                n_jobs=-1,
                verbose=-1,
            ),
            use_log_target=use_log_target,
        )
    return candidates


def run_model_comparison(
    config_path: str | Path | None = None,
    track_mlflow: bool = False,
) -> pd.DataFrame:
    """Load processed splits, engineer features on train only, and compare regression models."""
    config = load_config(config_path)
    processed_dir = resolve_path(config["data"]["processed_dir"])
    reports_dir = resolve_path(config["paths"]["reports_dir"])
    figures_dir = resolve_path(config["paths"]["figures_dir"])
    seed = int(config["project"]["random_seed"])

    train_df = pd.read_csv(processed_dir / "train.csv")
    test_df = pd.read_csv(processed_dir / "test.csv")

    feat_bundle = feature_pipeline(train_df=train_df, test_df=test_df, random_state=seed)
    X_train = feat_bundle["X_train"]
    y_train = feat_bundle["y_train"]
    X_test = feat_bundle["X_test"]
    y_test = feat_bundle["y_test"]

    candidates = get_candidate_models(random_state=seed, use_log_target=True)

    results_df, fitted_models = compare_models(
        candidates,
        X_train=X_train,
        y_train=y_train,
        X_test=X_test,
        y_test=y_test,
        output_md_path=reports_dir / "model_comparison.md",
        output_fig_path=figures_dir / "model_comparison.png",
    )

    if track_mlflow:
        from src.models.mlflow_tracking import log_experiment, setup_mlflow

        setup_mlflow(config_path=config_path)
        for _, row in results_df.iterrows():
            m_name = str(row["model"])
            log_experiment(
                model=fitted_models[m_name],
                metrics={
                    "train_r2": float(row["train_r2"]),
                    "test_r2": float(row["test_r2"]),
                    "test_mae": float(row["test_mae"]),
                    "test_rmse": float(row["test_rmse"]),
                    "test_mape": float(row["test_mape"]),
                },
                params={"algorithm": m_name, "random_state": seed},
                run_name=f"benchmark_{m_name}",
                input_example=X_test.head(3),
                tags={"phase": "6_benchmark"},
            )
    return results_df


if __name__ == "__main__":
    summary = run_model_comparison()
    print(summary.to_string(index=False))
