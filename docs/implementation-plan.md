# Implementation Plan & Progress Tracker

> **Development Rule**: Build **one phase at a time**, verify every gate passes, synchronize `docs/` and `agents/`, and commit before moving to the next phase.

---

## Master Roadmap Overview

| Phase | Name | Status | Dependencies | Target Commit Scope |
|-------|------|--------|--------------|---------------------|
| 0 | Project Documentation & AI Agent Configuration | `Completed` | Initial repo (`b08cdf7`) | `AGENTS.md`, `docs/`, `agents/` |
| 1 | Problem Definition & Data Sourcing | `Completed` | Phase 0 | `README.md`, `config/`, `src/data/load_data.py`, `requirements.txt`, `setup.py` |
| 2 | Data Understanding & EDA | `Completed` | Phase 1 | `src/data/eda.py`, `notebooks/01_eda.py`, `reports/` |
| 3 | Data Cleaning & Validation | `Completed` | Phase 2 | `src/data/cleaning.py`, `src/data/validators.py`, `tests/unit/test_cleaning.py` |
| 4 | Feature Engineering | `Completed` | Phase 3 | `src/features/transformers.py`, `src/features/build_features.py`, `tests/unit/test_features.py` |
| 5 | Data Splitting & Validation | `Completed` | Phase 3, 4 | `src/data/split.py`, `data/processed/` |
| 6 | Model Development | `Completed` | Phase 4, 5 | `src/models/train.py`, `src/models/predict.py`, `reports/model_comparison.md` |
| 7 | Hyperparameter Optimization | `Pending` | Phase 6 | `src/models/hyperparameter_tuning.py`, `config/hyperparameters.yaml`, `reports/tuning_results.md` |
| 8 | Model Evaluation | `Pending` | Phase 6, 7 | `src/models/evaluate.py`, `reports/model_evaluation.md`, `reports/figures/` |
| 9 | MLflow & Model Management | `Pending` | Phase 6–8 | `src/models/mlflow_tracking.py`, `mlflow_experiments/` |
| 10 | ML Pipeline Development | `Pending` | Phase 3–9 | `src/pipeline/training_pipeline.py`, `src/pipeline/inference_pipeline.py`, `models/` |
| 11 | Backend Development | `Pending` | Phase 10 | `src/api/{app,schemas,dependencies,middleware}.py`, `docs/api-documentation.md` |
| 12 | Testing | `Pending` | Phase 1–11 | `tests/{unit,integration,model}/`, `pytest.ini`, `Makefile` |
| 13 | Docker & CI/CD | `Pending` | Phase 11, 12 | `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `.github/workflows/`, `scripts/` |
| 14 | Cloud Deployment | `Pending` | Phase 11, 13 | `infrastructure/cloudformation.yaml`, `config/production.yaml`, `scripts/aws_deploy.sh`, `docs/deployment_guide.md` |
| 15 | Monitoring | `Pending` | Phase 10, 11 | `src/monitoring/`, `config/monitoring_thresholds.yaml`, `tests/unit/test_monitoring.py` |
| 16 | Model Retraining | `Pending` | Phase 9, 10, 15 | `src/retraining/`, `config/retraining.yaml`, `docs/retraining_guide.md`, `tests/unit/test_retraining.py` |

---

## Detailed Phase Breakdown & Verification Gates

### Phase 0 — Project Documentation & AI Agent Configuration
- **Deliverables**: Root `AGENTS.md`, `docs/` (`README.md`, `architecture.md`, `implementation-plan.md`, `implementation-results.md`, `technical-decisions.md`, `data-schema.md`, `api-documentation.md`, `setup-guide.md`, `known-issues.md`), `agents/` guides.
- **Verification**: All files exist, accurately reflect workspace reality, contain zero secrets, and pass link/consistency checks.

### Phase 1 — Problem Definition & Data Sourcing
- **Deliverables**: `README.md`, `config/config.yaml`, `src/__init__.py`, `src/utils/{__init__.py,config.py}`, `src/data/{__init__.py,load_data.py}`, `requirements.txt`, `setup.py`, updated `.gitignore`.
- **Verification**: `load_data()` reads `Data/house_prices.csv` via `config/config.yaml` and verifies shape `(187531, 21)`.

### Phase 2 — Data Understanding & EDA
- **Deliverables**: `src/data/eda.py`, `notebooks/01_eda.py`, `reports/eda_summary.md`, `reports/data_quality_report.json`, `reports/figures/*.png`.
- **Verification**: Script runs cleanly end-to-end; summary report, JSON quality profile, and all plots exist.

### Phase 3 — Data Cleaning & Validation
- **Deliverables**: `src/data/cleaning.py`, `src/data/validators.py`, `tests/unit/test_cleaning.py`.
- **Verification**: Price & area parsing handle all discovered units; `Index`-excluded duplicates removed; outliers handled; schema validation and unit tests pass.

### Phase 4 — Feature Engineering
- **Deliverables**: `src/features/__init__.py`, `src/features/transformers.py`, `src/features/build_features.py`, `tests/unit/test_features.py`.
- **Verification**: Custom sklearn transformers support `fit`/`transform` cleanly without NaN/inf or unseen-category crashes; unit tests pass.

### Phase 5 — Data Splitting & Validation
- **Deliverables**: `src/data/split.py`, `data/processed/{train.csv,test.csv}`.
- **Verification**: ~80/20 stratified split + city-holdout geo-split verify zero overlap/leakage and preserved target distribution.

### Phase 6 — Model Development
- **Deliverables**: `src/models/__init__.py`, `src/models/{train.py,predict.py}`, `reports/model_comparison.md`, `reports/figures/model_comparison.png`.
- **Verification**: Baseline, linear (`Linear`/`Ridge`/`Lasso`), tree, and ensemble (`RandomForest`/`HistGradientBoosting`/`XGBoost`/`LightGBM`) models train and rank cleanly.

### Phase 7 — Hyperparameter Optimization
- **Deliverables**: `src/models/hyperparameter_tuning.py`, `config/hyperparameters.yaml`, `reports/tuning_results.md`.
- **Verification**: K-Fold CV + Optuna/RandomizedSearchCV complete; best params saved; tuned model beats defaults with controlled train/val gap.

### Phase 8 — Model Evaluation
- **Deliverables**: `src/models/evaluate.py`, `reports/model_evaluation.md`, residual/parity/feature-importance plots.
- **Verification**: MAE, RMSE, R², MAPE, Adjusted R², residual diagnostics, and error segmentation by city/price tier/BHK generated.

### Phase 9 — MLflow & Model Management
- **Deliverables**: `src/models/mlflow_tracking.py`, `mlflow_experiments/`, training integration.
- **Verification**: Experiments, parameters, metrics, artifacts, and registered model versions log and reload identically.

### Phase 10 — ML Pipeline Development
- **Deliverables**: `src/pipeline/__init__.py`, `src/pipeline/{training_pipeline.py,inference_pipeline.py}`, `models/house_price_pipeline.joblib`.
- **Verification**: Pipeline trains from raw CSV, serializes, reloads, and serves raw-dict inference accurately.

### Phase 11 — Backend Development
- **Deliverables**: `src/api/{__init__.py,app.py,schemas.py,dependencies.py,middleware.py}`, updated `docs/api-documentation.md`.
- **Verification**: `/health` returns 200; `/predict` and `/predict/batch` return valid predictions; `/model/info` returns metadata; invalid input returns 422.

### Phase 12 — Testing
- **Deliverables**: `tests/conftest.py`, `tests/unit/*`, `tests/integration/*`, `tests/model/*`, `pytest.ini`, `Makefile`.
- **Verification**: Full `pytest` suite passes with coverage report.

### Phase 13 — Docker & CI/CD
- **Deliverables**: `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `.github/workflows/{ci.yml,cd.yml}`, `scripts/{build.sh,deploy.sh}`.
- **Verification**: Compose/workflow YAML valid; container builds and runs if Docker daemon is present (or validated locally with explicit environment status noted).

### Phase 14 — Cloud Deployment
- **Deliverables**: `infrastructure/cloudformation.yaml`, `scripts/aws_deploy.sh`, `config/production.yaml`, `docs/deployment_guide.md`.
- **Verification**: CloudFormation template validates; production config loads cleanly and API runs with production settings.

### Phase 15 — Monitoring
- **Deliverables**: `src/monitoring/{__init__.py,data_drift.py,prediction_drift.py,performance_monitor.py,dashboard.py}`, `config/monitoring_thresholds.yaml`, `tests/unit/test_monitoring.py`.
- **Verification**: Synthetic shifted data triggers drift alerts; baseline data passes; performance drop triggers alert; unit tests pass.

### Phase 16 — Model Retraining
- **Deliverables**: `src/retraining/{__init__.py,retrain.py,scheduler.py,versioning.py}`, `config/retraining.yaml`, `docs/retraining_guide.md`, `tests/unit/test_retraining.py`.
- **Verification**: Retraining trigger check, champion/challenger comparison, approval gate, semantic versioning, and rollback all pass tests.
