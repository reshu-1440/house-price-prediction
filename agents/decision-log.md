# Agent & Engineering Decision Log

> Append-only chronological register synchronized with [`docs/technical-decisions.md`](../docs/technical-decisions.md).

| ID | Date | Phase | Decision | Canonical Detail |
|----|------|-------|----------|------------------|
| TD-001 | 2026-11-12 | Phase 0 | Keep local raw CSV path at `Data/house_prices.csv` (gitignored via TD-012) | [docs/technical-decisions.md#td-001](../docs/technical-decisions.md#td-001-keep-raw-dataset-at-datahouse_pricescsv) |
| TD-002 | 2026-11-12 | Phase 0 | Document file/MLflow/log schemas in `docs/data-schema.md` & `agents/data-guidelines.md` rather than inventing an unused SQL DB schema | [docs/technical-decisions.md#td-002](../docs/technical-decisions.md#td-002-use-file--mlflow-persistence-instead-of-an-rdbms) |
| TD-003 | 2026-11-12 | Phase 0 | Ban `Price (in rupees)` from features to prevent target leakage | [docs/technical-decisions.md#td-003](../docs/technical-decisions.md#td-003-exclude-price-in-rupees-from-input-features-leakage-prevention) |
| TD-004 | 2026-11-12 | Phase 0 | Deduplicate excluding `Index` (`119,339` masked duplicates) before train/test split | [docs/technical-decisions.md#td-004](../docs/technical-decisions.md#td-004-deduplicate-excluding-index-before-splitting) |
| TD-005 | 2026-11-12 | Phase 0 | Support all 81 cities via config instead of hardcoding 3 prototype cities | [docs/technical-decisions.md#td-005](../docs/technical-decisions.md#td-005-expand-geographic-scope-beyond-3-prototype-cities) |
| TD-006 | 2026-11-12 | Phase 3 | Unify Carpet/Super Area into `effective_area_sqft` + `area_type`; use `log10` 2.5*IQR outlier bounds | [docs/technical-decisions.md#td-006](../docs/technical-decisions.md#td-006-unify-area-columns-and-apply-log10-iqr-25-outlier-bounds) |
| TD-007 | 2026-11-12 | Phase 5 | Split before computing `bathroom_median` and log10-IQR `outlier_bounds` | [docs/technical-decisions.md#td-007](../docs/technical-decisions.md#td-007-split-before-fitting-imputers--outlier-bounds) |
| TD-008 | 2026-11-12 | Phase 6 | Wrap regressors with `TransformedTargetRegressor(log1p/expm1)` for skewed INR prices | [docs/technical-decisions.md#td-008](../docs/technical-decisions.md#td-008-wrap-regressors-with-transformedtargetregressorlog1p--expm1) |
| TD-009 | 2026-11-12 | Phase 7 | Select Optuna-tuned LightGBM (`test_r2=0.8128`, `cv_r2=0.8082`) as primary model | [docs/technical-decisions.md#td-009](../docs/technical-decisions.md#td-009-select-tuned-lightgbm-as-primary-model-candidate) |
| TD-010 | 2026-11-12 | Phase 9 | Use MLflow 3.18 SQLite store, `@production` aliases, and `cloudpickle` serialization | [docs/technical-decisions.md#td-010](../docs/technical-decisions.md#td-010-use-mlflow-318-sqlite-store-alias-promotion-and-cloudpickle-serialization) |
| TD-011 | 2026-11-12 | Phase 16 | Champion/challenger approval gate + semantic versioning + atomic `os.replace` swaps | [docs/technical-decisions.md#td-011](../docs/technical-decisions.md#td-011-championchallenger-gate-with-atomic-osreplace-versioned-swaps) |
| TD-012 | 2026-11-12 | Post-Phase 16 | Strip `Data/house_prices.csv` (101.05 MiB) from Git history, `.gitignore` it, and automate staging via `Data/data_download.py` | [docs/technical-decisions.md#td-012](../docs/technical-decisions.md#td-012-exclude-raw-dataset-datahouse_pricescsv-from-git-history--automate-download) |
| TD-013 | 2026-11-12 | Post-Phase 16 | Add React + Vite + TypeScript SPA in `frontend/`, `GET /locations`, Vite CORS + `X-Process-Time-Ms` exposure, and `start.bat --frontend` / `--fullstack` | [docs/technical-decisions.md#td-013](../docs/technical-decisions.md#td-013-build-react--vite--typescript-frontend-aligned-11-with-fastapi--trained-pipeline) |
