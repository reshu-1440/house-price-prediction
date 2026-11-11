# Technology Stack

> Clearly distinguishes **Verified Installed** dependencies in `.venv` from **Planned** libraries introduced in upcoming phases.

---

## 1. Runtime & Environment `[Verified]`
- **OS**: Windows
- **Python**: `3.13.15` (`.venv\Scripts\python.exe`)
- **Version Control**: Git

## 2. Installed Packages `[Verified in .venv]`
- `pandas==3.1.1` — Tabular processing
- `numpy==2.5.4` — Numerical computing
- `PyYAML==6.0.3` — Configuration loading
- `kagglehub==1.0.3` — Dataset acquisition
- `requests==2.34.2` — HTTP client

## 3. Planned Stack by Phase `[Planned]`
- **EDA & Visualization (Phase 2, 8)**: `matplotlib`, `seaborn`, `scipy`
- **ML & Pipelines (Phase 3–10)**: `scikit-learn`, `joblib`, `xgboost` / `lightgbm` (subject to Python 3.13 wheel availability check in Phase 6), `optuna` (Phase 7)
- **Experiment Tracking & Registry (Phase 9)**: `mlflow`
- **Backend Serving (Phase 11)**: `fastapi`, `uvicorn`, `pydantic`
- **Testing & Quality (Phase 12)**: `pytest`, `pytest-cov`, `httpx`, `ruff` / `flake8`
- **Containerization & Cloud (Phase 13–14)**: `Docker`, `docker-compose`, `GitHub Actions`, `AWS CloudFormation` (ECS Fargate / ALB / ECR / S3)
- **Monitoring & Drift (Phase 15)**: `scipy` (KS test), custom PSI/drift & optional `streamlit` dashboard
