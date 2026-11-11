"""Scikit-learn compatible feature engineering transformers (training-serving safe)."""

from __future__ import annotations

import re
from typing import Any, Iterable

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.model_selection import KFold
from sklearn.preprocessing import OneHotEncoder

DEFAULT_CATEGORICAL_COLUMNS: tuple[str, ...] = (
    "Transaction",
    "Status",
    "Furnishing",
    "Ownership",
    "facing",
    "area_type",
    "parking_type",
)


def _normalize_facing(series: pd.Series) -> pd.Series:
    """Normalize irregular spacing around hyphens in compass directions (e.g., 'South -West')."""
    cleaned = series.astype("string").fillna("Missing").str.strip()
    cleaned = cleaned.str.replace(r"\s*-\s*", "-", regex=True)
    cleaned = cleaned.replace({"": "Missing", "nan": "Missing", "None": "Missing"})
    return cleaned.astype(str)


class BHKExtractor(BaseEstimator, TransformerMixin):
    """Extract numeric ``bhk`` plus ``is_studio`` and ``is_penthouse`` flags from listing Title."""

    def __init__(self, title_col: str = "Title", default_bhk: float = 2.0) -> None:
        self.title_col = title_col
        self.default_bhk = default_bhk

    def _parse_raw_bhk(self, titles: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
        text = titles.astype("string").fillna("")
        bhk = pd.to_numeric(
            text.str.extract(r"(\d+)\s*BHK", flags=re.IGNORECASE)[0],
            errors="coerce",
        ).astype("float64")
        is_studio = text.str.contains(r"\bstudio\b", case=False, na=False).astype("float64")
        is_penthouse = text.str.contains(r"\bpenthouse\b", case=False, na=False).astype("float64")
        # Treat Studio apartments without explicit BHK prefix as 1 BHK
        bhk = bhk.where(bhk.notna(), np.where(is_studio == 1.0, 1.0, np.nan))
        return bhk, is_studio, is_penthouse

    def fit(self, X: pd.DataFrame, y: Any = None) -> BHKExtractor:
        if self.title_col in X.columns:
            bhk, _, _ = self._parse_raw_bhk(X[self.title_col])
            self.median_bhk_ = float(bhk.median()) if bhk.notna().any() else float(self.default_bhk)
        else:
            self.median_bhk_ = float(self.default_bhk)
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        out = X.copy()
        if self.title_col in out.columns:
            bhk, is_studio, is_penthouse = self._parse_raw_bhk(out[self.title_col])
            out["bhk"] = bhk.fillna(self.median_bhk_).clip(lower=1.0)
            out["is_studio"] = is_studio
            out["is_penthouse"] = is_penthouse
        else:
            out["bhk"] = float(self.median_bhk_)
            out["is_studio"] = 0.0
            out["is_penthouse"] = 0.0
        return out


class FloorExtractor(BaseEstimator, TransformerMixin):
    """Extract ``floor_number``, ``total_floors``, ``floor_ratio``, and floor indicators."""

    def __init__(
        self,
        floor_col: str = "Floor",
        default_floor: float = 2.0,
        default_total_floors: float = 4.0,
    ) -> None:
        self.floor_col = floor_col
        self.default_floor = default_floor
        self.default_total_floors = default_total_floors

    @staticmethod
    def _parse_floor_token(token: str) -> float:
        t = token.strip().lower()
        if not t or t in {"nan", "none"}:
            return float("nan")
        if "ground" in t:
            return 0.0
        if "lower basement" in t:
            return -2.0
        if "upper basement" in t or "basement" in t:
            return -1.0
        match = re.search(r"-?\d+", t)
        return float(match.group(0)) if match else float("nan")

    def _parse_floor_series(self, series: pd.Series) -> tuple[pd.Series, pd.Series]:
        floor_vals = []
        total_vals = []
        for raw in series.astype("string").fillna(""):
            text = str(raw).strip()
            if not text or text.lower() in {"<na>", "nan", "none"}:
                floor_vals.append(np.nan)
                total_vals.append(np.nan)
                continue
            parts = re.split(r"\s+out\s+of\s+", text, maxsplit=1, flags=re.IGNORECASE)
            f_val = self._parse_floor_token(parts[0])
            t_val = np.nan
            if len(parts) == 2:
                m = re.search(r"\d+", parts[1])
                if m:
                    t_val = float(m.group(0))
            floor_vals.append(f_val)
            total_vals.append(t_val)
        return pd.Series(floor_vals, index=series.index, dtype="float64"), pd.Series(
            total_vals, index=series.index, dtype="float64"
        )

    def fit(self, X: pd.DataFrame, y: Any = None) -> FloorExtractor:
        if self.floor_col in X.columns:
            f_num, t_num = self._parse_floor_series(X[self.floor_col])
            self.median_floor_ = (
                float(f_num.median()) if f_num.notna().any() else float(self.default_floor)
            )
            self.median_total_floors_ = (
                float(t_num.median()) if t_num.notna().any() else float(self.default_total_floors)
            )
        else:
            self.median_floor_ = float(self.default_floor)
            self.median_total_floors_ = float(self.default_total_floors)
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        out = X.copy()
        if self.floor_col in out.columns:
            f_num, t_num = self._parse_floor_series(out[self.floor_col])
        else:
            f_num = pd.Series(np.nan, index=out.index, dtype="float64")
            t_num = pd.Series(np.nan, index=out.index, dtype="float64")

        floor_filled = f_num.fillna(self.median_floor_)
        # Ensure total_floors >= max(floor_filled, 1) when total_floors is missing
        total_filled = t_num.fillna(self.median_total_floors_)
        total_filled = np.maximum(total_filled, np.maximum(floor_filled, 1.0))

        out["floor_number"] = floor_filled
        out["total_floors"] = total_filled
        out["floor_ratio"] = np.clip(floor_filled / total_filled, -1.0, 1.0)
        out["is_ground_floor"] = (floor_filled == 0.0).astype("float64")
        out["is_top_floor"] = ((floor_filled > 0) & (floor_filled == total_filled)).astype("float64")
        return out


class AreaFeatureBuilder(BaseEstimator, TransformerMixin):
    """Build domain ratios, log transformations, and structural flags without fitting state."""

    def fit(self, X: pd.DataFrame, y: Any = None) -> AreaFeatureBuilder:
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        out = X.copy()
        area = pd.to_numeric(out["effective_area_sqft"], errors="coerce").astype("float64").clip(lower=1.0)
        bhk = pd.to_numeric(out.get("bhk", pd.Series(2.0, index=out.index)), errors="coerce").fillna(2.0).clip(lower=1.0)
        bath = pd.to_numeric(out.get("bathroom_count", pd.Series(2.0, index=out.index)), errors="coerce").fillna(2.0).clip(lower=1.0)
        balcony = pd.to_numeric(out.get("balcony_count", pd.Series(0.0, index=out.index)), errors="coerce").fillna(0.0).clip(lower=0.0)

        out["log_effective_area"] = np.log1p(area)
        out["area_per_bhk"] = area / bhk
        out["bathroom_per_bhk"] = bath / bhk
        out["total_rooms_proxy"] = bhk + bath + balcony
        out["bhk_x_log_area"] = bhk * out["log_effective_area"]

        if "area_type" in out.columns:
            out["is_carpet_area"] = (out["area_type"].astype(str).str.lower() == "carpet").astype("float64")
        else:
            out["is_carpet_area"] = 0.0

        if "Society" in out.columns:
            out["has_society"] = (~out["Society"].astype(str).isin(["Missing", "nan", ""])).astype("float64")
        else:
            out["has_society"] = 0.0

        if "overlooking" in out.columns:
            out["has_overlooking"] = (~out["overlooking"].astype(str).isin(["Missing", "nan", ""])).astype("float64")
        else:
            out["has_overlooking"] = 0.0

        if "facing" in out.columns:
            out["facing"] = _normalize_facing(out["facing"])

        return out


class LocationEncoder(BaseEstimator, TransformerMixin):
    """Leakage-safe frequency and smoothed target encoding for ``location``."""

    def __init__(
        self,
        location_col: str = "location",
        smoothing: float = 20.0,
        n_splits: int = 5,
        random_state: int = 42,
        use_oof_in_fit_transform: bool = True,
    ) -> None:
        self.location_col = location_col
        self.smoothing = smoothing
        self.n_splits = n_splits
        self.random_state = random_state
        self.use_oof_in_fit_transform = use_oof_in_fit_transform

    def _compute_mapping(
        self, loc_series: pd.Series, target_series: pd.Series
    ) -> tuple[float, float, dict[str, float], dict[str, float], dict[str, float]]:
        y_vals = pd.to_numeric(target_series, errors="coerce").astype("float64")
        log_y = np.log1p(y_vals.clip(lower=0.0))

        global_mean = float(y_vals.mean())
        global_log_mean = float(log_y.mean())

        stats = pd.DataFrame({"loc": loc_series, "y": y_vals, "log_y": log_y}).groupby("loc").agg(
            count=("y", "count"),
            mean_y=("y", "mean"),
            mean_log_y=("log_y", "mean"),
        )
        total_rows = max(len(loc_series), 1)
        smooth = float(self.smoothing)

        target_map = (
            (stats["count"] * stats["mean_y"] + smooth * global_mean) / (stats["count"] + smooth)
        ).to_dict()
        log_target_map = (
            (stats["count"] * stats["mean_log_y"] + smooth * global_log_mean)
            / (stats["count"] + smooth)
        ).to_dict()
        freq_map = (stats["count"] / total_rows).to_dict()
        return global_mean, global_log_mean, target_map, log_target_map, freq_map

    def fit(self, X: pd.DataFrame, y: pd.Series | np.ndarray | None = None) -> LocationEncoder:
        if y is None:
            raise ValueError("LocationEncoder.fit requires target y for smoothed target encoding.")

        loc_clean = X[self.location_col].astype(str).str.strip().str.lower()
        y_series = pd.Series(y, index=X.index, dtype="float64")
        (
            self.global_mean_,
            self.global_log_mean_,
            self.target_map_,
            self.log_target_map_,
            self.freq_map_,
        ) = self._compute_mapping(loc_clean, y_series)
        return self

    def fit_transform(self, X: pd.DataFrame, y: pd.Series | np.ndarray | None = None) -> pd.DataFrame:
        self.fit(X, y)
        if not self.use_oof_in_fit_transform or len(X) < self.n_splits or y is None:
            return self.transform(X)

        out = X.copy()
        loc_clean = out[self.location_col].astype(str).str.strip().str.lower()
        y_series = pd.Series(y, index=out.index, dtype="float64")

        oof_target = pd.Series(np.nan, index=out.index, dtype="float64")
        oof_log_target = pd.Series(np.nan, index=out.index, dtype="float64")
        kf = KFold(n_splits=self.n_splits, shuffle=True, random_state=self.random_state)

        for tr_idx, val_idx in kf.split(out):
            g_mean, g_log_mean, t_map, lt_map, _ = self._compute_mapping(
                loc_clean.iloc[tr_idx], y_series.iloc[tr_idx]
            )
            val_locs = loc_clean.iloc[val_idx]
            oof_target.iloc[val_idx] = val_locs.map(t_map).fillna(g_mean)
            oof_log_target.iloc[val_idx] = val_locs.map(lt_map).fillna(g_log_mean)

        out["location_target_enc"] = oof_target
        out["location_log_target_enc"] = oof_log_target
        out["location_freq"] = loc_clean.map(self.freq_map_).fillna(0.0)
        return out

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        out = X.copy()
        loc_clean = out[self.location_col].astype(str).str.strip().str.lower()
        out["location_target_enc"] = loc_clean.map(self.target_map_).fillna(self.global_mean_)
        out["location_log_target_enc"] = loc_clean.map(self.log_target_map_).fillna(
            self.global_log_mean_
        )
        out["location_freq"] = loc_clean.map(self.freq_map_).fillna(0.0)
        return out


class CategoricalEncoder(BaseEstimator, TransformerMixin):
    """One-hot encode low-cardinality categorical attributes with safe unseen handling."""

    def __init__(self, columns: Iterable[str] = DEFAULT_CATEGORICAL_COLUMNS) -> None:
        self.columns = tuple(columns)

    def fit(self, X: pd.DataFrame, y: Any = None) -> CategoricalEncoder:
        self.active_columns_ = [c for c in self.columns if c in X.columns]
        self.encoder_ = OneHotEncoder(handle_unknown="ignore", sparse_output=False, dtype=np.float64)
        if self.active_columns_:
            cat_frame = X[self.active_columns_].astype(str).fillna("Missing")
            self.encoder_.fit(cat_frame)
            self.encoded_feature_names_ = [
                re.sub(r"[^A-Za-z0-9_]+", "_", name)
                for name in self.encoder_.get_feature_names_out(self.active_columns_)
            ]
        else:
            self.encoded_feature_names_ = []
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        out = X.copy()
        if not self.active_columns_:
            return out

        cat_frame = out[self.active_columns_].astype(str).fillna("Missing")
        encoded = self.encoder_.transform(cat_frame)
        encoded_df = pd.DataFrame(encoded, columns=self.encoded_feature_names_, index=out.index)
        out = out.drop(columns=self.active_columns_)
        return pd.concat([out, encoded_df], axis=1)
