"""Unit tests for Phase 5 train/test splitting and leakage validation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data.split import (
    create_price_bins,
    geographical_split,
    save_splits,
    train_test_split_stratified,
    validate_no_leakage,
)


def _make_split_sample_df(n_per_city: int = 10) -> pd.DataFrame:
    """Create a deterministic cleaned DataFrame across 3 cities."""
    rng = np.random.default_rng(42)
    rows = []
    cities = ["new-delhi", "bangalore", "ahmedabad"]
    for city_idx, city in enumerate(cities):
        base_price = (city_idx + 1) * 5_000_000.0
        for i in range(n_per_city):
            rows.append(
                {
                    "Title": f"{(i % 3) + 1} BHK Flat {city} {i}",
                    "location": city,
                    "Transaction": "Resale" if i % 2 == 0 else "New Property",
                    "effective_area_sqft": 900.0 + i * 75.0,
                    "Price_in_rupees": base_price + float(rng.integers(100_000, 2_000_000)) + i * 10_000.0,
                }
            )
    return pd.DataFrame(rows)


def test_create_price_bins_returns_expected_buckets() -> None:
    df = _make_split_sample_df(10)
    bins = create_price_bins(df, n_bins=5)
    assert len(bins) == len(df)
    assert bins.nunique() == 5


def test_train_test_split_stratified_preserves_ratio_and_cities() -> None:
    df = _make_split_sample_df(10)
    train, test = train_test_split_stratified(df, test_size=0.2, random_state=42)
    assert len(train) == 24
    assert len(test) == 6
    assert set(train.index).isdisjoint(set(test.index))
    assert set(test["location"].unique()) == {"new-delhi", "bangalore", "ahmedabad"}


def test_geographical_split_holds_out_cities() -> None:
    df = _make_split_sample_df(8)
    in_dom, holdout = geographical_split(df, holdout_cities=["Ahmedabad"])
    assert "ahmedabad" not in set(in_dom["location"])
    assert set(holdout["location"].unique()) == {"ahmedabad"}
    assert len(in_dom) + len(holdout) == len(df)


def test_validate_no_leakage_passes_and_detects_violations() -> None:
    df = _make_split_sample_df(10)
    train, test = train_test_split_stratified(df, test_size=0.2, random_state=42)
    report = validate_no_leakage(train, test)
    assert report["index_disjoint"] is True
    assert report["cross_split_duplicates"] == 0

    # Inject duplicate row leakage
    leaked_test = pd.concat([test, train.iloc[[0]]], ignore_index=False)
    with pytest.raises(ValueError, match="Index leakage|duplicate leakage"):
        validate_no_leakage(train, leaked_test, check_index_disjoint=False)

    # Inject forbidden column leakage
    bad_train = train.copy()
    bad_train["Price (in rupees)"] = 6000.0
    with pytest.raises(ValueError, match="Price \\(in rupees\\)"):
        validate_no_leakage(bad_train, test)


def test_save_splits_writes_csv_and_metadata(tmp_path: Path) -> None:
    df = _make_split_sample_df(5)
    train, test = train_test_split_stratified(df, test_size=0.2, random_state=42)
    tr_path, te_path = save_splits(train, test, tmp_path, metadata={"ok": True})
    assert tr_path.exists()
    assert te_path.exists()
    assert (tmp_path / "split_metadata.json").exists()
