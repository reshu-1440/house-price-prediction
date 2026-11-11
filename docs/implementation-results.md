# Implementation Results & Progress Log

> This document records **only verified, executed outcomes** from completed phases. Nothing is marked complete until its verification gate has actually passed. *(Note: Original commit SHAs listed below reflect pre-rewrite history prior to stripping `Data/house_prices.csv` per `TD-012`.)*

---

## Initial Baseline (Pre-Phase 0)

- **Initial Commit**: `Initialize & Add Dataset` *(later rewritten to exclude `Data/house_prices.csv` per `TD-012`)*
- **Tracked Files**:
  - `.gitignore` (ignores `.venv`, `Data/house_prices.csv`, etc.)
  - `Data/data_download.py` (downloads Kaggle `juhibhojani/house-price` and stages `Data/house_prices.csv`)
- **Local Raw Dataset (Gitignored)**:
  - `Data/house_prices.csv` (187,531 rows × 21 columns, 106,149,815 bytes / 101.05 MiB)
- **Untracked Exploratory Prototypes**:
  - `Data/data_check.py`
  - `Data/data_cleaning.py`
- **Verified Environment**:
  - Windows PowerShell
  - `.venv` running `Python 3.13.15`
  - Installed packages: `pandas==3.1.1`, `numpy==2.5.4`, `kagglehub==1.0.3`, `PyYAML==6.0.3`, `requests==2.34.2`

---

## Phase 0 — Project Documentation & AI Agent Configuration

- **Status**: `Completed`
- **Deliverables Created**:
  - Root entry point: `AGENTS.md`
  - `docs/` (9 files): `README.md`, `architecture.md`, `implementation-plan.md`, `implementation-results.md`, `technical-decisions.md`, `data-schema.md`, `api-documentation.md`, `setup-guide.md`, `known-issues.md`
  - `agents/` (17 files): `AGENTS.md`, `agent.md`, `architecture.md`, `implementation-plan.md`, `coding-standards.md`, `development-workflow.md`, `testing-guidelines.md`, `debugging-guidelines.md`, `security-guidelines.md`, `project-context.md`, `technology-stack.md`, `data-guidelines.md`, `api-guidelines.md`, `task-management.md`, `documentation-guidelines.md`, `decision-log.md`, `troubleshooting.md`
- **Verification**:
  - Verified all 27 markdown files exist and are substantive (`>= 100` chars), with 0 placeholders and 0 broken relative links.
  - Verified raw dataset schema observations directly against `Data/house_prices.csv` (`187531` rows × `21` columns, `81` unique locations, `119339` duplicate rows excluding `Index`, `9684` `Call for Price` records, `17665` nulls in `Price (in rupees)`, `187531` nulls in `Dimensions` and `Plot Area`).
- **Commit**: `5621ec9` (`Phase 0: Establish docs/ and agents/ knowledge base and AI agent instructions`)

---

## Phase 1 — Problem Definition & Data Sourcing

- **Status**: `Completed`
- **Deliverables Created/Updated**:
  - `README.md`, `.gitignore`, `requirements.txt`, `setup.py`
  - `config/config.yaml`
  - `src/__init__.py`, `src/utils/__init__.py`, `src/utils/config.py`
  - `src/data/__init__.py`, `src/data/load_data.py`
  - `tests/__init__.py`, `tests/unit/__init__.py`, `tests/unit/test_load_data.py`
- **Verification**:
  - Installed `setuptools==84.2.1`, `wheel==0.48.0`, `pytest==9.2.0` and editable package `house-price-prediction==0.1.0` in `.venv`.
  - `python -m pytest tests/unit/test_load_data.py -v`: `6 passed`.
  - `python -m src.data.load_data`: loaded `Data/house_prices.csv` with shape `(187531, 21)`, `81` locations, `0` exact full-row duplicates, `119339` duplicates excluding `Index`, `239.18 MB` memory usage.
- **Commit**: `051019d` (`Phase 1: Problem definition, project structure, and data sourcing setup`)

---

## Phase 2 — Data Understanding & EDA

- **Status**: `Completed`
- **Deliverables Created/Updated**:
  - `src/data/eda.py`
  - `notebooks/01_eda.py`
  - `tests/unit/test_eda.py`
  - `reports/eda_summary.md`, `reports/data_quality_report.json`, and 6 plots in `reports/figures/`
  - Updated `requirements.txt` and `setup.py` with `matplotlib`, `seaborn`, `scipy`
