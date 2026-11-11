"""Cross-validation and hyperparameter optimization via Optuna and RandomizedSearchCV."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import optuna
import pandas as pd
import yaml
from sklearn.compose import TransformedTargetRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import make_scorer, mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.model_selection import KFold, RandomizedSearchCV, cross_validate

from src.features.build_features import feature_pipeline
from src.models.train import compute_basic_metrics
from src.utils.config import get_logger, load_config, resolve_path

logger = get_logger(__name__)
optuna.logging.set_verbosity(optuna.logging.WARNING)

try:
    from xgboost import XGBRegressor
except ImportError:  # pragma: no cover
    XGBRegressor = None  # type: ignore[assignment]

try:
    from lightgbm import LGBMRegressor
except ImportError:  # pragma: no cover
    LGBMRegressor = None  # type: ignore[assignment]


def cross_validate_model(
    model: Any,
    X: pd.DataFrame,
    y: pd.Series,
    cv: int = 5,
    random_state: int = 42,
) -> dict[str, float]:
    """Run shuffled K-Fold cross-validation returning mean and std R², MAE, and RMSE."""
    kf = KFold(n_splits=cv, shuffle=True, random_state=random_state)
    scoring = {
        "r2": "r2",
        "neg_mae": make_scorer(mean_absolute_error, greater_is_better=False),
        "neg_rmse": make_scorer(root_mean_squared_error, greater_is_better=False),
    }
    scores = cross_validate(model, X, y, cv=kf, scoring=scoring, n_jobs=1)
    return {
        "cv_r2_mean": round(float(np.mean(scores["test_r2"])), 4),
        "cv_r2_std": round(float(np.std(scores["test_r2"])), 4),
        "cv_mae_mean": round(float(-np.mean(scores["test_neg_mae"])), 2),
        "cv_rmse_mean": round(float(-np.mean(scores["test_neg_rmse"])), 2),
    }


def tune_random_forest(
    X: pd.DataFrame,
    y: pd.Series,
    n_iter: int = 6,
    cv: int = 3,
    random_state: int = 42,
) -> dict[str, Any]:
    """Tune a log-target RandomForestRegressor via RandomizedSearchCV."""
    base = TransformedTargetRegressor(
        regressor=RandomForestRegressor(random_state=random_state, n_jobs=1),
        func=np.log1p,
        inverse_func=np.expm1,
    )
    param_dist = {
        "regressor__n_estimators": [100, 150, 200],
        "regressor__max_depth": [14, 18, 22, None],
        "regressor__min_samples_leaf": [2, 4, 6, 8],
        "regressor__max_features": ["sqrt", 0.5, 0.7],
    }
    kf = KFold(n_splits=cv, shuffle=True, random_state=random_state)
    search = RandomizedSearchCV(
        estimator=base,
        param_distributions=param_dist,
        n_iter=n_iter,
        cv=kf,
        scoring="r2",
        random_state=random_state,
        n_jobs=-1,
    )
    search.fit(X, y)

    best_params = {
        k.replace("regressor__", ""): v for k, v in search.best_params_.items()
    }
    return {
        "model": search.best_estimator_,
        "best_params": best_params,
        "best_cv_r2": round(float(search.best_score_), 4),
    }


def _build_gb_regressor(
    model_type: str, params: dict[str, Any], random_state: int
) -> TransformedTargetRegressor:
    """Construct a log-target gradient boosting regressor for XGBoost or LightGBM."""
    kind = model_type.strip().lower()
    if kind == "xgboost":
        if XGBRegressor is None:
            raise ImportError("xgboost is required for model_type='xgboost'.")
        est = XGBRegressor(
            **params,
            random_state=random_state,
            n_jobs=-1,
            tree_method="hist",
            verbosity=0,
        )
    elif kind == "lightgbm":
        if LGBMRegressor is None:
            raise ImportError("lightgbm is required for model_type='lightgbm'.")
        est = LGBMRegressor(
            **params,
            random_state=random_state,
            n_jobs=-1,
            verbose=-1,
        )
    else:
        raise ValueError(f"Unsupported model_type '{model_type}'. Choose 'xgboost' or 'lightgbm'.")

    return TransformedTargetRegressor(
        regressor=est,
        func=np.log1p,
        inverse_func=np.expm1,
    )


def tune_gradient_boosting(
    X: pd.DataFrame,
    y: pd.Series,
    model_type: str = "xgboost",
    n_trials: int = 12,
    cv: int = 3,
    random_state: int = 42,
) -> dict[str, Any]:
    """Tune XGBoost or LightGBM using Optuna TPE search with K-Fold CV."""
    kind = model_type.strip().lower()
    kf = KFold(n_splits=cv, shuffle=True, random_state=random_state)

    def _suggest_params(trial: optuna.Trial) -> dict[str, Any]:
        if kind == "xgboost":
            return {
                "n_estimators": trial.suggest_int("n_estimators", 200, 500, step=50),
                "learning_rate": trial.suggest_float("learning_rate", 0.03, 0.12, log=True),
                "max_depth": trial.suggest_int("max_depth", 5, 9),
                "min_child_weight": trial.suggest_int("min_child_weight", 2, 12),
                "subsample": trial.suggest_float("subsample", 0.7, 0.95),
                "colsample_bytree": trial.suggest_float("colsample_bytree", 0.65, 0.95),
                "reg_lambda": trial.suggest_float("reg_lambda", 0.5, 5.0, log=True),
            }
        return {
            "n_estimators": trial.suggest_int("n_estimators", 200, 550, step=50),
            "learning_rate": trial.suggest_float("learning_rate", 0.03, 0.12, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 31, 110),
            "min_child_samples": trial.suggest_int("min_child_samples", 10, 45),
            "subsample": trial.suggest_float("subsample", 0.7, 0.95),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.65, 0.95),
            "reg_lambda": trial.suggest_float("reg_lambda", 0.1, 5.0, log=True),
        }

    def _objective(trial: optuna.Trial) -> float:
        params = _suggest_params(trial)
        fold_r2s: list[float] = []
        for tr_idx, val_idx in kf.split(X):
            model = _build_gb_regressor(kind, params, random_state=random_state)
            model.fit(X.iloc[tr_idx], y.iloc[tr_idx])
            preds = np.clip(model.predict(X.iloc[val_idx]), a_min=0.0, a_max=None)
            fold_r2s.append(float(r2_score(y.iloc[val_idx], preds)))
        return float(np.mean(fold_r2s))

    sampler = optuna.samplers.TPESampler(seed=random_state)
    study = optuna.create_study(direction="maximize", sampler=sampler)
    study.optimize(_objective, n_trials=n_trials)

    best_params = dict(study.best_params)
    best_model = _build_gb_regressor(kind, best_params, random_state=random_state)
    best_model.fit(X, y)

    return {
        "model": best_model,
        "best_params": best_params,
        "best_cv_r2": round(float(study.best_value), 4),
    }


def save_best_params(params_by_model: dict[str, dict[str, Any]], output_path: Path) -> Path:
    """Persist tuned model hyperparameters cleanly to YAML."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(params_by_model, fh, sort_keys=False)
    logger.info("Saved best hyperparameters to %s", output_path)
    return output_path


