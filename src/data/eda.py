"""Exploratory Data Analysis (EDA) and data quality profiling utilities."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from src.utils.config import get_logger

logger = get_logger(__name__)

_PRICE_UNIT_MULTIPLIERS: dict[str, float] = {
    "cr": 1e7,
    "crore": 1e7,
    "lac": 1e5,
    "lakh": 1e5,
}

_AREA_TO_SQFT: dict[str, float] = {
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


def _extract_numeric_price(series: pd.Series) -> pd.Series:
    """Parse ``Amount(in rupees)`` strings into numeric INR, returning NaN for Call for Price."""
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
    multipliers = units.map(_PRICE_UNIT_MULTIPLIERS).fillna(1.0)
    parsed = (nums * multipliers).astype("float64")
    parsed.loc[is_call] = np.nan
    return parsed


def _extract_area_sqft(series: pd.Series) -> pd.Series:
    """Parse area strings (with commas and regional units) into square feet."""
    text = series.astype("string").str.strip().str.replace(",", "", regex=False)
    nums = pd.to_numeric(text.str.extract(r"([-+]?\d*\.?\d+)")[0], errors="coerce")
    units = text.str.extract(r"[0-9.]+\s*([A-Za-z0-9]+)$")[0].str.lower().fillna("sqft")
    factors = units.map(_AREA_TO_SQFT).fillna(np.nan)
    return (nums * factors).astype("float64")


def _extract_count_with_gt10(series: pd.Series) -> pd.Series:
    """Parse count strings where ``> 10`` maps to 11.0 for numeric profiling."""
    text = series.astype("string").str.strip()
    mapped = text.replace({"> 10": "11", ">10": "11"})
    return pd.to_numeric(mapped, errors="coerce").astype("float64")


def _prepare_eda_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Build an enriched copy of ``df`` with temporary parsed columns for plotting."""
    eda_df = df.copy()
    if "Amount(in rupees)" in eda_df.columns:
        eda_df["_price_in_rupees"] = _extract_numeric_price(eda_df["Amount(in rupees)"])
    if "Carpet Area" in eda_df.columns:
        eda_df["_carpet_area_sqft"] = _extract_area_sqft(eda_df["Carpet Area"])
    if "Super Area" in eda_df.columns:
        eda_df["_super_area_sqft"] = _extract_area_sqft(eda_df["Super Area"])
    if "Bathroom" in eda_df.columns:
        eda_df["_bathroom_num"] = _extract_count_with_gt10(eda_df["Bathroom"])
    if "Balcony" in eda_df.columns:
        eda_df["_balcony_num"] = _extract_count_with_gt10(eda_df["Balcony"])
    if "Title" in eda_df.columns:
        eda_df["_bhk_num"] = pd.to_numeric(
            eda_df["Title"].astype("string").str.extract(r"(\d+)\s*BHK", flags=re.IGNORECASE)[0],
            errors="coerce",
        ).astype("float64")
    return eda_df


def generate_summary_statistics(df: pd.DataFrame) -> dict[str, Any]:
    """Compute structural summary statistics, dtypes, null counts, and parsed target summary."""
    eda_df = _prepare_eda_frame(df)
    null_counts = df.isnull().sum()
    null_pct = (null_counts / max(len(df), 1) * 100).round(2)

    numeric_cols = [
        c
        for c in (
            "_price_in_rupees",
            "Price (in rupees)",
            "_carpet_area_sqft",
            "_super_area_sqft",
            "_bathroom_num",
            "_balcony_num",
            "_bhk_num",
        )
        if c in eda_df.columns
    ]
    numeric_summary: dict[str, dict[str, float | None]] = {}
    for col in numeric_cols:
        valid = eda_df[col].dropna()
        if valid.empty:
            numeric_summary[col] = {
                "count": 0.0,
                "mean": None,
                "median": None,
                "std": None,
                "min": None,
                "p25": None,
                "p75": None,
                "p99": None,
                "max": None,
            }
        else:
            numeric_summary[col] = {
                "count": float(len(valid)),
                "mean": round(float(valid.mean()), 2),
                "median": round(float(valid.median()), 2),
                "std": round(float(valid.std(ddof=1)) if len(valid) > 1 else 0.0, 2),
                "min": round(float(valid.min()), 2),
                "p25": round(float(valid.quantile(0.25)), 2),
                "p75": round(float(valid.quantile(0.75)), 2),
                "p99": round(float(valid.quantile(0.99)), 2),
                "max": round(float(valid.max()), 2),
            }

    return {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "dtypes": {str(k): str(v) for k, v in df.dtypes.items()},
        "null_counts": {str(k): int(v) for k, v in null_counts.items()},
        "null_percentages": {str(k): float(v) for k, v in null_pct.items()},
        "numeric_summary": numeric_summary,
    }


