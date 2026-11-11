# Technical Architecture Guide for Agents

> See [`docs/architecture.md`](../docs/architecture.md) for the full system overview and current-vs-planned component status.

---

## 1. Target Module Dependency Rules

Enforce a clean directed acyclic graph (DAG) across `src/` packages:

```text
config/*.yaml
    ▲
src/utils/ (config loader, logger)
    ▲
src/data/ (load_data, eda, cleaning, validators, split)
    ▲
src/features/ (sklearn transformers, build_features)
    ▲
src/models/ (train, predict, evaluate, hyperparameter_tuning, mlflow_tracking)
    ▲
src/pipeline/ (training_pipeline, inference_pipeline)
    ▲
    ├──► src/api/ (FastAPI app, schemas, dependencies, middleware)
    ├──► src/monitoring/ (data_drift, prediction_drift, performance_monitor, dashboard)
    └──► src/retraining/ (retrain, scheduler, versioning)
```

### Strict Boundary Rules
- **Never** import `src.api` inside `src.data`, `src.features`, `src.models`, or `src.pipeline`.
- **Never** import training-only scripts inside `src/api/app.py`; the API calls `src/pipeline/inference_pipeline.py` against a serialized pipeline artifact (`models/house_price_pipeline.joblib` or MLflow Registry model).
- **Never** hardcode file paths inside `src/` modules; resolve paths via `src/utils/config.py` backed by `config/config.yaml`.

---

## 2. Inference vs. Training Parity

- Preprocessing logic (regex extractors for BHK/Floor/Area, imputation, encodings) MUST live in custom scikit-learn `BaseEstimator`/`TransformerMixin` classes (`src/features/transformers.py`) combined in `ColumnTransformer` / `Pipeline` (`src/pipeline/training_pipeline.py`).
- This guarantees that raw JSON inputs sent to `POST /predict` pass through the exact same deterministic transformations used during training, preventing training-serving skew.
