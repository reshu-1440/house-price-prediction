"""Centralized raw dataset loader and overview diagnostics."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pandas as pd

from src.utils.config import get_logger, load_config, resolve_path

logger = get_logger(__name__)

REQUIRED_RAW_COLUMNS: tuple[str, ...] = (
    "Index",
    "Title",
    "Description",
    "Amount(in rupees)",
    "Price (in rupees)",
    "location",
    "Carpet Area",
    "Status",
    "Floor",
    "Transaction",
    "Furnishing",
    "facing",
    "overlooking",
    "Society",
    "Bathroom",
    "Balcony",
    "Car Parking",
    "Ownership",
    "Super Area",
    "Dimensions",
    "Plot Area",
)


def _validate_raw_columns(df: pd.DataFrame) -> None:
    """Ensure all expected raw dataset columns exist in ``df``."""
    missing = [col for col in REQUIRED_RAW_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Raw dataset is missing required columns: {missing}")


def load_raw_data(
    config_path: str | Path | None = None,
    data_path: str | Path | None = None,
    cities: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Load the raw house prices CSV safely without modifying the source file.

    Args:
        config_path: Optional path to YAML config. Uses ``config/config.yaml`` by default.
        data_path: Optional explicit CSV path overriding ``config['data']['raw_path']``.
        cities: Optional city slug filter overriding ``config['data']['cities']``.

    Returns:
        DataFrame loaded from ``Data/house_prices.csv`` (optionally filtered by city).
    """
    config = load_config(config_path)
    data_cfg = config.get("data", {})

    raw_rel = data_path if data_path is not None else data_cfg.get("raw_path")
    if not raw_rel:
        raise ValueError("Raw dataset path is missing from config['data']['raw_path'].")

    csv_path = resolve_path(raw_rel)
    if not csv_path.exists():
        raise FileNotFoundError(f"Raw dataset file not found: {csv_path}")

    logger.info("Loading raw dataset from %s", csv_path)
    df = pd.read_csv(csv_path, low_memory=False)
    if df.empty:
        raise ValueError(f"Loaded dataset from {csv_path} is empty.")

    _validate_raw_columns(df)

    active_cities = list(cities) if cities is not None else data_cfg.get("cities")
    if active_cities:
        normalized = [str(c).strip().lower() for c in active_cities]
        df = df.loc[df["location"].astype(str).str.strip().str.lower().isin(normalized)].copy()
        logger.info("Filtered to %d cities -> %d rows", len(normalized), len(df))

    logger.info(
        "Loaded dataset with shape (%d, %d) across %d locations",
        df.shape[0],
        df.shape[1],
        df["location"].nunique(),
    )
    return df


def get_dataset_overview(df: pd.DataFrame) -> dict[str, Any]:
    """Return key structural metrics for a loaded raw DataFrame."""
    cols_except_index = [c for c in df.columns if c != "Index"]
    return {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "column_names": list(df.columns),
        "unique_locations": int(df["location"].nunique()) if "location" in df.columns else 0,
        "memory_mb": round(float(df.memory_usage(deep=True).sum()) / (1024 * 1024), 2),
        "exact_duplicates_all_cols": int(df.duplicated().sum()),
        "duplicates_excluding_index": int(df.duplicated(subset=cols_except_index).sum()),
        "null_counts": {str(k): int(v) for k, v in df.isnull().sum().items()},
    }


if __name__ == "__main__":
    raw_df = load_raw_data()
    overview = get_dataset_overview(raw_df)
    print(f"Rows: {overview['rows']} | Columns: {overview['columns']}")
    print(f"Unique locations: {overview['unique_locations']}")
    print(f"Duplicates (all cols): {overview['exact_duplicates_all_cols']}")
    print(f"Duplicates (excluding Index): {overview['duplicates_excluding_index']}")
    print(f"Memory usage: {overview['memory_mb']} MB")
