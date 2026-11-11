"""Unit tests for configuration and raw dataset loading utilities."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.data.load_data import REQUIRED_RAW_COLUMNS, get_dataset_overview, load_raw_data
from src.utils.config import get_project_root, load_config, resolve_path


def _make_sample_raw_df(rows: int = 3) -> pd.DataFrame:
    """Create a minimal valid raw-schema DataFrame for fast unit testing."""
    data = {col: [None] * rows for col in REQUIRED_RAW_COLUMNS}
    data["Index"] = list(range(rows))
    data["Title"] = ["2 BHK Flat"] * rows
    data["Amount(in rupees)"] = ["50 Lac", "1.20 Cr", "50 Lac"][:rows]
    data["location"] = ["new-delhi", "bangalore", "new-delhi"][:rows]
    return pd.DataFrame(data)


def test_load_default_config() -> None:
    cfg = load_config()
    assert cfg["project"]["name"] == "house-price-prediction"
    assert cfg["data"]["raw_path"] == "Data/house_prices.csv"
    assert cfg["data"]["target_column"] == "Price_in_rupees"


def test_resolve_path_relative_to_root() -> None:
    resolved = resolve_path("Data/house_prices.csv")
    assert resolved == (get_project_root() / "Data/house_prices.csv").resolve()


def test_load_config_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "does_not_exist.yaml")


def test_load_raw_data_and_city_filter(tmp_path: Path) -> None:
    csv_path = tmp_path / "sample.csv"
    sample_df = _make_sample_raw_df(rows=3)
    sample_df.to_csv(csv_path, index=False)

    loaded_all = load_raw_data(data_path=csv_path)
    assert loaded_all.shape == (3, len(REQUIRED_RAW_COLUMNS))

    loaded_filtered = load_raw_data(data_path=csv_path, cities=["Bangalore"])
    assert len(loaded_filtered) == 1
    assert loaded_filtered["location"].iloc[0] == "bangalore"


def test_load_raw_data_missing_columns_raises(tmp_path: Path) -> None:
    csv_path = tmp_path / "bad.csv"
    pd.DataFrame({"Index": [0], "Title": ["1 BHK"]}).to_csv(csv_path, index=False)

    with pytest.raises(ValueError, match="missing required columns"):
        load_raw_data(data_path=csv_path)


def test_get_dataset_overview_detects_index_masked_duplicates() -> None:
    df = pd.DataFrame(
        {
            "Index": [0, 1, 2],
            "location": ["pune", "pune", "mumbai"],
            "Title": ["2 BHK", "2 BHK", "3 BHK"],
        }
    )
    overview = get_dataset_overview(df)
    assert overview["rows"] == 3
    assert overview["unique_locations"] == 2
    assert overview["exact_duplicates_all_cols"] == 0
    assert overview["duplicates_excluding_index"] == 1


def test_load_raw_data_missing_file_hints_download_script(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Data/data_download.py"):
        load_raw_data(data_path=tmp_path / "missing.csv")


def test_data_download_stages_csv_and_respects_force(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib.util

    script_path = get_project_root() / "Data" / "data_download.py"
    spec = importlib.util.spec_from_file_location("data_download", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    cache_dir = tmp_path / "kaggle_cache"
    cache_dir.mkdir()
    (cache_dir / "house_prices.csv").write_text("Index,Title\n0,2 BHK\n", encoding="utf-8")

    calls: list[str] = []

    def _fake_download(slug: str) -> str:
        calls.append(slug)
        return str(cache_dir)

    monkeypatch.setattr(module.kagglehub, "dataset_download", _fake_download)

    out_path = tmp_path / "Data" / "house_prices.csv"
    staged = module.download_dataset(output_path=out_path)
    assert staged == out_path.resolve()
    assert out_path.read_text(encoding="utf-8") == "Index,Title\n0,2 BHK\n"
    assert len(calls) == 1

    # Calling again without force skips download
    module.download_dataset(output_path=out_path)
    assert len(calls) == 1

    # Calling with force refreshes file
    (cache_dir / "house_prices.csv").write_text("Index,Title\n0,3 BHK\n", encoding="utf-8")
    module.download_dataset(output_path=out_path, force=True)
    assert len(calls) == 2
    assert out_path.read_text(encoding="utf-8") == "Index,Title\n0,3 BHK\n"