- **Verified Key Findings**:
  - `177,847` valid numeric prices (`median = 7,800,000 INR`, `mean = 11,981,344.19 INR`, `P25 = 4,840,000`, `P75 = 14,500,000`, `P99 = 70,000,000`, `max = 14,003,000,000 INR`); `9,684` `Call for Price`.
  - `Carpet Area` and `Super Area` are mutually exclusive across all `187,531` rows (`Carpet only = 106,858`, `Super only = 79,846`, `Both = 0`, `Neither = 827`).
  - `> 10` string entries appear `35` times in `Bathroom` and `22` times in `Balcony`.
  - `Transaction` counts: `Resale = 144,172`, `New Property = 42,565`, `Other = 709`, `NaN = 83`, `Rent/Lease = 2`.
- **Verification**:
  - `python -m pytest -v`: `9 passed`.
  - `python notebooks/01_eda.py`: completed exit code `0`, generated JSON, Markdown, and 6 PNG figures.
- **Commit**: `58edd69` (`Phase 2: Exploratory data analysis with visualizations and data quality report`)

---

## Phase 3 — Data Cleaning & Validation

- **Status**: `Completed`
- **Deliverables Created/Updated**:
  - `src/data/cleaning.py` (canonical price/area/count/parking parsers, `Index`-excluded deduplication, valid record filtering, missing-value handling, log10-IQR outlier filtering)
  - `src/data/validators.py` (`validate_raw_schema`, `validate_cleaned_data`, `assert_valid`, `SchemaValidationError`)
  - Refactored `src/data/eda.py` to reuse shared parsers from `src/data/cleaning.py`
  - `tests/unit/test_cleaning.py`
- **Verification**:
  - `python -m pytest -v`: `16 passed`.
  - Full dataset run (`clean_pipeline` + `validate_cleaned_data` on `Data/house_prices.csv`):
    - `187,531` raw -> `68,192` after `Index`-excluded dedup -> `65,048` valid sale listings with positive price & area -> `64,461` final rows × `20` columns after `2.5 * IQR` log10 outlier filter (`Price_in_rupees` bounds: `355,776.5`–`125,612,569.9` INR; `effective_area_sqft` bounds: `197.2`–`6,759.5` sqft).
    - All `10` schema/domain validation checks passed (`Price (in rupees)` absent, zero nulls in critical columns, zero duplicate rows).
- **Commit**: `8975b52` (`Phase 3: Data cleaning pipeline with validation and schema checks`)

---

## Phase 4 — Feature Engineering

- **Status**: `Completed`
- **Deliverables Created/Updated**:
  - `src/features/__init__.py`
  - `src/features/transformers.py` (`BHKExtractor`, `FloorExtractor`, `AreaFeatureBuilder`, `LocationEncoder`, `CategoricalEncoder`)
  - `src/features/build_features.py` (`extract_bhk`, `extract_floor_info`, `create_area_features`, `create_interaction_features`, `feature_pipeline`)
  - `tests/unit/test_features.py`
  - Updated `requirements.txt` and `setup.py` with `scikit-learn>=1.6.0` and `joblib>=1.4.0`
- **Verification**:
  - `python -m pytest -v`: `22 passed`.
  - Full cleaned dataset verification (`feature_pipeline` fit on 80% split, transformed on 20%): engineered `50` numeric/one-hot features across `51,568` train and `12,893` test samples with `0` NaNs and `All finite: True`.
- **Commit**: `57c0638` (`Phase 4: Feature engineering with custom transformers and encoding`)

---

## Phase 5 — Data Splitting & Validation

- **Status**: `Completed`
- **Deliverables Created/Updated**:
  - `src/data/split.py` (`create_price_bins`, `train_test_split_stratified`, `geographical_split`, `validate_no_leakage`, `save_splits`, `run_split_pipeline`)
  - `tests/unit/test_split.py`
  - Generated `data/processed/{train.csv,test.csv,split_metadata.json}` (gitignored CSV/runtime split outputs under `data/processed/` & `Data/processed/`)
- **Verification**:
  - `python -m pytest -v`: `27 passed`.
  - `python -m src.data.split`:
    - `train = 51,568` rows (`80.0%`), `test = 12,892` rows (`20.0%`).
    - Train-only `bathroom_count` median (`2.0`) and log10-IQR bounds applied to both splits.
    - Leakage validation: `index_disjoint = True`, `cross_split_duplicates = 0`, `leakage_column_absent = True`, KS statistic = `0.00409` (`p = 0.99499`).
    - Verified `geographical_split` cleanly isolates holdout cities (`pune`, `jaipur`) on the generated training split.
