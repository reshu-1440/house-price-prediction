# System Architecture

> **Last Updated**: Phase 16 (All 17 Phases — Phase 0 through Phase 16 — Implemented)
> **Legend**: `[Implemented]` = present and verified in repo · `[Prototype]` = exploratory draft in `Data/`

---

## 1. Current Repository State `[Implemented]`

All planned engineering layers (Phases 0–16) are implemented in `src/`, `config/`, `tests/`, `docs/`, `agents/`, `infrastructure/`, `scripts/`, and `.github/workflows/`:
- **Raw Dataset `[Local / Gitignored]`**: `Data/house_prices.csv` (187,531 listings × 21 columns, 106.15 MB; excluded from Git via `.gitignore` and downloaded via `Data/data_download.py`).
- **Legacy Prototypes `[Prototype]`**: `Data/data_check.py`, `Data/data_cleaning.py` (superseded by `src/data/`).
- **Production ML System `[Implemented]`**: Config/utils, EDA, cleaning & validation, feature transformers, leakage-safe stratified/geo splitting, regression benchmark & Optuna HPO (`lightgbm` champion), residual/segment evaluation, MLflow SQLite tracking & `@production` registry, unified sklearn `Pipeline` (`models/house_price_pipeline.joblib`), FastAPI service, pytest suite, Docker & GitHub Actions CI/CD, AWS CloudFormation IaC, drift/performance monitoring, and automated retraining/versioning/rollback.

---

## 2. End-to-End Architecture `[Implemented]`

```text
[Data/house_prices.csv (Immutable Raw)]
        │
        ▼ (Phase 1: src/data/load_data.py + config/config.yaml)
[Phase 2: EDA & Data Quality Report] ──► reports/eda_summary.md, reports/figures/*.png
        │
        ▼ (Phase 3: src/data/cleaning.py + src/data/validators.py)
[Cleaned & Schema-Validated Dataset]
        │
        ▼ (Phase 5: src/data/split.py — Deduped & Stratified / Geo Split)
   ┌────┴────────────────────────────┐
   ▼                                 ▼
[Train Split]                 [Test Split (Held-Out)]
   │                                 │
   ▼ (Phase 4 & 10: Custom Sklearn Transformers & ColumnTransformer)
[Phase 6–7: Model Training & Optuna/CV Tuning] ──► [Phase 9: MLflow Tracking & Registry]
   │                                 │
   └──────────────┬──────────────────┘
                  ▼
         [Phase 8: Model Evaluation & Error Segmentation]
                  │
                  ▼ (Phase 10: Serialized Joblib / MLflow Pipeline)
         [Phase 11: FastAPI Inference Service (/health, /predict, /predict/batch)]
                  │
     ┌────────────┼──────────────────────┐
     ▼            ▼                      ▼
[Phase 12:    [Phase 13–14:          [Phase 15–16:
 Pytest]       Docker/GH Actions/     Drift/Perf Monitoring &
               AWS ECS/S3/ECR]        Champion/Challenger Retraining]
```

---

## 3. Module Boundaries `[Implemented]`

| Layer | Directory | Responsibility | Allowed Dependencies |
|-------|-----------|----------------|----------------------|
| Configuration | `config/` | YAML settings for paths, hyperparameters, monitoring thresholds, retraining, production | None (data only) |
| Utilities | `src/utils/` | Config loader, structured logging | Standard library, `PyYAML` |
| Data & Validation | `src/data/` | Loading, EDA, cleaning, schema validation, leakage-safe splitting | `src/utils`, `pandas`, `numpy`, `scipy` |
| Features | `src/features/` | Sklearn-compatible transformers (`BHKExtractor`, `FloorExtractor`, `LocationTargetEncoder`, etc.) | `scikit-learn`, `pandas`, `numpy` |
| Models & Tracking | `src/models/` | Training, HPO, evaluation metrics/plots, MLflow tracking/registry | `src/features`, `src/utils`, ML libs |
| Pipelines | `src/pipeline/` | End-to-end preprocessing+model training & raw-input inference pipelines | `src/data`, `src/features`, `src/models` |
| Backend API | `src/api/` | FastAPI app, Pydantic schemas, middleware, model dependency lifecycle | `src/pipeline`, `fastapi`, `pydantic` |
| Monitoring | `src/monitoring/` | Data drift (KS/PSI), prediction drift, performance tracking, alerts | `src/utils`, `scipy`, `pandas` |
| Retraining | `src/retraining/` | Trigger evaluation, champion/challenger comparison, approval, versioning/rollback | `src/pipeline`, `src/monitoring`, `src/models` |
| Tests | `tests/` | Unit (`tests/unit`), integration (`tests/integration`), model quality (`tests/model`) | `pytest` + target `src/` modules |
| Infra & CI/CD | `.github/`, `infrastructure/`, `scripts/` | Docker, GitHub Actions CI/CD, CloudFormation AWS stack | Infrastructure config |

---

## 4. Storage & Persistence Architecture

This project does **not** use a relational database (RDBMS). Persistence relies on:
1. **Raw & Processed Files**: Immutable CSV in `Data/house_prices.csv`; processed train/test splits in `data/processed/` (Phase 5).
2. **Model & Pipeline Artifacts**: Serialized `joblib` pipelines and version metadata in `models/` (Phase 10 & 16).
3. **Experiment & Registry Store**: Local MLflow tracking URI (SQLite backend + file artifact store in `mlflow_experiments/`, Phase 9).
4. **Monitoring Logs & Reports**: Structured JSON/CSV prediction & drift logs and Markdown/PNG evaluation reports in `reports/` (Phases 2, 8, 15).
