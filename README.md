# House Price Prediction — End-to-End ML Engineering Project

An end-to-end machine learning engineering workflow to predict residential property sale prices (`Price_in_rupees`) across **81 Indian cities** using the Kaggle `juhibhojani/house-price` dataset (`Data/house_prices.csv`).

---

## 1. Business Problem & Target Definition

- **Objective**: Estimate fair market sale prices for residential apartments and houses in India from listing attributes (`location`, area, BHK configuration, floor level, transaction type, furnishing, ownership, parking, bathrooms, balconies).
- **Dataset**: `Data/house_prices.csv` (`187,531` rows × `21` columns covering `81` Indian cities).
- **Target Variable**: `Price_in_rupees` (numeric value in INR parsed from `Amount(in rupees)` where `Lac` = `10^5` INR and `Cr` = `10^7` INR; `Call for Price` rows excluded).
- **Strict Leakage Safeguards**:
  - `Price (in rupees)` (derived price-per-sqft column) is **never** used as a model input feature.
  - Exact duplicates masked by `Index` (`119,339` rows) are removed prior to train/test splitting.

---

## 2. Repository Structure

- `AGENTS.md` & `agents/` — AI coding agent instructions, standards, workflows, and decision log
- `docs/` — Project documentation, architecture, roadmap, data schemas, deployment, and verified implementation results
- `config/` — Central YAML configuration (`config.yaml`, `hyperparameters.yaml`, `production.yaml`, `monitoring_thresholds.yaml`, `retraining.yaml`)
- `Data/data_download.py` — Automated Kaggle dataset downloader staging `Data/house_prices.csv` (raw CSV is gitignored because it exceeds GitHub's 100 MB limit)
- `src/` — Modular ML engineering package (`utils/`, `data/`, `features/`, `models/`, `pipeline/`, `api/`, `monitoring/`, `retraining/`)
- `tests/` — Unit, integration, and model quality/fairness tests (`pytest`)
- `infrastructure/`, `scripts/`, `Dockerfile`, `docker-compose.yml`, `.github/workflows/` — Containerization, CI/CD, and AWS ECS deployment

---

## 3. Quickstart for Teammates (Clone & Run)

### Option A — Run Tests, Lint & Container Build (No Dataset Required)

All `pytest` tests and `ruff` checks use self-contained synthetic fixtures and run immediately after cloning:

```powershell
# 1. Create and activate virtual environment (Windows PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies and package in editable mode
pip install -r requirements.txt
pip install --no-build-isolation --no-deps -e .

# 3. Verify lint and tests without downloading the 101 MB dataset
python -m ruff check src tests
python -m pytest -v
```

### Option B — Full Training, Local Serving & Deployment (With Dataset)

Because `Data/house_prices.csv` (`101.05 MB`) exceeds GitHub's `100 MB` file limit, it is gitignored and fetched cleanly from Kaggle:

```powershell
# 1. Download Data/house_prices.csv via kagglehub
python Data/data_download.py

# 2. Verify dataset loading
python -m src.data.load_data

# 3. Train and serialize models/house_price_pipeline.joblib
python -m src.pipeline.training_pipeline

# 4. Serve FastAPI predictions locally (http://127.0.0.1:8000/docs)
uvicorn src.api.app:app --host 0.0.0.0 --port 8000

# 5. Or build & start Docker Compose services (API + MLflow)
docker compose up -d --build
```

---

## 4. Phased Roadmap

Development strictly follows the 17-phase roadmap (`Phase 0` through `Phase 16`) tracked in [`docs/implementation-plan.md`](docs/implementation-plan.md) and [`docs/implementation-results.md`](docs/implementation-results.md).