- **Commit**: `9c7640c` (`Phase 5: Train/test splitting with stratification and leakage validation`)

---

## Phase 6 — Model Development

- **Status**: `Completed`
- **Deliverables Created/Updated**:
  - `src/models/__init__.py`
  - `src/models/train.py` (`train_baseline`, `train_linear_models`, `train_decision_tree`, `train_random_forest`, `train_gradient_boosting`, `get_candidate_models`, `compare_models`, `run_model_comparison`)
  - `src/models/predict.py` (`predict`, `predict_single`)
  - `tests/unit/test_models.py`
  - `reports/model_comparison.md` and `reports/figures/model_comparison.png`
  - Updated `requirements.txt` and `setup.py` with `xgboost>=2.1.0` and `lightgbm>=4.5.0`
- **Verified Benchmark Results (`51,568` train / `12,892` test, `50` features)**:
  - `XGBoost`: Test R² = `0.8020`, MAE = `2,294,631.54 INR`, RMSE = `4,964,175.07 INR`, MAPE = `22.81%`, Fit = `5.395s`
  - `LightGBM`: Test R² = `0.8019`, MAE = `2,293,107.10 INR`, RMSE = `4,965,086.68 INR`, MAPE = `22.80%`, Fit = `4.732s`
  - `RandomForest`: Test R² = `0.7970`, MAE = `2,287,191.84 INR`, RMSE = `5,026,132.55 INR`, MAPE = `22.87%`, Fit = `35.915s`
  - `HistGradientBoosting`: Test R² = `0.7950`, MAE = `2,317,845.49 INR`, Fit = `10.893s`
  - `DecisionTree`: Test R² = `0.7484`, Fit = `0.870s`
  - `Ridge` / `LinearRegression` / `Lasso`: Test R² = `0.6386` / `0.6385` / `0.6382`
  - `Baseline_Median`: Test R² = `-0.0894`, MAE = `5,740,420.42 INR`
- **Verification**:
  - `python -m pytest -v`: `28 passed`.
  - `python -m src.models.train`: exited `0`, generated `reports/model_comparison.md` and `reports/figures/model_comparison.png`.
- **Commit**: `e3c684a` (`Phase 6: Model development with baseline and multiple regression algorithms`)

---

## Phase 7 — Hyperparameter Optimization

- **Status**: `Completed`
- **Deliverables Created/Updated**:
  - `src/models/hyperparameter_tuning.py` (`cross_validate_model`, `tune_random_forest`, `tune_gradient_boosting`, `save_best_params`, `run_hyperparameter_tuning`)
  - `config/hyperparameters.yaml`
  - `reports/tuning_results.md`
  - `tests/unit/test_tuning.py`
  - Updated `requirements.txt` and `setup.py` with `optuna>=4.0.0`
- **Verified Tuning Results (3-fold CV on `51,568` train / evaluated on `12,892` test)**:
  - `lightgbm` (Optuna, 12 trials): CV R² = `0.8082`, Train R² = `0.9318`, **Test R² = `0.8128`**, Train-Test Gap = `0.1190`, Test MAE = `2,206,793.51 INR`, Test RMSE = `4,827,094.43 INR`, Test MAPE = `22.12%`
  - `xgboost` (Optuna, 12 trials): CV R² = `0.8014`, Train R² = `0.9363`, Test R² = `0.8102`, Train-Test Gap = `0.1260`, Test MAE = `2,212,525.78 INR`, Test RMSE = `4,859,924.57 INR`, Test MAPE = `22.09%`
  - `random_forest` (RandomizedSearchCV, 6 iters): CV R² = `0.7915`, Train R² = `0.9389`, Test R² = `0.8019`, Train-Test Gap = `0.1370`, Test MAE = `2,235,657.22 INR`
- **Verification**:
  - `python -m pytest -v`: `29 passed`.
  - `python -m src.models.hyperparameter_tuning`: exited `0`, generated `config/hyperparameters.yaml` and `reports/tuning_results.md`; every tuned model beat its Phase 6 default.
- **Commit**: `debea12` (`Phase 7: Hyperparameter optimization with cross-validation and experiment tracking`)

---

## Phase 8 — Model Evaluation

