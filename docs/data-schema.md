# Data & Storage Schema

> **Note**: This ML project uses file-based datasets, serialized model artifacts, MLflow tracking stores, and structured monitoring logs rather than a relational SQL database. This document describes every schema in the project and distinguishes **Verified Raw** from **Planned** schemas.

---

## 1. Raw Dataset Schema (`Data/house_prices.csv`) `[Verified]`

Observed directly on `Data/house_prices.csv`: **187,531 rows × 21 columns**.

| # | Column Name | Observed Raw Dtype | Null Count | % Null | Verified Notes & Anomalies |
|---|-------------|--------------------|------------|--------|----------------------------|
| 1 | `Index` | `int64` | 0 | 0.00% | Sequential row ID (`0..187530`); masks `119,339` duplicate rows |
| 2 | `Title` | `str` | 0 | 0.00% | Listing title; typically begins with `N BHK` (e.g., `3 BHK`: 80,848; `2 BHK`: 75,508) |
| 3 | `Description` | `str` | 3,023 | 1.61% | Free-text listing description |
| 4 | `Amount(in rupees)` | `str` | 0 | 0.00% | **Raw Target Source**: `112,568` `Lac`, `65,279` `Cr`, `9,684` `Call for Price` |
| 5 | `Price (in rupees)` | `float64` | 17,665 | 9.42% | Price per sqft (`min=0.0`, `median=6034.0`, `max=6.7e6`) — **FORBIDDEN as model feature (target leakage)** |
| 6 | `location` | `str` | 0 | 0.00% | `81` lowercase hyphenated Indian cities (top: `new-delhi` 27,599; `bangalore` 24,030; `kolkata` 22,380) |
| 7 | `Carpet Area` | `str` | 80,673 | 43.02% | Area string with mixed units (`sqft`: 100,428; `sqyrd`: 5,526; `sqm`: 894; `marla`/`acre`/`kanal`/etc.) |
| 8 | `Status` | `str` | 615 | 0.33% | Values: `'Ready to Move'`, `NaN` |
| 9 | `Floor` | `str` | 7,077 | 3.77% | Format like `'10 out of 11'`, `'Ground out of 7'` |
| 10 | `Transaction` | `str` | 83 | 0.04% | Values: `'Resale'`, `'New Property'`, `'Other'`, `'Rent/Lease'`, `NaN` |
| 11 | `Furnishing` | `str` | 2,897 | 1.54% | Values: `'Unfurnished'`, `'Semi-Furnished'`, `'Furnished'`, `NaN` |
| 12 | `facing` | `str` | 70,233 | 37.45% | Cardinal/intercardinal facing direction |
| 13 | `overlooking` | `str` | 81,436 | 43.43% | View/facing amenities (e.g., `'Garden/Park'`) |
| 14 | `Society` | `str` | 109,678 | 58.49% | Housing society/township name (high cardinality) |
| 15 | `Bathroom` | `str` | 828 | 0.44% | Numeric strings `'1'`..`'10'` plus `'> 10'` |
| 16 | `Balcony` | `str` | 48,935 | 26.09% | Numeric strings `'1'`..`'10'` plus `'> 10'` |
| 17 | `Car Parking` | `str` | 103,357 | 55.11% | Strings like `'1 Open'`, `'1 Covered'`, `'66 Covered'` |
| 18 | `Ownership` | `str` | 65,517 | 34.94% | `'Freehold'`, `'Co-operative Society'`, `'Power Of Attorney'`, `'Leasehold'`, `NaN` |
| 19 | `Super Area` | `str` | 107,685 | 57.42% | Area string with commas & mixed units (`sqft`: 75,353; `sqyrd`: 3,547; `sqm`: 873; comma numbers like `1,000 sqft`, etc.) |
| 20 | `Dimensions` | `float64` | 187,531 | 100.00% | Completely null across entire dataset |
| 21 | `Plot Area` | `float64` | 187,531 | 100.00% | Completely null across entire dataset |

---

## 2. Cleaned Schema (`src/data/cleaning.py`) `[Implemented: Phase 3]`

Verified output of `clean_pipeline` on `Data/house_prices.csv`: **64,461 rows × 20 columns**.

- **Target**:
  - `Price_in_rupees` (`float64`, strictly `> 0`): parsed from `Amount(in rupees)` (`Lac`/`Lakh` × `1e5`, `Cr`/`Crore` × `1e7`; `Call for Price` excluded).
- **Dropped Columns**: `Index`, `Dimensions`, `Plot Area`, `Price (in rupees)` (leakage), `Amount(in rupees)`, `Carpet Area`, `Super Area`, `Bathroom`, `Balcony`, `Car Parking` (replaced by parsed fields).
- **Cleaned & Parsed Columns**:
  - Numeric: `carpet_area_sqft`, `super_area_sqft`, `effective_area_sqft` (`carpet` coalesced with `super`), `bathroom_count` (`> 10` -> `11.0`, median-imputed `2.0`), `balcony_count` (`> 10` -> `11.0`, `0.0` when missing), `parking_count` (`0.0` when missing).
  - Categorical / Text: `Title`, `Description`, `location` (normalized lowercase), `Transaction` (`Resale`, `New Property`), `Status`, `Floor`, `Furnishing`, `facing`, `overlooking`, `Society`, `Ownership`, `area_type` (`carpet`, `super`), `parking_type` (`Covered`, `Open`, `Other`, `Missing`).

### Engineered Feature Matrix (`src/features/build_features.py`) `[Implemented: Phase 4]`

Verified **50 engineered features** (zero NaNs, all finite):
- **Extracted Structural Features**: `bhk`, `is_studio`, `is_penthouse`, `floor_number`, `total_floors`, `floor_ratio`, `is_ground_floor`, `is_top_floor`.
- **Area & Interaction Features**: `effective_area_sqft`, `log_effective_area`, `area_per_bhk`, `bathroom_per_bhk`, `total_rooms_proxy`, `bhk_x_log_area`, `is_carpet_area`, `has_society`, `has_overlooking`.
- **Location Encodings (`LocationEncoder`, out-of-fold during train `fit_transform`)**: `location_target_enc`, `location_log_target_enc`, `location_freq`.
- **One-Hot Categorical Encodings (`CategoricalEncoder`, `handle_unknown="ignore"`)**: encoded columns from `Transaction`, `Status`, `Furnishing`, `Ownership`, normalized `facing`, `area_type`, `parking_type`.

---

## 3. Model, MLflow & Monitoring Storage `[Planned: Phases 9, 10, 15, 16]`

| Store | Planned Path | Format | Purpose |
|-------|--------------|--------|---------|
| Processed Splits | `data/processed/{train,test}.csv` | CSV | Deduplicated, cleaned, leakage-validated splits (Phase 5) |
| MLflow Tracking | `mlflow_experiments/` | SQLite + Artifact dir | Runs, params, metrics, model signatures, Model Registry (Phase 9) |
| Serialized Pipeline | `models/house_price_pipeline.joblib` + `models/metadata.json` | Joblib + JSON | Production preprocessing + regression pipeline (Phase 10) |
| Version Archive | `models/versions/v*/` | Joblib + JSON manifest | Semantic versions & rollback checkpoints (Phase 16) |
| Monitoring Logs | `reports/monitoring/*.json` | JSON / JSONL | Prediction logs, KS/PSI drift reports, performance history (Phase 15) |
