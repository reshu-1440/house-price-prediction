"""Functional and end-to-end feature engineering pipeline wrappers."""

from __future__ import annotations

from typing import Any, Iterable

import pandas as pd

from src.features.transformers import (
    DEFAULT_CATEGORICAL_COLUMNS,
    AreaFeatureBuilder,
    BHKExtractor,
    CategoricalEncoder,
    FloorExtractor,
    LocationEncoder,
)
from src.utils.config import get_logger

logger = get_logger(__name__)

NUMERIC_FEATURE_COLUMNS: tuple[str, ...] = (
    "effective_area_sqft",
    "log_effective_area",
    "bathroom_count",
    "balcony_count",
    "parking_count",
    "bhk",
    "is_studio",
    "is_penthouse",
    "floor_number",
    "total_floors",
    "floor_ratio",
    "is_ground_floor",
    "is_top_floor",
    "area_per_bhk",
    "bathroom_per_bhk",
    "total_rooms_proxy",
    "bhk_x_log_area",
    "is_carpet_area",
    "has_society",
    "has_overlooking",
    "location_target_enc",
    "location_log_target_enc",
    "location_freq",
)


def extract_bhk(df: pd.DataFrame) -> pd.DataFrame:
    """Apply ``BHKExtractor`` standalone to a DataFrame."""
    return BHKExtractor().fit_transform(df)


def extract_floor_info(df: pd.DataFrame) -> pd.DataFrame:
    """Apply ``FloorExtractor`` standalone to a DataFrame."""
    return FloorExtractor().fit_transform(df)


def create_area_features(df: pd.DataFrame) -> pd.DataFrame:
    """Apply ``AreaFeatureBuilder`` (area + interaction features) to a DataFrame."""
    return AreaFeatureBuilder().fit_transform(df)


def create_interaction_features(df: pd.DataFrame) -> pd.DataFrame:
    """Alias for ``create_area_features`` creating BHK/area/bathroom interactions."""
    return AreaFeatureBuilder().fit_transform(df)


def feature_pipeline(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame | None = None,
    target_col: str = "Price_in_rupees",
    categorical_cols: Iterable[str] = DEFAULT_CATEGORICAL_COLUMNS,
    smoothing: float = 20.0,
    random_state: int = 42,
) -> dict[str, Any]:
    """Fit all feature transformers on ``train_df`` only and transform ``train_df`` and ``test_df``.

    Returns:
        Dictionary containing ``X_train``, ``y_train``, optional ``X_test`` / ``y_test``,
        ``feature_names``, and ``transformers`` (fitted instances).
    """
    if target_col not in train_df.columns:
        raise ValueError(f"Target column '{target_col}' not found in training DataFrame.")

    y_train = pd.to_numeric(train_df[target_col], errors="coerce").astype("float64")
    train_work = train_df.drop(columns=[target_col]).copy()

    bhk_ext = BHKExtractor()
    floor_ext = FloorExtractor()
    area_builder = AreaFeatureBuilder()
    loc_enc = LocationEncoder(smoothing=smoothing, random_state=random_state)
    cat_enc = CategoricalEncoder(columns=categorical_cols)

    train_work = bhk_ext.fit_transform(train_work)
    train_work = floor_ext.fit_transform(train_work)
    train_work = area_builder.fit_transform(train_work)
    train_work = loc_enc.fit_transform(train_work, y_train)
    train_work = cat_enc.fit_transform(train_work)

    feature_cols = [
        c for c in NUMERIC_FEATURE_COLUMNS if c in train_work.columns
    ] + cat_enc.encoded_feature_names_
    X_train = train_work[feature_cols].astype("float64").copy()

    result: dict[str, Any] = {
        "X_train": X_train,
        "y_train": y_train,
        "feature_names": feature_cols,
        "transformers": {
            "bhk_extractor": bhk_ext,
            "floor_extractor": floor_ext,
            "area_builder": area_builder,
            "location_encoder": loc_enc,
            "categorical_encoder": cat_enc,
        },
    }

    if test_df is not None:
        y_test = (
            pd.to_numeric(test_df[target_col], errors="coerce").astype("float64")
            if target_col in test_df.columns
            else None
        )
        test_work = test_df.drop(columns=[target_col], errors="ignore").copy()
        test_work = bhk_ext.transform(test_work)
        test_work = floor_ext.transform(test_work)
        test_work = area_builder.transform(test_work)
        test_work = loc_enc.transform(test_work)
        test_work = cat_enc.transform(test_work)
        result["X_test"] = test_work[feature_cols].astype("float64").copy()
        result["y_test"] = y_test

    logger.info("Engineered %d features for %d training samples", len(feature_cols), len(X_train))
    return result
