"""Train/test splitting, geographical validation splits, and leakage verification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.model_selection import train_test_split

from src.data.cleaning import (
    compute_outlier_bounds,
    deduplicate_listings,
    filter_valid_records,
    handle_missing_values,
    parse_area_columns,
    parse_car_parking,
    parse_price,
    remove_outliers,
)
from src.data.load_data import load_raw_data
from src.data.validators import assert_valid, validate_cleaned_data
from src.utils.config import get_logger, load_config, resolve_path

logger = get_logger(__name__)


def create_price_bins(
    df: pd.DataFrame,
    target_col: str = "Price_in_rupees",
    n_bins: int = 5,
) -> pd.Series:
    """Create quantile-based price buckets for stratified splitting."""
    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found for binning.")
    prices = pd.to_numeric(df[target_col], errors="coerce")
    unique_vals = prices.nunique(dropna=True)
    effective_bins = max(1, min(n_bins, unique_vals))
    if effective_bins <= 1:
        return pd.Series(0, index=df.index, dtype="int64")
    bins = pd.qcut(prices, q=effective_bins, labels=False, duplicates="drop")
    return bins.fillna(0).astype("int64")


def train_test_split_stratified(
    df: pd.DataFrame,
    test_size: float = 0.2,
    random_state: int = 42,
    target_col: str = "Price_in_rupees",
    location_col: str = "location",
    n_price_bins: int = 5,
    min_stratum_count: int = 5,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split ``df`` into stratified train/test DataFrames preserving original indices."""
    if len(df) < 4:
        raise ValueError(f"Dataset too small to split: {len(df)} rows.")

    price_bins = create_price_bins(df, target_col=target_col, n_bins=n_price_bins)
    if location_col in df.columns:
        raw_strata = df[location_col].astype(str).str.lower() + "_" + price_bins.astype(str)
        counts = raw_strata.value_counts()
        rare_keys = counts[counts < min_stratum_count].index
        strata = raw_strata.where(~raw_strata.isin(rare_keys), other="rare_" + price_bins.astype(str))
    else:
        strata = price_bins.astype(str)

    # Collapse any remaining singleton strata so sklearn train_test_split never fails
    final_counts = strata.value_counts()
    singleton_keys = final_counts[final_counts < 2].index
    if len(singleton_keys) > 0:
        strata = strata.where(~strata.isin(singleton_keys), other="singleton_fallback")

    use_stratify = strata if (strata.value_counts().min() >= 2 and strata.nunique() > 1) else None
    n_test_est = int(np.floor(len(df) * test_size))
    if use_stratify is not None and n_test_est < use_stratify.nunique():
        use_stratify = (
            price_bins
            if (
                price_bins.value_counts().min() >= 2
                and price_bins.nunique() > 1
                and n_test_est >= price_bins.nunique()
            )
            else None
        )

    train_df, test_df = train_test_split(
        df,
        test_size=test_size,
        random_state=random_state,
        stratify=use_stratify,
    )
    logger.info(
        "Stratified split completed: train=%d (%.1f%%), test=%d (%.1f%%)",
        len(train_df),
        len(train_df) / len(df) * 100,
        len(test_df),
        len(test_df) / len(df) * 100,
    )
    return train_df.copy(), test_df.copy()


