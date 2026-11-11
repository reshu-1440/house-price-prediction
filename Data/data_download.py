"""Download the Kaggle house price dataset and stage it at ``Data/house_prices.csv``."""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

import kagglehub

DATASET_SLUG = "juhibhojani/house-price"
DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parent / "house_prices.csv"


def _locate_csv(download_dir: Path) -> Path:
    """Find ``house_prices.csv`` (or the largest CSV) inside a kagglehub download folder."""
    preferred = download_dir / "house_prices.csv"
    if preferred.is_file():
        return preferred

    candidates = sorted(
        download_dir.rglob("*.csv"),
        key=lambda p: p.stat().st_size,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(f"No CSV file found inside downloaded dataset directory: {download_dir}")
    return candidates[0]


def download_dataset(
    output_path: str | Path | None = None,
    force: bool = False,
) -> Path:
    """Download ``juhibhojani/house-price`` via kagglehub and place it at ``Data/house_prices.csv``."""
    target = Path(output_path).resolve() if output_path is not None else DEFAULT_OUTPUT_PATH
    if target.exists() and not force:
        size_mb = target.stat().st_size / (1024 * 1024)
        print(f"Dataset already present at {target} ({size_mb:.2f} MB). Use --force to re-download.")
        return target

    target.parent.mkdir(parents=True, exist_ok=True)
    cached_dir = Path(kagglehub.dataset_download(DATASET_SLUG))
    source_csv = _locate_csv(cached_dir)

    tmp_path = target.with_suffix(".csv.tmp")
    shutil.copy2(source_csv, tmp_path)
    os.replace(tmp_path, target)

    size_mb = target.stat().st_size / (1024 * 1024)
    print(f"Dataset ready at {target} ({size_mb:.2f} MB)")
    return target


def main() -> None:
    """CLI entrypoint for downloading the raw Kaggle dataset."""
    parser = argparse.ArgumentParser(description="Download Kaggle house-price CSV into Data/house_prices.csv.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional target path (defaults to Data/house_prices.csv).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download and overwrite the existing CSV if present.",
    )
    args = parser.parse_args()
    download_dataset(output_path=args.output, force=args.force)


if __name__ == "__main__":
    main()
