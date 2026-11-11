"""MLflow experiment tracking, artifact logging, and model registry management."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
import yaml
from mlflow.models import infer_signature
from mlflow.tracking import MlflowClient

from src.features.build_features import feature_pipeline
from src.models.evaluate import compute_metrics
from src.models.hyperparameter_tuning import _build_gb_regressor
from src.models.predict import predict
from src.utils.config import get_logger, load_config, resolve_path

logger = get_logger(__name__)

DEFAULT_EXPERIMENT_NAME = "house_price_prediction"
DEFAULT_REGISTERED_MODEL_NAME = "house_price_regressor"


def _default_tracking_uris(mlflow_dir: Path) -> tuple[str, str]:
    """Return SQLite tracking URI and file:// artifact URI inside ``mlflow_dir``."""
    mlflow_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir = mlflow_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    db_path = (mlflow_dir / "mlflow.db").resolve()
    return f"sqlite:///{db_path.as_posix()}", artifacts_dir.resolve().as_uri()


def setup_mlflow(
    experiment_name: str = DEFAULT_EXPERIMENT_NAME,
    tracking_uri: str | None = None,
    artifact_location: str | None = None,
    config_path: str | Path | None = None,
) -> str:
    """Configure MLflow tracking URI and return active ``experiment_id``."""
    if tracking_uri is None:
        cfg = load_config(config_path)
        mlflow_dir = resolve_path(cfg["paths"].get("mlflow_dir", "mlflow_experiments"))
        default_uri, default_artifacts = _default_tracking_uris(mlflow_dir)
        tracking_uri = default_uri
        if artifact_location is None:
            artifact_location = default_artifacts

    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient(tracking_uri=tracking_uri)
    existing = client.get_experiment_by_name(experiment_name)
    if existing is None:
        exp_id = client.create_experiment(
            name=experiment_name, artifact_location=artifact_location
        )
        logger.info("Created MLflow experiment '%s' (id=%s)", experiment_name, exp_id)
    else:
        exp_id = existing.experiment_id
    mlflow.set_experiment(experiment_name)
    return str(exp_id)


