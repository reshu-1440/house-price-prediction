# Data & Storage Guidelines

> Replaces SQL `database-guidelines.md` because this project uses file-based datasets, `joblib` model artifacts, MLflow tracking stores, and JSON/CSV monitoring logs rather than a relational database.

---

## 1. Raw Data Immutability
- `Data/house_prices.csv` is **read-only**. Never overwrite, sort in place, or filter `Data/house_prices.csv` on disk.
- All derived datasets go under `data/processed/` (Phase 5+).

## 2. Target Leakage & Deduplication Rules
1. **Drop `Price (in rupees)` Immediately**: It is a per-sqft price column derived from the target `Amount(in rupees)`. Never include it in feature matrices or inference schemas.
2. **Deduplicate Excluding `Index`**: `Data/house_prices.csv` contains `119,339` duplicate rows masked solely by unique `Index` values. Always drop `Index` before deduplicating and before train/test splitting.
3. **Train-Only Fitting**: Fit target encoders, frequency maps, imputers, scalers, and outlier bounds exclusively on the training split.

## 3. Storage & Artifact Conventions
- **Processed Splits**: `data/processed/train.csv`, `data/processed/test.csv` (reproducible via `src/data/split.py`).
- **Model Artifacts**: `models/house_price_pipeline.joblib` + `models/metadata.json` (gitignored large binaries or managed via MLflow / semantic versioning in Phase 16).
- **MLflow Store**: `mlflow_experiments/` using local SQLite tracking (`sqlite:///mlflow_experiments/mlflow.db`) and artifact folder (Phase 9).
- **Monitoring Logs**: Append structured JSONL/JSON records under `reports/monitoring/` (Phase 15).