- **Status**: `Completed`
- **Deliverables Created/Updated**:
  - `src/models/evaluate.py` (`compute_metrics`, `plot_residuals`, `plot_actual_vs_predicted`, `error_segmentation`, `plot_feature_importance`, `generate_evaluation_report`, `run_model_evaluation`)
  - `tests/unit/test_evaluate.py`
  - `reports/model_evaluation.md`, `reports/evaluation_metrics.json`, and 3 diagnostic figures (`residuals.png`, `actual_vs_predicted.png`, `feature_importance.png`) in `reports/figures/`
- **Verified Test Evaluation (`lightgbm_tuned`, `12,892` test rows)**:
  - `R² = 0.8128`, `Adjusted R² = 0.8121`
  - `MAE = ₹2,206,793.51`, `Median AE = ₹1,011,185.35`, `RMSE = ₹4,827,094.43`
  - `MAPE = 22.12%`, `Within ±20% = 58.38%`
  - Error segmentation confirmed higher accuracy on `New Property` (R²=`0.8348`, MAPE=`18.80%`) vs `Resale` (R²=`0.7985`, MAPE=`23.29%`), and top feature drivers `area_per_bhk`, `location_target_enc`, `effective_area_sqft`, `floor_ratio`.
- **Verification**:
  - `python -m pytest -v`: `31 passed`.
  - `python -m src.models.evaluate`: exited `0`, generated Markdown, JSON, and 3 diagnostic PNG charts.
- **Commit**: `b78be7d` (`Phase 8: Model evaluation with metrics, residual analysis, and error segmentation`)

---

## Phase 9 — MLflow & Model Management

- **Status**: `Completed`
- **Deliverables Created/Updated**:
  - `src/models/mlflow_tracking.py` (`setup_mlflow`, `log_experiment`, `register_model`, `transition_model_stage`, `load_production_model`, `run_tracked_training`)
  - `src/models/train.py` (added optional `track_mlflow=True` integration)
  - `src/data/cleaning.py` (hardened pandas 3.1 + PyArrow CoW compatibility via `.where(...)`)
  - `tests/unit/test_mlflow_tracking.py`
  - Updated `requirements.txt` and `setup.py` with `mlflow>=3.0.0`
- **Verification**:
  - `python -m pytest -v`: `32 passed`.
  - `python -m src.models.mlflow_tracking`:
    - Logged `xgboost` (`eb91eef55fa34382bef1fd94bcefef91`) and `lightgbm` (`7e76ad5be3084641bfdfc8fe8f7ae492`) runs with model signatures and evaluation artifacts to `mlflow_experiments/mlflow.db`.
    - Registered `house_price_regressor` version `1`, promoted alias `@production`, and verified `load_production_model` predictions matched original predictions (`registry_verified: true`).
- **Commit**: `0cc4de8` (`Phase 9: MLflow integration with experiment tracking and model registry`)

---

## Phase 10 — ML Pipeline Development

- **Status**: `Completed`
- **Deliverables Created/Updated**:
  - `src/pipeline/__init__.py`
  - `src/pipeline/training_pipeline.py` (`build_preprocessor`, `build_training_pipeline`, `save_pipeline`, `load_pipeline`, `run_training_pipeline`)
  - `src/pipeline/inference_pipeline.py` (`predict_from_raw`)
  - `src/features/transformers.py` (added module-scoped `RawInputNormalizer` & `FeatureMatrixAligner` for safe cross-process joblib serialization)
  - `models/metadata.json` (plus gitignored `models/house_price_pipeline.joblib`)
  - `tests/unit/test_pipeline.py`
- **Verification**:
  - `python -m pytest -v`: `33 passed`.
  - `python -m src.pipeline.training_pipeline`: trained end-to-end from `Data/house_prices.csv` (`51,568` train / `12,892` test, `50` features across `81` cities), achieved `R² = 0.8128`, `MAE = ₹2,206,793.51`, `RMSE = ₹4,827,094.43`, saved `models/house_price_pipeline.joblib` & `models/metadata.json`.
  - Cross-process `load_pipeline` + `predict_from_raw` on raw Bangalore 3 BHK `1500 sqft` dict returned `INR 14,742,100` (`147.42 Lac`).
- **Commit**: `f5ae07e` (`Phase 10: Reproducible ML pipeline with preprocessing and inference`)

---

## Phase 11 — Backend Development