def log_experiment(
    model: Any,
    metrics: dict[str, float],
    params: dict[str, Any],
    run_name: str | None = None,
    artifacts: Iterable[str | Path] | None = None,
    input_example: pd.DataFrame | None = None,
    registered_model_name: str | None = None,
    tags: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Log parameters, metrics, artifacts, and model to MLflow, returning run details."""
    clean_params = {
        str(k): (v if isinstance(v, (str, int, float, bool)) else str(v))
        for k, v in params.items()
    }
    clean_metrics = {
        str(k): float(v)
        for k, v in metrics.items()
        if v is not None and np.isfinite(float(v))
    }

    signature = None
    if input_example is not None and not input_example.empty:
        sample_preds = predict(model, input_example)
        signature = infer_signature(input_example, sample_preds)

    with mlflow.start_run(run_name=run_name) as run:
        if tags:
            mlflow.set_tags(tags)
        if clean_params:
            mlflow.log_params(clean_params)
        if clean_metrics:
            mlflow.log_metrics(clean_metrics)
        if artifacts:
            for artifact_path in artifacts:
                p = Path(artifact_path)
                if p.exists():
                    mlflow.log_artifact(str(p))

        model_info = mlflow.sklearn.log_model(
            sk_model=model,
            name="model",
            serialization_format=mlflow.sklearn.SERIALIZATION_FORMAT_CLOUDPICKLE,
            signature=signature,
            input_example=input_example,
        )

        registered_version: str | None = None
        if registered_model_name:
            mv = mlflow.register_model(model_info.model_uri, registered_model_name)
            registered_version = str(mv.version)

        logger.info(
            "Logged MLflow run %s (model_uri=%s, registered_version=%s)",
            run.info.run_id,
            model_info.model_uri,
            registered_version,
        )
        return {
            "run_id": run.info.run_id,
            "model_uri": model_info.model_uri,
            "registered_version": registered_version,
        }


def register_model(
    model_name: str,
    run_id_or_uri: str,
    artifact_path: str = "model",
) -> str:
    """Register a logged run or model URI under ``model_name`` and return its version."""
    model_uri = (
        run_id_or_uri
        if run_id_or_uri.startswith(("runs:/", "models:/"))
        else f"runs:/{run_id_or_uri}/{artifact_path}"
    )
    mv = mlflow.register_model(model_uri=model_uri, name=model_name)
    logger.info("Registered model '%s' version %s", model_name, mv.version)
    return str(mv.version)


def transition_model_stage(
    model_name: str,
    version: str | int,
    stage: str = "production",
) -> None:
    """Assign an MLflow 3.x alias (e.g., 'production', 'staging') and stage tag to ``version``."""
    alias = stage.strip().lower()
    client = MlflowClient()
    client.set_registered_model_alias(name=model_name, alias=alias, version=str(version))
    client.set_model_version_tag(
        name=model_name, version=str(version), key="stage", value=stage
    )
    logger.info("Assigned alias '@%s' to '%s' version %s", alias, model_name, version)


def load_production_model(
    model_name: str = DEFAULT_REGISTERED_MODEL_NAME,
    alias_or_version: str = "production",
) -> Any:
    """Load a registered sklearn model by alias (default '@production') or numeric version."""
    spec = str(alias_or_version).strip()
    uri = (
        f"models:/{model_name}/{spec}"
        if spec.isdigit()
        else f"models:/{model_name}@{spec.lower()}"
    )
    return mlflow.sklearn.load_model(uri)


def run_tracked_training(config_path: str | Path | None = None) -> dict[str, Any]:
    """Train tuned champion/challenger models, log to MLflow, register, and promote champion."""
    config = load_config(config_path)
    processed_dir = resolve_path(config["data"]["processed_dir"])
    reports_dir = resolve_path(config["paths"]["reports_dir"])
    figures_dir = resolve_path(config["paths"]["figures_dir"])
    seed = int(config["project"]["random_seed"])

    hp_path = resolve_path("config/hyperparameters.yaml")
    with hp_path.open("r", encoding="utf-8") as fh:
        hp_cfg = yaml.safe_load(fh)
    best_name = str(hp_cfg.get("best_model", "lightgbm"))

    train_df = pd.read_csv(processed_dir / "train.csv")
    test_df = pd.read_csv(processed_dir / "test.csv")

    bundle = feature_pipeline(train_df=train_df, test_df=test_df, random_state=seed)
    X_train, y_train = bundle["X_train"], bundle["y_train"]
    X_test, y_test = bundle["X_test"], bundle["y_test"]

    setup_mlflow(experiment_name=DEFAULT_EXPERIMENT_NAME, config_path=config_path)

    tracked_runs: dict[str, Any] = {}
    for candidate_name in ("xgboost", "lightgbm"):
        if candidate_name not in hp_cfg:
            continue
        params = dict(hp_cfg[candidate_name]["params"])
        model = _build_gb_regressor(candidate_name, params, random_state=seed)
        model.fit(X_train, y_train)
        preds = predict(model, X_test)
        metrics = compute_metrics(y_test, preds, n_features=len(bundle["feature_names"]))

        is_champ = candidate_name == best_name
        artifacts = (
            [
                reports_dir / "model_evaluation.md",
                reports_dir / "evaluation_metrics.json",
                figures_dir / "residuals.png",
                figures_dir / "actual_vs_predicted.png",
                figures_dir / "feature_importance.png",
            ]
            if is_champ
            else None
        )
        run_info = log_experiment(
            model=model,
            metrics=metrics,
            params={"algorithm": candidate_name, **params},
            run_name=f"{candidate_name}_tuned",
            artifacts=artifacts,
            input_example=X_test.head(5),
            registered_model_name=DEFAULT_REGISTERED_MODEL_NAME if is_champ else None,
            tags={"phase": "9", "champion": str(is_champ).lower()},
        )
        if is_champ and run_info["registered_version"] is not None:
            transition_model_stage(
                DEFAULT_REGISTERED_MODEL_NAME,
                version=run_info["registered_version"],
                stage="production",
            )
            reloaded = load_production_model(DEFAULT_REGISTERED_MODEL_NAME, "production")
            reloaded_preds = predict(reloaded, X_test.head(20))
            assert np.allclose(preds[:20], reloaded_preds), "Registry reloaded predictions differ!"
            run_info["registry_verified"] = True

        tracked_runs[candidate_name] = {
            **run_info,
            "metrics": {k: round(float(v), 4) for k, v in metrics.items()},
        }

    return tracked_runs


if __name__ == "__main__":
    summary = run_tracked_training()
    print(json.dumps(summary, indent=2))