def generate_data_quality_report(
    df: pd.DataFrame, output_path: Path | None = None
) -> dict[str, Any]:
    """Profile data quality issues (duplicates, Call for Price, 100%-nulls, area coverage)."""
    cols_except_index = [c for c in df.columns if c != "Index"]
    all_null_cols = [str(c) for c in df.columns if df[c].isnull().all()]

    call_for_price_count = (
        int(df["Amount(in rupees)"].astype(str).str.contains("Call for Price", case=False, na=False).sum())
        if "Amount(in rupees)" in df.columns
        else 0
    )

    carpet_present = df["Carpet Area"].notnull() if "Carpet Area" in df.columns else pd.Series(False, index=df.index)
    super_present = df["Super Area"].notnull() if "Super Area" in df.columns else pd.Series(False, index=df.index)

    gt10_bathroom = (
        int(df["Bathroom"].astype(str).str.contains(">", na=False).sum())
        if "Bathroom" in df.columns
        else 0
    )
    gt10_balcony = (
        int(df["Balcony"].astype(str).str.contains(">", na=False).sum())
        if "Balcony" in df.columns
        else 0
    )

    report: dict[str, Any] = {
        "total_rows": int(len(df)),
        "total_columns": int(df.shape[1]),
        "exact_duplicates_all_columns": int(df.duplicated().sum()),
        "duplicates_excluding_index": int(df.duplicated(subset=cols_except_index).sum()),
        "unique_rows_excluding_index": int(len(df) - df.duplicated(subset=cols_except_index).sum()),
        "call_for_price_count": call_for_price_count,
        "all_null_columns": all_null_cols,
        "area_coverage": {
            "carpet_only": int((carpet_present & ~super_present).sum()),
            "super_only": int((~carpet_present & super_present).sum()),
            "both_present": int((carpet_present & super_present).sum()),
            "neither_present": int((~carpet_present & ~super_present).sum()),
        },
        "gt10_string_counts": {
            "bathroom": gt10_bathroom,
            "balcony": gt10_balcony,
        },
        "transaction_counts": (
            {str(k): int(v) for k, v in df["Transaction"].value_counts(dropna=False).items()}
            if "Transaction" in df.columns
            else {}
        ),
        "unique_locations": int(df["location"].nunique()) if "location" in df.columns else 0,
        "top_10_locations": (
            {str(k): int(v) for k, v in df["location"].value_counts().head(10).items()}
            if "location" in df.columns
            else {}
        ),
    }

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        logger.info("Saved data quality report to %s", output_path)

    return report


