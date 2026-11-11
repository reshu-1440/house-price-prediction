"""Data cleaning, unit normalization, deduplication, and outlier handling."""

from __future__ import annotations

import re
from typing import Any, Iterable

import numpy as np
import pandas as pd

from src.utils.config import get_logger

logger = get_logger(__name__)

PRICE_UNIT_MULTIPLIERS: dict[str, float] = {
    "cr": 1e7,
    "crore": 1e7,
    "lac": 1e5,
    "lakh": 1e5,
}

AREA_TO_SQFT: dict[str, float] = {
    "sqft": 1.0,
    "sqyrd": 9.0,
    "sqm": 10.7639,
    "acre": 43560.0,
    "marla": 272.25,
    "kanal": 5445.0,
    "ground": 2400.0,
    "cent": 435.56,
    "bigha": 27000.0,
    "biswa2": 1350.0,
    "aankadam": 72.0,
}

LEAKAGE_AND_DROP_COLUMNS: tuple[str, ...] = (
    "Index",
    "Price (in rupees)",
    "Dimensions",
    "Plot Area",
    "Amount(in rupees)",
    "Carpet Area",
    "Super Area",
)

CATEGORICAL_FILL_COLUMNS: tuple[str, ...] = (
    "Status",
    "Furnishing",
    "facing",
    "overlooking",
    "Society",
    "Ownership",
)


def parse_price_series(series: pd.Series) -> pd.Series:
    """Parse ``Amount(in rupees)`` strings into numeric INR, returning NaN for invalid entries."""
    text = series.astype("string").str.strip()
    is_call = text.str.contains("Call for Price", case=False, na=False)
    nums = pd.to_numeric(
        text.str.replace(",", "", regex=False).str.extract(r"([-+]?\d*\.?\d+)")[0],
        errors="coerce",
    )
    units = (
        text.str.extract(r"\b(cr|crore|lac|lakh)\b", flags=re.IGNORECASE)[0]
        .str.lower()
        .fillna("")
    )
    multipliers = units.map(PRICE_UNIT_MULTIPLIERS).fillna(1.0)
    parsed = (nums * multipliers).astype("float64")
    return parsed.where(~is_call & (parsed > 0), np.nan)


def parse_area_series(series: pd.Series) -> pd.Series:
    """Parse area strings (commas and regional units) into square feet."""
    text = series.astype("string").str.strip().str.replace(",", "", regex=False)
    nums = pd.to_numeric(text.str.extract(r"([-+]?\d*\.?\d+)")[0], errors="coerce")
    units = text.str.extract(r"[0-9.]+\s*([A-Za-z0-9]+)$")[0].str.lower().fillna("sqft")
    factors = units.map(AREA_TO_SQFT).fillna(np.nan)
    parsed = (nums * factors).astype("float64")
    return parsed.where(parsed > 0, np.nan)


def parse_count_series(series: pd.Series) -> pd.Series:
    """Parse count strings where ``> 10`` maps to 11.0."""
    text = series.astype("string").str.strip()
    mapped = text.replace({"> 10": "11", ">10": "11"})
    return pd.to_numeric(mapped, errors="coerce").astype("float64")


def parse_price(df: pd.DataFrame) -> pd.DataFrame:
    """Add numeric ``Price_in_rupees`` column parsed from ``Amount(in rupees)``."""
    out = df.copy()
    if "Amount(in rupees)" in out.columns:
        out["Price_in_rupees"] = parse_price_series(out["Amount(in rupees)"])
    return out


