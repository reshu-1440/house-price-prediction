"""Schema and domain validation checks for raw and cleaned datasets."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from src.data.load_data import REQUIRED_RAW_COLUMNS

REQUIRED_CLEANED_COLUMNS: tuple[str, ...] = (
    "Title",
    "location",
    "Transaction",
    "Status",
    "Furnishing",
    "Ownership",
    "Price_in_rupees",
    "effective_area_sqft",
    "area_type",
    "bathroom_count",
    "balcony_count",
    "parking_count",
    "parking_type",
)

FORBIDDEN_LEAKAGE_COLUMNS: tuple[str, ...] = (
    "Price (in rupees)",
    "Index",
    "Amount(in rupees)",
    "Dimensions",
    "Plot Area",
)


@dataclass
class ValidationCheck:
    """Outcome of a single schema or domain expectation check."""

    name: str
    passed: bool
    details: str


@dataclass
class ValidationReport:
    """Aggregated validation results across all schema/domain expectations."""

    stage: str
    row_count: int
    column_count: int
    checks: list[ValidationCheck] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Return True only when every validation check passed."""
        return all(check.passed for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        """Serialize report to a JSON-friendly dictionary."""
        return {
            "stage": self.stage,
            "success": self.success,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "failed_checks": [c.name for c in self.checks if not c.passed],
            "checks": [
                {"name": c.name, "passed": c.passed, "details": c.details}
                for c in self.checks
            ],
        }


class SchemaValidationError(ValueError):
    """Raised when dataset schema or domain expectations fail."""


def validate_raw_schema(df: pd.DataFrame) -> ValidationReport:
    """Validate raw CSV structure prior to cleaning."""
    checks: list[ValidationCheck] = []
    checks.append(
        ValidationCheck(
            name="non_empty_dataframe",
            passed=len(df) > 0,
            details=f"Row count = {len(df)}",
        )
    )
    missing_cols = [c for c in REQUIRED_RAW_COLUMNS if c not in df.columns]
    checks.append(
        ValidationCheck(
            name="required_raw_columns_present",
            passed=len(missing_cols) == 0,
            details="All 21 raw columns present"
            if not missing_cols
            else f"Missing: {missing_cols}",
        )
    )
    return ValidationReport(
        stage="raw",
        row_count=int(df.shape[0]),
        column_count=int(df.shape[1]),
        checks=checks,
    )


def validate_cleaned_data(df: pd.DataFrame) -> ValidationReport:
    """Validate cleaned dataset schema, null absence, value ranges, and leakage removal."""
    checks: list[ValidationCheck] = []

    checks.append(
        ValidationCheck(
            name="non_empty_dataframe",
            passed=len(df) > 0,
            details=f"Row count = {len(df)}",
        )
    )

    missing_cols = [c for c in REQUIRED_CLEANED_COLUMNS if c not in df.columns]
    checks.append(
        ValidationCheck(
            name="required_cleaned_columns_present",
            passed=len(missing_cols) == 0,
            details="All required cleaned columns present"
            if not missing_cols
            else f"Missing: {missing_cols}",
        )
    )

    leaked_cols = [c for c in FORBIDDEN_LEAKAGE_COLUMNS if c in df.columns]
    checks.append(
        ValidationCheck(
            name="no_leakage_or_dropped_columns",
            passed=len(leaked_cols) == 0,
            details="Zero leakage/raw-dropped columns present"
            if not leaked_cols
            else f"Unexpected columns: {leaked_cols}",
        )
    )

    critical_no_nulls = (
        "Price_in_rupees",
        "effective_area_sqft",
        "location",
        "Transaction",
        "bathroom_count",
        "balcony_count",
        "parking_count",
    )
    null_violations = {
        c: int(df[c].isna().sum())
        for c in critical_no_nulls
        if c in df.columns and df[c].isna().any()
    }
    checks.append(
        ValidationCheck(
            name="zero_nulls_in_critical_columns",
            passed=len(null_violations) == 0,
            details="No nulls in critical columns"
            if not null_violations
            else f"Null counts: {null_violations}",
        )
    )

    if "Price_in_rupees" in df.columns and not df.empty:
        min_price = float(df["Price_in_rupees"].min())
        checks.append(
            ValidationCheck(
                name="positive_price_range",
                passed=min_price > 0,
                details=f"Min Price_in_rupees = {min_price:,.2f}",
            )
        )

    if "effective_area_sqft" in df.columns and not df.empty:
        min_area = float(df["effective_area_sqft"].min())
        checks.append(
            ValidationCheck(
                name="positive_area_range",
                passed=min_area > 0,
                details=f"Min effective_area_sqft = {min_area:,.2f}",
            )
        )

    if "bathroom_count" in df.columns and not df.empty:
        min_bath = float(df["bathroom_count"].min())
        checks.append(
            ValidationCheck(
                name="valid_bathroom_count",
                passed=min_bath >= 1.0,
                details=f"Min bathroom_count = {min_bath}",
            )
        )

    if "Transaction" in df.columns and not df.empty:
        observed_tx = set(df["Transaction"].dropna().unique())
        allowed_tx = {"Resale", "New Property"}
        checks.append(
            ValidationCheck(
                name="valid_transaction_categories",
                passed=observed_tx.issubset(allowed_tx),
                details=f"Observed transactions = {sorted(observed_tx)}",
            )
        )

    if "area_type" in df.columns and not df.empty:
        observed_area_types = set(df["area_type"].dropna().unique())
        allowed_area_types = {"carpet", "super"}
        checks.append(
            ValidationCheck(
                name="valid_area_type_categories",
                passed=observed_area_types.issubset(allowed_area_types),
                details=f"Observed area types = {sorted(observed_area_types)}",
            )
        )

    dup_count = int(df.duplicated().sum()) if not df.empty else 0
    checks.append(
        ValidationCheck(
            name="zero_duplicate_rows",
            passed=dup_count == 0,
            details=f"Duplicate rows = {dup_count}",
        )
    )

    return ValidationReport(
        stage="cleaned",
        row_count=int(df.shape[0]),
        column_count=int(df.shape[1]),
        checks=checks,
    )


def assert_valid(report: ValidationReport) -> ValidationReport:
    """Raise ``SchemaValidationError`` if ``report`` contains failed checks."""
    if not report.success:
        failed = [f"{c.name} ({c.details})" for c in report.checks if not c.passed]
        raise SchemaValidationError(
            f"Validation failed at stage '{report.stage}': {'; '.join(failed)}"
        )
    return report