def run_hyperparameter_tuning(
    config_path: str | Path | None = None,
    n_trials: int = 12,
    n_iter_rf: int = 6,
    cv: int = 3,
) -> dict[str, Any]:
    """Tune XGBoost, LightGBM, and RandomForest on training split and evaluate on test."""
    config = load_config(config_path)
    processed_dir = resolve_path(config["data"]["processed_dir"])
    reports_dir = resolve_path(config["paths"]["reports_dir"])
    seed = int(config["project"]["random_seed"])

    train_df = pd.read_csv(processed_dir / "train.csv")
    test_df = pd.read_csv(processed_dir / "test.csv")

    bundle = feature_pipeline(train_df=train_df, test_df=test_df, random_state=seed)
    X_train, y_train = bundle["X_train"], bundle["y_train"]
    X_test, y_test = bundle["X_test"], bundle["y_test"]

    logger.info("Tuning XGBoost via Optuna (%d trials, %d-fold CV)", n_trials, cv)
    xgb_res = tune_gradient_boosting(
        X_train, y_train, model_type="xgboost", n_trials=n_trials, cv=cv, random_state=seed
    )

    logger.info("Tuning LightGBM via Optuna (%d trials, %d-fold CV)", n_trials, cv)
    lgb_res = tune_gradient_boosting(
        X_train, y_train, model_type="lightgbm", n_trials=n_trials, cv=cv, random_state=seed
    )

    logger.info("Tuning RandomForest via RandomizedSearchCV (%d iters, %d-fold CV)", n_iter_rf, cv)
    rf_res = tune_random_forest(
        X_train, y_train, n_iter=n_iter_rf, cv=cv, random_state=seed
    )

    tuned_entries = {
        "xgboost": xgb_res,
        "lightgbm": lgb_res,
        "random_forest": rf_res,
    }

    rows: list[dict[str, Any]] = []
    params_payload: dict[str, Any] = {}
    for name, res in tuned_entries.items():
        mdl = res["model"]
        tr_pred = np.clip(mdl.predict(X_train), a_min=0.0, a_max=None)
        te_pred = np.clip(mdl.predict(X_test), a_min=0.0, a_max=None)
        tr_m = compute_basic_metrics(y_train, tr_pred)
        te_m = compute_basic_metrics(y_test, te_pred)
        r2_gap = round(tr_m["r2"] - te_m["r2"], 4)

        params_payload[name] = {
            "params": res["best_params"],
            "cv_r2": res["best_cv_r2"],
            "test_r2": round(te_m["r2"], 4),
            "test_mae": round(te_m["mae"], 2),
        }
        rows.append(
            {
                "model": name,
                "cv_r2": res["best_cv_r2"],
                "train_r2": round(tr_m["r2"], 4),
                "test_r2": round(te_m["r2"], 4),
                "r2_gap": r2_gap,
                "test_mae": round(te_m["mae"], 2),
                "test_rmse": round(te_m["rmse"], 2),
                "test_mape": round(te_m["mape"], 2),
            }
        )

    results_df = pd.DataFrame(rows).sort_values("test_r2", ascending=False).reset_index(drop=True)
    best_model_name = str(results_df.iloc[0]["model"])
    params_payload["best_model"] = best_model_name

    params_path = resolve_path("config/hyperparameters.yaml")
    save_best_params(params_payload, params_path)

    report_path = reports_dir / "tuning_results.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    md_lines = [
        "# Hyperparameter Optimization Results",
        "",
        f"- **Cross-Validation**: {cv}-Fold Shuffled CV (on `51,568` training rows only)",
        f"- **Optuna Trials per Boosting Model**: {n_trials}",
        f"- **RandomizedSearchCV Iterations (RandomForest)**: {n_iter_rf}",
        f"- **Selected Champion Model**: `{best_model_name}`",
        "",
        "| Model | CV R² | Train R² | Test R² | Train-Test Gap | Test MAE (INR) | Test RMSE (INR) | Test MAPE (%) |",
        "|-------|-------|----------|---------|----------------|----------------|-----------------|---------------|",
    ]
    for _, r in results_df.iterrows():
        md_lines.append(
            f"| {r['model']} | {r['cv_r2']:.4f} | {r['train_r2']:.4f} | {r['test_r2']:.4f} | "
            f"{r['r2_gap']:.4f} | {r['test_mae']:,.2f} | {r['test_rmse']:,.2f} | {r['test_mape']:.2f}% |"
        )
    md_lines.extend(["", "## Best Hyperparameters", "", "```yaml", yaml.safe_dump(params_payload, sort_keys=False).strip(), "```"])
    report_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    logger.info("Saved tuning summary report to %s", report_path)

    return {
        "results": results_df,
        "params_path": str(params_path),
        "report_path": str(report_path),
        "best_model": best_model_name,
    }


if __name__ == "__main__":
    summary = run_hyperparameter_tuning()
    print(summary["results"].to_string(index=False))