def parse_area_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Parse ``Carpet Area`` and ``Super Area`` into unified ``effective_area_sqft`` + ``area_type``."""
    out = df.copy()
    carpet = (
        parse_area_series(out["Carpet Area"])
        if "Carpet Area" in out.columns
        else pd.Series(np.nan, index=out.index, dtype="float64")
    )
    super_a = (
        parse_area_series(out["Super Area"])
        if "Super Area" in out.columns
        else pd.Series(np.nan, index=out.index, dtype="float64")
    )

    out["carpet_area_sqft"] = carpet
    out["super_area_sqft"] = super_a
    out["effective_area_sqft"] = carpet.fillna(super_a)
    out["area_type"] = np.where(
        carpet.notna(),
        "carpet",
        np.where(super_a.notna(), "super", "missing"),
    )
    return out


def parse_car_parking(df: pd.DataFrame) -> pd.DataFrame:
    """Extract numeric ``parking_count`` and ``parking_type`` from ``Car Parking``."""
    out = df.copy()
    if "Car Parking" not in out.columns:
        out["parking_count"] = 0.0
        out["parking_type"] = "Missing"
        return out

    raw = out["Car Parking"].astype("string").str.strip().str.rstrip(",")
    counts = pd.to_numeric(raw.str.extract(r"(\d+)")[0], errors="coerce").astype("float64")
    ptype = pd.Series("Missing", index=out.index, dtype="object")
    ptype = ptype.where(~raw.str.contains("Covered", case=False, na=False), "Covered")
    ptype = ptype.where(~raw.str.contains("Open", case=False, na=False), "Open")
    has_other = raw.notna() & (ptype == "Missing")
    ptype = ptype.where(~has_other, "Other")

    out["parking_count"] = counts.fillna(0.0).clip(lower=0.0)
    out["parking_type"] = ptype.astype(str)
    return out


def deduplicate_listings(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicate property listings excluding the sequential ``Index`` column."""
    subset = [c for c in df.columns if c != "Index"]
    deduped = df.drop_duplicates(subset=subset, keep="first").copy()
    removed = len(df) - len(deduped)
    if removed:
        logger.info("Removed %d duplicate rows (excluding Index) -> %d remaining", removed, len(deduped))
    return deduped


def filter_valid_records(
    df: pd.DataFrame,
    valid_transactions: Iterable[str] = ("Resale", "New Property"),
) -> pd.DataFrame:
    """Keep valid sale listings with positive target price and valid area, dropping leakage columns."""
    out = df.copy()
    valid_tx_norm = {str(v).strip().casefold() for v in valid_transactions}

    tx_clean = (
        out["Transaction"].astype("string").str.strip().str.casefold()
        if "Transaction" in out.columns
        else pd.Series("", index=out.index, dtype="string")
    )
    tx_mask = tx_clean.isin(valid_tx_norm)
    price_mask = out["Price_in_rupees"].notna() & (out["Price_in_rupees"] > 0)
    area_mask = out["effective_area_sqft"].notna() & (out["effective_area_sqft"] > 0)

    filtered = out.loc[tx_mask & price_mask & area_mask].copy()

    # Standardize Transaction casing cleanly
    filtered["Transaction"] = (
        filtered["Transaction"]
        .astype("string")
        .str.strip()
        .str.casefold()
        .map({"resale": "Resale", "new property": "New Property"})
        .fillna(filtered["Transaction"].astype(str).str.strip())
    )

    drop_cols = [c for c in LEAKAGE_AND_DROP_COLUMNS if c in filtered.columns]
    filtered = filtered.drop(columns=drop_cols)
    logger.info("Filtered valid records: %d -> %d rows", len(out), len(filtered))
    return filtered


def handle_missing_values(
    df: pd.DataFrame,
    bathroom_median: float | None = None,
) -> pd.DataFrame:
    """Parse count columns and handle missing values cleanly without dropping valid listings."""
    out = df.copy()

    if "Bathroom" in out.columns:
        out["bathroom_count"] = parse_count_series(out["Bathroom"])
    elif "bathroom_count" not in out.columns:
        out["bathroom_count"] = np.nan

    if "Balcony" in out.columns:
        out["balcony_count"] = parse_count_series(out["Balcony"]).fillna(0.0)
    elif "balcony_count" not in out.columns:
        out["balcony_count"] = 0.0

    # Replace non-positive bathroom values with NaN before median imputation
    out["bathroom_count"] = out["bathroom_count"].where(out["bathroom_count"] > 0, np.nan)
    computed_median = (
        float(bathroom_median)
        if bathroom_median is not None
        else (
            float(out["bathroom_count"].median())
            if out["bathroom_count"].notna().any()
            else 2.0
        )
    )
    out["bathroom_count"] = out["bathroom_count"].fillna(computed_median)
    out["balcony_count"] = out["balcony_count"].clip(lower=0.0)

    if "location" in out.columns:
        out["location"] = out["location"].astype(str).str.strip().str.lower()

    for col in CATEGORICAL_FILL_COLUMNS:
        if col in out.columns:
            out[col] = (
                out[col]
                .astype("string")
                .str.strip()
                .fillna("Missing")
                .replace({"": "Missing", "nan": "Missing", "None": "Missing"})
                .astype(str)
            )

    if "Description" in out.columns:
        out["Description"] = out["Description"].fillna("").astype(str)

    raw_count_cols = [c for c in ("Bathroom", "Balcony", "Car Parking") if c in out.columns]
    if raw_count_cols:
        out = out.drop(columns=raw_count_cols)

    return out