- **Status**: `Completed`
- **Deliverables Created/Updated**:
  - `src/api/__init__.py`, `src/api/schemas.py`, `src/api/dependencies.py`, `src/api/middleware.py`, `src/api/app.py`
  - `tests/unit/test_schemas.py`
  - Updated `docs/api-documentation.md`, `requirements.txt`, and `setup.py` (`fastapi`, `uvicorn`, `pydantic`, `httpx`)
- **Verification**:
  - `python -m pytest -v`: `35 passed` (including `TestClient` tests for `/health`, `/model/info`, `/predict`, `/predict/batch`, `422` validation errors, and `503` unloaded-model behavior).
  - Live `uvicorn` HTTP server probe (`127.0.0.1:8012`): `/health` -> `200` (`healthy`), `/predict` -> `200` (`₹1.34 Cr`), `/predict/batch` -> `200` (`count=2`), invalid payload -> `422`.
- **Commit**: `2a02a04` (`Phase 11: FastAPI backend with Pydantic validation and prediction endpoints`)

---

## Phase 12 — Testing

- **Status**: `Completed`
- **Deliverables Created/Updated**:
  - `tests/conftest.py` (shared raw DataFrame, fast fitted pipeline, and API `TestClient` fixtures)
  - `tests/integration/__init__.py`, `tests/integration/test_api.py`, `tests/integration/test_training_flow.py`
  - `tests/model/__init__.py`, `tests/model/test_model_quality.py`, `tests/model/test_model_fairness.py`
  - `pytest.ini`, `pyproject.toml`, `Makefile`
  - Cleaned all lint findings across `src/` and `tests/` (`ruff`) and eliminated Pandas4 string-fill warning in `src/data/cleaning.py`
  - Updated `requirements.txt` with `pytest-cov>=5.0.0` and `ruff>=0.6.0`
- **Verification**:
  - `python -m ruff check src tests`: `All checks passed!` (`0` errors).
  - `python -m pytest --cov=src --cov-report=term-missing -v`: `41 passed` (`34` unit, `4` integration, `3` model tests; `82%` total statement coverage across `src/`, `97%` on `src/api/app.py`, `98%` on `src/data/validators.py` and `src/data/eda.py`).
- **Commit**: `7a91867` (`Phase 12: Comprehensive test suite with unit, integration, and model tests`)

---

## Phase 13 — Docker & CI/CD

- **Status**: `Completed` (local container daemon inactive on host; config & workflows validated)
- **Deliverables Created/Updated**:
  - `Dockerfile` (multi-stage `builder`, `trainer`, and non-root `runtime` with `HEALTHCHECK`)
  - `docker-compose.yml` (`api` + `mlflow` services), `.dockerignore`
  - `.github/workflows/ci.yml` (`lint-and-test` + `docker-build`), `.github/workflows/cd.yml` (tag/dispatch verification + ECR deploy template)
  - `scripts/build.sh`, `scripts/deploy.sh`
- **Verification**:
  - `docker compose config -q`: exited `0` (valid compose syntax and schema).
  - YAML & Dockerfile structural validation: `docker-compose.yml`, `.github/workflows/ci.yml`, `.github/workflows/cd.yml`, and `Dockerfile` multi-stage/non-root directives passed.
  - Note: Docker Desktop daemon (`desktop-linux`) was not running on the host (`docker info` exited `1`), so live `docker build` / container startup was not executed locally.
- **Commit**: `f6991ac` (`Phase 13: Docker containerization and GitHub Actions CI/CD pipelines`)

---

## Phase 14 — Cloud Deployment

- **Status**: `Completed`
- **Deliverables Created/Updated**:
  - `infrastructure/cloudformation.yaml` (13 AWS resources: S3 bucket, ECR repo, CloudWatch logs, IAM roles, ALB, TargetGroup `/health`, SecurityGroups, ECS Fargate cluster/task/service)
  - `config/production.yaml` & `scripts/aws_deploy.sh`
  - `src/api/app.py` (added `load_production_settings`, `APP_ENV=production` CORS binding, and `run_production_server`)
  - `docs/deployment_guide.md`, updated `docs/README.md`
  - Updated `tests/unit/test_schemas.py` with `test_load_production_settings`
- **Verification**:
  - CloudFormation YAML structure check: `13` resources and `4` outputs validated.
  - `python -m ruff check src tests`: `All checks passed!`.
  - `python -m pytest -v`: `42 passed` (verified after final edits).
- **Commit**: `614ba93` (`Phase 14: AWS cloud deployment infrastructure and production configuration`)

---

## Phase 15 — Monitoring