def geographical_split(
    df: pd.DataFrame,
    holdout_cities: Iterable[str],
    location_col: str = "location",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split dataset by holding out specific cities for unseen-geography validation."""
    if location_col not in df.columns:
        raise ValueError(f"Location column '{location_col}' not found.")

    holdout_norm = {str(c).strip().lower() for c in holdout_cities}
    loc_norm = df[location_col].astype(str).str.strip().str.lower()
    mask = loc_norm.isin(holdout_norm)
    in_domain = df.loc[~mask].copy()
    holdout = df.loc[mask].copy()

    if in_domain.empty or holdout.empty:
        raise ValueError(
            f"Geographical split resulted in empty partition (in_domain={len(in_domain)}, holdout={len(holdout)})."
        )
    logger.info(
        "Geographical split: in_domain=%d rows (%d cities), holdout=%d rows (%d cities)",
        len(in_domain),
        in_domain[location_col].nunique(),
        len(holdout),
        holdout[location_col].nunique(),
    )
    return in_domain, holdout


def validate_no_leakage(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    target_col: str = "Price_in_rupees",
    check_index_disjoint: bool = True,
) -> dict[str, Any]:
    """Assert zero index overlap, zero leakage columns, zero exact duplicates across splits."""
    if check_index_disjoint:
        overlap_idx = set(train_df.index).intersection(set(test_df.index))
        if overlap_idx:
            raise ValueError(f"Index leakage detected: {len(overlap_idx)} overlapping indices.")

    if "Price (in rupees)" in train_df.columns or "Price (in rupees)" in test_df.columns:
        raise ValueError("Forbidden leakage column 'Price (in rupees)' present in split.")

    common_cols = [c for c in train_df.columns if c in test_df.columns and c != "Index"]
    merged = pd.merge(
        train_df[common_cols].drop_duplicates(),
        test_df[common_cols].drop_duplicates(),
        on=common_cols,
        how="inner",
    )
    if not merged.empty:
        raise ValueError(
            f"Cross-split duplicate leakage detected: {len(merged)} identical records in train and test."
        )

    ks_stat: float | None = None
    ks_pvalue: float | None = None
    if target_col in train_df.columns and target_col in test_df.columns:
        tr_y = pd.to_numeric(train_df[target_col], errors="coerce").dropna()
        te_y = pd.to_numeric(test_df[target_col], errors="coerce").dropna()
        if len(tr_y) >= 2 and len(te_y) >= 2:
            res = stats.ks_2samp(tr_y, te_y)
            ks_stat = round(float(res.statistic), 5)
            ks_pvalue = round(float(res.pvalue), 5)

    return {
        "train_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
        "index_disjoint": True,
        "cross_split_duplicates": 0,
        "leakage_column_absent": True,
        "target_ks_statistic": ks_stat,
        "target_ks_pvalue": ks_pvalue,
    }


def save_splits(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    output_dir: Path,
    metadata: dict[str, Any] | None = None,
) -> tuple[Path, Path]:
    """Persist train and test splits (and optional metadata JSON) under ``output_dir``."""
    output_dir.mkdir(parents=True, exist_ok=True)
    train_path = output_dir / "train.csv"
    test_path = output_dir / "test.csv"

    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path, index=False)

    if metadata is not None:
        meta_path = output_dir / "split_metadata.json"
        with meta_path.open("w", encoding="utf-8") as fh:
            json.dump(metadata, fh, indent=2)

    logger.info("Saved processed splits to %s (%d train, %d test)", output_dir, len(train_df), len(test_df))
    return train_path, test_path


def run_split_pipeline(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load raw data, clean deterministically, split, fit train-only bounds/medians, and save."""
    config = load_config(config_path)
    split_cfg = config.get("splitting", {})
    data_cfg = config.get("data", {})

    test_size = float(split_cfg.get("test_size", 0.2))
    random_state = int(split_cfg.get("random_state", 42))
    valid_tx = tuple(data_cfg.get("valid_transactions", ("Resale", "New Property")))
    processed_dir = resolve_path(data_cfg.get("processed_dir", "data/processed"))

    raw_df = load_raw_data(config_path=config_path)

    # Step 1: Deterministic deduplication & parsing prior to splitting
    step_df = deduplicate_listings(raw_df)
    step_df = parse_price(step_df)
    step_df = parse_area_columns(step_df)
    step_df = parse_car_parking(step_df)
    step_df = filter_valid_records(step_df, valid_transactions=valid_tx)
    step_df = step_df.drop_duplicates().reset_index(drop=True)

    # Step 2: Stratified split BEFORE fitting any medians or outlier bounds
    train_raw, test_raw = train_test_split_stratified(
        step_df,
        test_size=test_size,
        random_state=random_state,
    )

    # Step 3: Impute missing values using TRAIN-ONLY bathroom median
    train_imputed = handle_missing_values(train_raw)
    train_bath_median = float(train_imputed["bathroom_count"].median())
    test_imputed = handle_missing_values(test_raw, bathroom_median=train_bath_median)

    # Step 4: Compute outlier bounds on TRAIN ONLY and apply to both splits
    train_bounds = compute_outlier_bounds(train_imputed, factor=2.5)
    train_clean, _ = remove_outliers(train_imputed, bounds=train_bounds)
    test_clean, _ = remove_outliers(test_imputed, bounds=train_bounds)

    # Step 5: Validate schema and cross-split leakage invariants BEFORE resetting indices
    leakage_report = validate_no_leakage(train_clean, test_clean, check_index_disjoint=True)
    train_clean = train_clean.reset_index(drop=True)
    test_clean = test_clean.reset_index(drop=True)

    assert_valid(validate_cleaned_data(train_clean))
    assert_valid(validate_cleaned_data(test_clean))

    metadata = {
        "test_size": test_size,
        "random_state": random_state,
        "train_bathroom_median": train_bath_median,
        "train_outlier_bounds": {
            k: [float(v[0]), float(v[1])] for k, v in train_bounds.items()
        },
        "leakage_checks": leakage_report,
    }
    train_path, test_path = save_splits(
        train_clean, test_clean, output_dir=processed_dir, metadata=metadata
    )
    return {
        "train_path": str(train_path),
        "test_path": str(test_path),
        "metadata": metadata,
    }


if __name__ == "__main__":
    result = run_split_pipeline()
    print(json.dumps(result["metadata"], indent=2))
