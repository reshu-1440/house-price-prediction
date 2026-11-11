"""Reproducible end-to-end preprocessing and training pipeline."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import joblib
import numpy as np
import pandas as pd
import yaml
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from src.data.cleaning import (
    compute_outlier_bounds,
    deduplicate_listings,
    filter_valid_records,
    parse_area_columns,
    parse_car_parking,
    parse_price,
    remove_outliers,
)
from src.data.load_data import load_raw_data
from src.data.split import train_test_split_stratified, validate_no_leakage
from src.features.transformers import (
    DEFAULT_CATEGORICAL_COLUMNS,
    AreaFeatureBuilder,
    BHKExtractor,
    CategoricalEncoder,
    FeatureMatrixAligner,
    FloorExtractor,
    LocationEncoder,
    RawInputNormalizer,
)
from src.models.evaluate import compute_metrics
from src.models.hyperparameter_tuning import _build_gb_regressor
from src.utils.config import get_logger, load_config, resolve_path

logger = get_logger(__name__)


def build_preprocessor(
    categorical_cols: Iterable[str] = DEFAULT_CATEGORICAL_COLUMNS,
    smoothing: float = 20.0,
    random_state: int = 42,
) -> Pipeline:
    """Build the reproducible sklearn preprocessing pipeline from raw inputs to feature matrix."""
    imputer = SimpleImputer(strategy="median").set_output(transform="pandas")
    return Pipeline(
        steps=[
            ("normalizer", RawInputNormalizer()),
            ("bhk_extractor", BHKExtractor()),
            ("floor_extractor", FloorExtractor()),
            ("area_builder", AreaFeatureBuilder()),
            ("location_encoder", LocationEncoder(smoothing=smoothing, random_state=random_state)),
            ("categorical_encoder", CategoricalEncoder(columns=categorical_cols)),
            ("feature_aligner", FeatureMatrixAligner()),
            ("imputer", imputer),
        ]
    )


def build_training_pipeline(
    model: Any | None = None,
    model_type: str = "lightgbm",
    model_params: dict[str, Any] | None = None,
    random_state: int = 42,
) -> Pipeline:
    """Assemble full sklearn Pipeline from raw inputs through regression estimator."""
    if model is None:
        params = model_params or {}
        model = _build_gb_regressor(model_type, params=params, random_state=random_state)
    preprocessor = build_preprocessor(random_state=random_state)
    return Pipeline(steps=[("preprocessor", preprocessor), ("regressor", model)])


def save_pipeline(
    pipeline: Pipeline,
    path: str | Path,
    metadata: dict[str, Any] | None = None,
) -> Path:
    """Serialize a fitted pipeline with joblib and optional sidecar metadata JSON."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, target, compress=3)
    logger.info("Saved pipeline artifact to %s", target)

    if metadata is not None:
        meta_path = target.parent / "metadata.json"
        meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        logger.info("Saved pipeline metadata to %s", meta_path)

    return target


def load_pipeline(path: str | Path) -> Pipeline:
    """Load a serialized joblib pipeline artifact from disk."""
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"Pipeline artifact not found: {target}")
    return joblib.load(target)


def run_training_pipeline(
    config_path: str | Path | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Train end-to-end pipeline from raw CSV, evaluate on held-out split, and serialize."""
    config = load_config(config_path)
    data_cfg = config.get("data", {})
    split_cfg = config.get("splitting", {})
    seed = int(config["project"]["random_seed"])
    test_size = float(split_cfg.get("test_size", 0.2))
    valid_tx = tuple(data_cfg.get("valid_transactions", ("Resale", "New Property")))
    target_col = str(data_cfg.get("target_column", "Price_in_rupees"))

    hp_path = resolve_path("config/hyperparameters.yaml")
    with hp_path.open("r", encoding="utf-8") as fh:
        hp_cfg = yaml.safe_load(fh)
    best_name = str(hp_cfg.get("best_model", "lightgbm"))
    best_params = dict(hp_cfg[best_name]["params"])

    # Step 1: Load raw dataset and run deterministic row cleaning & target parsing
    raw_df = load_raw_data(config_path=config_path)
    step_df = deduplicate_listings(raw_df)
    step_df = parse_price(step_df)
    step_df = parse_area_columns(step_df)
    step_df = parse_car_parking(step_df)
    step_df = filter_valid_records(step_df, valid_transactions=valid_tx)
    step_df = step_df.drop_duplicates().reset_index(drop=True)

    # Step 2: Stratified split BEFORE train-only outlier filtering & pipeline fitting
    train_raw, test_raw = train_test_split_stratified(
        step_df, test_size=test_size, random_state=seed
    )
    train_bounds = compute_outlier_bounds(train_raw, factor=2.5)
    train_clean, _ = remove_outliers(train_raw, bounds=train_bounds)
    test_clean, _ = remove_outliers(test_raw, bounds=train_bounds)
    validate_no_leakage(train_clean, test_clean, check_index_disjoint=True)

    train_clean = train_clean.reset_index(drop=True)
    test_clean = test_clean.reset_index(drop=True)

    X_train_raw = train_clean.drop(columns=[target_col])
    y_train = train_clean[target_col].astype("float64")
    X_test_raw = test_clean.drop(columns=[target_col])
    y_test = test_clean[target_col].astype("float64")

    # Step 3: Fit unified sklearn Pipeline (preprocessing + tuned model)
    pipeline = build_training_pipeline(
        model_type=best_name,
        model_params=best_params,
        random_state=seed,
    )
    pipeline.fit(X_train_raw, y_train)

    # Step 4: Evaluate held-out test metrics
    y_pred = np.clip(pipeline.predict(X_test_raw), a_min=0.0, a_max=None)
    feature_names = list(pipeline.named_steps["preprocessor"].named_steps["feature_aligner"].feature_names_)
    metrics = compute_metrics(y_test, y_pred, n_features=len(feature_names))

    models_dir = resolve_path(config["paths"].get("models_dir", "models"))
    artifact_path = (
        Path(output_path) if output_path is not None else models_dir / "house_price_pipeline.joblib"
    )
    metadata = {
        "model_name": best_name,
        "model_version": config["project"].get("version", "0.1.0"),
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "train_samples": int(len(X_train_raw)),
        "test_samples": int(len(X_test_raw)),
        "feature_count": len(feature_names),
        "feature_names": feature_names,
        "hyperparameters": best_params,
        "metrics": {k: round(float(v), 4) for k, v in metrics.items()},
        "known_locations_count": int(train_clean["location"].nunique()),
    }
    save_pipeline(pipeline, artifact_path, metadata=metadata)

    return {
        "pipeline_path": str(artifact_path),
        "metadata": metadata,
    }


if __name__ == "__main__":
    summary = run_training_pipeline()
    print(json.dumps(summary["metadata"], indent=2))