- **Status**: `Completed`
- **Deliverables Created/Updated**:
  - `config/monitoring_thresholds.yaml`
  - `src/monitoring/__init__.py`, `src/monitoring/data_drift.py` (KS test, PSI, Chi-squared + drift reports & PSI chart), `src/monitoring/prediction_drift.py` (distribution shift + robust anomaly flags), `src/monitoring/performance_monitor.py` (JSONL tracking + threshold alerting), `src/monitoring/dashboard.py` (HTML dashboard)
  - `tests/unit/test_monitoring.py`
  - Sample baseline vs. test monitoring outputs under `reports/monitoring/`
- **Verification**:
  - `python -m ruff check src tests`: `All checks passed!`.
  - `python -m pytest tests/unit/test_monitoring.py -v`: `2 passed` (verified drift alerts trigger on shifted data & degraded metrics).
  - Baseline vs. held-out test check (`1,000` samples each): `Data drift detected: False`, `Pred drift: False`, `Alert: False`; generated `reports/monitoring/monitoring_dashboard.html` and drift report artifacts.
- **Commit**: `e2f64e3` (`Phase 15: Monitoring system for data drift, prediction drift, and model performance`)

---

## Phase 16 — Model Retraining

- **Status**: `Completed`
- **Deliverables Created/Updated**:
  - `config/retraining.yaml`
  - `src/retraining/__init__.py`, `src/retraining/retrain.py` (`check_retraining_trigger`, `compare_models`, `approve_model`, `replace_production_model`, `retrain_model`), `src/retraining/scheduler.py` (`compute_model_age_days`, `evaluate_and_run_scheduled_retraining`, CLI `--dry-run`/`--force`), `src/retraining/versioning.py` (`bump_semver`, `list_model_versions`, `version_model`, `rollback_model`)
  - `docs/retraining_guide.md`, updated `docs/README.md` & `docs/architecture.md`
  - `tests/unit/test_retraining.py`
- **Verification**:
  - `python -m ruff check src tests`: `All checks passed!`.
  - `python -m src.retraining.scheduler --dry-run`: returned `status: dry_run`, `cron_schedule: 0 2 * * 0`, `should_retrain: false`.
  - `python -m src.retraining.scheduler --force`: trained candidate end-to-end, passed champion/challenger gate (`R² = 0.8128`, `MAE = ₹2,206,793.51`, `r2_delta = 0.0`), archived `models/versions/v0.1.0/`, and atomically swapped `models/house_price_pipeline.joblib` (`status: promoted`).
  - `python -m pytest --cov=src --cov-report=term-missing -v`: **`47 passed`** (`83%` statement coverage across `2,254` statements in `src/`).

---

## Post-Phase 16 — GitHub Push Fix & Automated Dataset Onboarding (`TD-012`)

- **Status**: `Completed`
- **Deliverables Created/Updated**:
  - Rewrote commit history to remove `Data/house_prices.csv` (`101.05 MiB` blob exceeding GitHub's `100 MB` limit) from all commits while preserving the exact local file (`SHA256: ED1E6A1A2D1158F458CEF164F7E977F2C32A1EE392AD218037C11851814EF1E3`)
  - `.gitignore`: added `Data/house_prices.csv` and `data/raw/`
  - `Data/data_download.py`: upgraded to automatically locate and stage `house_prices.csv` at `Data/house_prices.csv` via `kagglehub`, with `--force` and `--output` CLI options
  - `src/data/load_data.py`: added actionable `Data/data_download.py` hint when `Data/house_prices.csv` is missing
  - `Makefile`: added `download-data` target
  - `tests/unit/test_load_data.py`: added 2 unit tests covering missing-CSV download hint and `Data/data_download.py` staging/skip/`--force` behavior
  - Updated `README.md`, `docs/setup-guide.md`, `docs/technical-decisions.md` (`TD-012`), `docs/architecture.md`, `docs/deployment_guide.md`, `docs/implementation-plan.md`, `agents/decision-log.md`, and `agents/troubleshooting.md`
- **Verification**:
  - Largest Git blob in `refs/heads/main`: `0.23 MB` (`reports/figures/actual_vs_predicted.png`)
  - `python -m ruff check Data/data_download.py src tests`: `All checks passed!`
  - `python -m pytest -v`: `49 passed` (`46` unit/model/training-flow tests + `3` FastAPI `TestClient` integration tests) without requiring `Data/house_prices.csv` in Git.