def compute_outlier_bounds(
    df: pd.DataFrame,
    columns: Iterable[str] = ("Price_in_rupees", "effective_area_sqft"),
    factor: float = 2.5,
) -> dict[str, tuple[float, float]]:
    """Compute log10-IQR bounds for positive numeric columns (fit on training data only)."""
    bounds: dict[str, tuple[float, float]] = {}
    for col in columns:
        if col not in df.columns:
            continue
        valid = pd.to_numeric(df[col], errors="coerce").dropna()
        valid = valid[valid > 0]
        if len(valid) < 4:
            continue
        log_vals = np.log10(valid)
        q1 = float(log_vals.quantile(0.25))
        q3 = float(log_vals.quantile(0.75))
        iqr = q3 - q1
        if iqr <= 0:
            continue
        lo = float(10 ** (q1 - factor * iqr))
        hi = float(10 ** (q3 + factor * iqr))
        bounds[col] = (lo, hi)
    return bounds


def remove_outliers(
    df: pd.DataFrame,
    bounds: dict[str, tuple[float, float]] | None = None,
    factor: float = 2.5,
) -> tuple[pd.DataFrame, dict[str, tuple[float, float]]]:
    """Filter rows outside log10-IQR bounds and return ``(cleaned_df, bounds)``."""
    active_bounds = bounds if bounds is not None else compute_outlier_bounds(df, factor=factor)
    mask = pd.Series(True, index=df.index)
    for col, (lo, hi) in active_bounds.items():
        if col in df.columns:
            mask &= df[col].between(lo, hi)
    cleaned = df.loc[mask].copy()
    removed = len(df) - len(cleaned)
    if removed:
        logger.info("Removed %d outlier rows -> %d remaining", removed, len(cleaned))
    return cleaned, active_bounds


def clean_pipeline(
    df: pd.DataFrame,
    valid_transactions: Iterable[str] = ("Resale", "New Property"),
    outlier_bounds: dict[str, tuple[float, float]] | None = None,
    bathroom_median: float | None = None,
    apply_outlier_filter: bool = True,
    outlier_factor: float = 2.5,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Run end-to-end data cleaning and return ``(cleaned_df, cleaning_metadata)``."""
    initial_rows = len(df)
    step_df = deduplicate_listings(df)
    after_dedup_rows = len(step_df)

    step_df = parse_price(step_df)
    step_df = parse_area_columns(step_df)
    step_df = parse_car_parking(step_df)
    step_df = filter_valid_records(step_df, valid_transactions=valid_transactions)
    after_filter_rows = len(step_df)

    step_df = handle_missing_values(step_df, bathroom_median=bathroom_median)

    used_bounds: dict[str, tuple[float, float]] = {}
    if apply_outlier_filter and not step_df.empty:
        step_df, used_bounds = remove_outliers(
            step_df, bounds=outlier_bounds, factor=outlier_factor
        )

    # Deduplicate once more on cleaned columns in case raw string formatting differences
    # (e.g. whitespace) collapsed into identical cleaned rows
    step_df = step_df.drop_duplicates().reset_index(drop=True)

    metadata: dict[str, Any] = {
        "initial_rows": initial_rows,
        "after_dedup_rows": after_dedup_rows,
        "after_filter_rows": after_filter_rows,
        "final_rows": len(step_df),
        "outlier_bounds": used_bounds,
        "bathroom_median_used": float(step_df["bathroom_count"].median())
        if not step_df.empty
        else 2.0,
    }
    return step_df, metadata