def plot_target_distribution(df: pd.DataFrame, output_path: Path) -> Path:
    """Plot log10 price histogram and boxplot for valid parsed ``Price_in_rupees``."""
    eda_df = _prepare_eda_frame(df)
    valid_prices = eda_df["_price_in_rupees"].dropna()
    valid_prices = valid_prices[valid_prices > 0]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))

    if not valid_prices.empty:
        log_prices = np.log10(valid_prices)
        sns.histplot(log_prices, bins=40, kde=True, ax=axes[0], color="#2b6cb0")
        axes[0].set_title("Log10 Price Distribution (INR)")
        axes[0].set_xlabel("log10(Price in Rupees)")
        axes[0].set_ylabel("Listing Count")

        clipped = valid_prices.clip(upper=valid_prices.quantile(0.99)) / 1e5
        sns.boxplot(x=clipped, ax=axes[1], color="#38a169")
        axes[1].set_title("Price Boxplot (INR Lakhs, Capped at P99)")
        axes[1].set_xlabel("Price (INR Lakhs)")
    else:
        axes[0].text(0.5, 0.5, "No valid prices", ha="center", va="center")
        axes[1].text(0.5, 0.5, "No valid prices", ha="center", va="center")

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_categorical_distributions(df: pd.DataFrame, output_path: Path) -> Path:
    """Plot bar charts for Transaction, Furnishing, Ownership, and Top 15 Locations."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(14, 9))

    cat_specs = [
        ("Transaction", "Transaction Types", axes[0, 0]),
        ("Furnishing", "Furnishing Status", axes[0, 1]),
        ("Ownership", "Ownership Types", axes[1, 0]),
    ]
    for col, title, ax in cat_specs:
        if col in df.columns:
            counts = df[col].fillna("Missing").value_counts().head(10)
            sns.barplot(x=counts.values, y=counts.index.astype(str), ax=ax, color="#3182ce")
        ax.set_title(title)
        ax.set_xlabel("Count")

    ax_loc = axes[1, 1]
    if "location" in df.columns:
        top_loc = df["location"].fillna("Missing").value_counts().head(15)
        sns.barplot(x=top_loc.values, y=top_loc.index.astype(str), ax=ax_loc, color="#2f855a")
    ax_loc.set_title("Top 15 Locations by Listing Count")
    ax_loc.set_xlabel("Count")

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_numerical_distributions(df: pd.DataFrame, output_path: Path) -> Path:
    """Plot histograms for Bathroom, Balcony, Carpet Area (sqft), and Super Area (sqft)."""
    eda_df = _prepare_eda_frame(df)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))

    specs = [
        ("_bathroom_num", "Bathroom Count (clipped P99)", axes[0, 0]),
        ("_balcony_num", "Balcony Count (clipped P99)", axes[0, 1]),
        ("_carpet_area_sqft", "Carpet Area sqft (clipped P99)", axes[1, 0]),
        ("_super_area_sqft", "Super Area sqft (clipped P99)", axes[1, 1]),
    ]
    for col, title, ax in specs:
        if col in eda_df.columns:
            series = pd.to_numeric(eda_df[col], errors="coerce").astype("float64").dropna()
            series = series[series > 0]
            if not series.empty:
                clipped = series.clip(upper=float(series.quantile(0.99)))
                sns.histplot(clipped, bins=30, ax=ax, color="#805ad5")
        ax.set_title(title)
        ax.set_ylabel("Count")

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_correlation_matrix(df: pd.DataFrame, output_path: Path) -> Path:
    """Plot correlation heatmap across parsed numeric attributes."""
    eda_df = _prepare_eda_frame(df)
    candidate_cols = [
        c
        for c in (
            "_price_in_rupees",
            "Price (in rupees)",
            "_carpet_area_sqft",
            "_super_area_sqft",
            "_bathroom_num",
            "_balcony_num",
            "_bhk_num",
        )
        if c in eda_df.columns
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 7))
    if len(candidate_cols) >= 2:
        corr = eda_df[candidate_cols].corr()
        sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0, ax=ax)
        ax.set_title("Numeric Feature Correlation Matrix (Note: Price (in rupees) is Leakage)")
    else:
        ax.text(0.5, 0.5, "Insufficient numeric columns", ha="center", va="center")

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_price_by_location(df: pd.DataFrame, output_path: Path, top_n: int = 15) -> Path:
    """Plot log10 price distribution across the top ``top_n`` cities by volume."""
    eda_df = _prepare_eda_frame(df)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(13, 6))

    if "location" in eda_df.columns and "_price_in_rupees" in eda_df.columns:
        valid = eda_df.loc[eda_df["_price_in_rupees"].notna() & (eda_df["_price_in_rupees"] > 0)].copy()
        top_cities = valid["location"].value_counts().head(top_n).index.tolist()
        subset = valid.loc[valid["location"].isin(top_cities)].copy()
        if not subset.empty:
            subset["log10_price"] = np.log10(subset["_price_in_rupees"])
            order = (
                subset.groupby("location")["log10_price"]
                .median()
                .sort_values(ascending=False)
                .index.tolist()
            )
            sns.boxplot(data=subset, x="location", y="log10_price", order=order, ax=ax)
            ax.tick_params(axis="x", rotation=45)
            ax.set_title(f"Log10 Property Price Across Top {len(order)} Cities")
            ax.set_ylabel("log10(Price in Rupees)")
            ax.set_xlabel("City")

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_missing_values(df: pd.DataFrame, output_path: Path) -> Path:
    """Plot missing value percentage for every column in ``df``."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    missing_pct = (df.isnull().sum() / max(len(df), 1) * 100).sort_values(ascending=True)

    fig, ax = plt.subplots(figsize=(10, 7))
    colors = ["#e53e3e" if val == 100.0 else "#dd6b20" if val > 30.0 else "#3182ce" for val in missing_pct.values]
    ax.barh(missing_pct.index.astype(str), missing_pct.values, color=colors)
    ax.set_xlim(0, 105)
    ax.set_xlabel("Missing Percentage (%)")
    ax.set_title("Missing Value Profile Across Raw Dataset Columns")

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def write_eda_markdown_report(
    summary: dict[str, Any],
    quality: dict[str, Any],
    figure_paths: list[Path],
    output_path: Path,
) -> Path:
    """Write a concise markdown EDA report strictly from computed statistics."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    price_stats = summary.get("numeric_summary", {}).get("_price_in_rupees", {})
    area_cov = quality.get("area_coverage", {})
    gt10 = quality.get("gt10_string_counts", {})

    lines = [
        "# Exploratory Data Analysis Summary",
        "",
        "## 1. Dataset Dimensions & Duplicate Profile",
        f"- **Rows**: {quality['total_rows']:,}",
        f"- **Columns**: {quality['total_columns']}",
        f"- **Unique Locations**: {quality['unique_locations']}",
        f"- **Exact Duplicates (All Columns)**: {quality['exact_duplicates_all_columns']:,}",
        f"- **Duplicates Excluding `Index`**: {quality['duplicates_excluding_index']:,}",
        f"- **Unique Rows Excluding `Index`**: {quality['unique_rows_excluding_index']:,}",
        "",
        "## 2. Target (`Price_in_rupees` Parsed from `Amount(in rupees)`) Profile",
        f"- **Valid Numeric Price Count**: {int(price_stats.get('count') or 0):,}",
        f"- **`Call for Price` Excluded Count**: {quality['call_for_price_count']:,}",
        f"- **Median Price (INR)**: {price_stats.get('median')}",
        f"- **Mean Price (INR)**: {price_stats.get('mean')}",
        f"- **P25 / P75 / P99 (INR)**: {price_stats.get('p25')} / {price_stats.get('p75')} / {price_stats.get('p99')}",
        f"- **Min / Max (INR)**: {price_stats.get('min')} / {price_stats.get('max')}",
        "",
        "## 3. Data Quality Findings",
        f"- **100% Null Columns**: {quality['all_null_columns']}",
        f"- **Area Coverage**: Carpet only={area_cov.get('carpet_only', 0):,}, "
        f"Super only={area_cov.get('super_only', 0):,}, "
        f"Both={area_cov.get('both_present', 0):,}, "
        f"Neither={area_cov.get('neither_present', 0):,}",
        f"- **`> 10` String Counts**: Bathroom={gt10.get('bathroom', 0):,}, Balcony={gt10.get('balcony', 0):,}",
        f"- **Transaction Counts**: `{quality.get('transaction_counts', {})}`",
        "",
        "## 4. Top 10 Cities by Listing Volume",
    ]
    for city, cnt in quality.get("top_10_locations", {}).items():
        lines.append(f"- `{city}`: {cnt:,}")

    lines.extend(["", "## 5. Generated Figures"])
    for fig_path in figure_paths:
        lines.append(f"- `{fig_path.name}`")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Saved EDA markdown report to %s", output_path)
    return output_path


def run_eda(
    df: pd.DataFrame,
    reports_dir: Path,
    figures_dir: Path,
) -> dict[str, Any]:
    """Execute the full EDA suite, saving JSON, Markdown, and PNG artifacts."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    summary = generate_summary_statistics(df)
    quality = generate_data_quality_report(
        df, output_path=reports_dir / "data_quality_report.json"
    )

    figure_paths = [
        plot_missing_values(df, figures_dir / "missing_values.png"),
        plot_target_distribution(df, figures_dir / "target_distribution.png"),
        plot_categorical_distributions(df, figures_dir / "categorical_distributions.png"),
        plot_numerical_distributions(df, figures_dir / "numerical_distributions.png"),
        plot_correlation_matrix(df, figures_dir / "correlation_matrix.png"),
        plot_price_by_location(df, figures_dir / "price_by_location.png"),
    ]

    md_path = write_eda_markdown_report(
        summary=summary,
        quality=quality,
        figure_paths=figure_paths,
        output_path=reports_dir / "eda_summary.md",
    )

    return {
        "summary": summary,
        "quality": quality,
        "figures": [str(p) for p in figure_paths],
        "markdown_report": str(md_path),
    }
