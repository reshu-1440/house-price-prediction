# Agent Execution Plan Checklist

> Mirrors [`docs/implementation-plan.md`](../docs/implementation-plan.md) with agent execution order, dependencies, and exit gates.

---

## Execution Rules
- Work strictly sequentially: `Phase 0 -> Phase 1 -> ... -> Phase 16`.
- A phase is **complete** only after:
  1. All deliverables exist and pass functional/test verification.
  2. `docs/implementation-plan.md` & `docs/implementation-results.md` (plus any changed docs) are updated.
  3. Changes are committed cleanly with `Phase N: <summary>`.

---

## Phase Gates Summary

- **Phase 0**: `AGENTS.md`, `docs/`, `agents/` created & consistency-verified -> Commit.
- **Phase 1**: Package skeleton (`src/`, `config/config.yaml`, `README.md`, `requirements.txt`, `setup.py`, `.gitignore`) loads `Data/house_prices.csv` `(187531, 21)` -> Commit.
- **Phase 2**: `src/data/eda.py` + `notebooks/01_eda.py` produce `reports/eda_summary.md`, `reports/data_quality_report.json`, and `reports/figures/*.png` -> Commit.
- **Phase 3**: `src/data/cleaning.py` + `src/data/validators.py` parse prices/areas, deduplicate excluding `Index`, drop `Price (in rupees)`, remove outliers, pass unit tests -> Commit.
- **Phase 4**: `src/features/transformers.py` + `build_features.py` pass `fit`/`transform` & unseen-category unit tests -> Commit.
- **Phase 5**: `src/data/split.py` writes stratified + verified non-leaky `data/processed/{train,test}.csv` & validates geo split -> Commit.
- **Phase 6**: `src/models/{train,predict}.py` compare baseline, linear, tree, and boosting models -> Commit.
- **Phase 7**: `src/models/hyperparameter_tuning.py` tunes top models via CV/Optuna, saves `config/hyperparameters.yaml` -> Commit.
- **Phase 8**: `src/models/evaluate.py` produces full metrics, residual/QQ plots, feature importance, error segmentation -> Commit.
- **Phase 9**: `src/models/mlflow_tracking.py` logs runs, artifacts, signatures, and registers model in MLflow -> Commit.
- **Phase 10**: `src/pipeline/{training,inference}_pipeline.py` trains, saves, reloads, and predicts from raw dict -> Commit.
- **Phase 11**: `src/api/` FastAPI endpoints (`/health`, `/predict`, `/predict/batch`, `/model/info`) verified via TestClient/uvicorn + `docs/api-documentation.md` updated -> Commit.
- **Phase 12**: `tests/{unit,integration,model}/`, `pytest.ini`, `Makefile` achieve passing test suite with coverage -> Commit.
- **Phase 13**: `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `.github/workflows/{ci,cd}.yml`, `scripts/` validated -> Commit.
- **Phase 14**: `infrastructure/cloudformation.yaml`, `config/production.yaml`, `scripts/aws_deploy.sh`, `docs/deployment_guide.md` validated -> Commit.
- **Phase 15**: `src/monitoring/` drift + performance monitoring & threshold alerts verified by tests -> Commit.
- **Phase 16**: `src/retraining/` trigger, champion/challenger approval, semantic versioning, and rollback verified by tests -> Commit.
