# Technical Decisions Log

> Records architectural and engineering choices made across the project lifecycle, including context, options evaluated, rationale, and implications. Synchronized with [`agents/decision-log.md`](../agents/decision-log.md).

---

## TD-001: Keep Raw Dataset at `Data/house_prices.csv`
- **Date**: 2026-11-12 (Phase 0)
- **Status**: Accepted
- **Context**: `Data/house_prices.csv` (106.15 MB) is already tracked in Git commit `b08cdf7`. Moving it to `data/raw/house_prices.csv` would duplicate or rewrite a large binary blob in Git history.
- **Decision**: Keep the immutable raw dataset at `Data/house_prices.csv` and configure `config/config.yaml` to point to `Data/house_prices.csv`, while using `data/processed/` for generated train/test splits.
- **Consequences**: Zero unnecessary Git repository bloat; all modules must load the path via config rather than hardcoding.

## TD-002: Use File + MLflow Persistence Instead of an RDBMS
- **Date**: 2026-11-12 (Phase 0)
- **Status**: Accepted
- **Context**: Standard software templates often include SQL database schemas (`database-schema.md`). This project operates on static/batch property CSV data, serialized `joblib` pipelines, MLflow tracking stores, and JSON/CSV monitoring logs without user accounts or transactional CRUD entities.
- **Decision**: Document dataset, pipeline artifact, MLflow, and monitoring storage schemas in [`docs/data-schema.md`](data-schema.md) instead of inventing an unused SQL schema.
- **Consequences**: Keeps documentation honest and directly aligned with project scope. If a user-facing prediction history DB is ever added later, a dedicated SQL schema document can be introduced then.

## TD-003: Exclude `Price (in rupees)` from Input Features (Leakage Prevention)
- **Date**: 2026-11-12 (Phase 0)
- **Status**: Accepted
- **Context**: Inspection of `Data/house_prices.csv` confirmed `Price (in rupees)` is the property's price per square foot (`17,665` nulls, `median = 6034.0`), derived directly from the listing's total price (`Amount(in rupees)`) divided by area.
- **Decision**: Strictly forbid `Price (in rupees)` as a model input feature; only `Amount(in rupees)` -> `Price_in_rupees` is the target, and any `price_per_sqft` analysis is restricted to EDA or training-target diagnostics / out-of-fold location statistics.
- **Consequences**: Prevents artificial 0.99+ R² data leakage and ensures the inference API works from real property attributes when total price is unknown.

## TD-004: Deduplicate Excluding `Index` Before Splitting
- **Date**: 2026-11-12 (Phase 0)
- **Status**: Accepted
- **Context**: Direct inspection of `Data/house_prices.csv` revealed `0` full-row duplicates (because `Index` is `0..187530`), yet `119,339` duplicate rows once `Index` is excluded (~63.6% of rows).
- **Decision**: Deduplicate records excluding `Index` during Phase 3 cleaning (and verify zero exact feature+target overlap between train and test in Phase 5).
- **Consequences**: Eliminates train/test memorization across identical scraped listings and produces honest generalization metrics.

## TD-005: Expand Geographic Scope Beyond 3 Prototype Cities
- **Date**: 2026-11-12 (Phase 0)
- **Status**: Accepted
- **Context**: Exploratory script `Data/data_cleaning.py` filtered to 3 cities (`new-delhi`, `bangalore`, `ahmedabad`). The full dataset covers `81` Indian cities.
- **Decision**: Support all 81 cities in the modular `src/` pipeline via configuration (defaulting to full-dataset training with optional city filtering in `config/config.yaml`) and handle high-cardinality cities with smoothed/out-of-fold target + frequency encoding.
- **Consequences**: Generalizes across all cities present in the dataset while preserving configurable city-subset experimentation and geographic holdout validation.

## TD-006: Unify Area Columns and Apply Log10-IQR (`2.5`) Outlier Bounds
- **Date**: 2026-11-12 (Phase 3)
- **Status**: Accepted
- **Context**: Phase 2 EDA established that `Carpet Area` and `Super Area` are mutually exclusive (`Both = 0`) and that raw numeric values span corrupt extremes (`1,400.3 Cr` price, `1.27B sqft` area). Linear IQR would discard legitimate metro luxury apartments.
- **Decision**: Coalesce area into `effective_area_sqft` alongside an explicit `area_type` indicator (`carpet` vs. `super`), and apply `log10` IQR (`factor = 2.5`) bounds on `Price_in_rupees` and `effective_area_sqft` (accepting pre-computed bounds from training splits).
- **Consequences**: Preserves `99.11%` of valid deduplicated sale listings across all 81 cities while stripping corrupt extremes and retaining area measurement semantics.

## TD-007: Split Before Fitting Imputers & Outlier Bounds
- **Date**: 2026-11-12 (Phase 5)
- **Status**: Accepted
- **Context**: Applying global medians (`bathroom_count`) or global quantile/log-IQR bounds before splitting leaks test distribution statistics into training.
- **Decision**: Perform only deterministic row-level deduplication and parsing prior to `train_test_split_stratified`, then fit `bathroom_median` and log10-IQR `outlier_bounds` strictly on the training split and apply them to both splits.
- **Consequences**: Zero train/test statistical leakage while maintaining identical schema and distribution parity (`KS p = 0.99499`).

## TD-008: Wrap Regressors with `TransformedTargetRegressor(log1p / expm1)`
- **Date**: 2026-11-12 (Phase 6)
- **Status**: Accepted
- **Context**: Target `Price_in_rupees` is strongly right-skewed (`3.5 Lac` to `12.9 Cr`), causing raw linear/MSE objectives to focus disproportionately on luxury outliers and occasionally predict negative prices for linear models.
- **Decision**: Wrap regression algorithms with `sklearn.compose.TransformedTargetRegressor(func=np.log1p, inverse_func=np.expm1)` while preserving standard INR predictions via `.predict()`.
- **Consequences**: Stabilizes variance across metro/non-metro price tiers, improves relative percentage accuracy (`MAPE`), and guarantees strictly positive predictions.
