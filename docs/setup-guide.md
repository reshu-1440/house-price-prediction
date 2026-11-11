# Setup Guide

> **Verified Environment**: Windows · PowerShell · Python `3.13.15` in `.venv`

---

## 1. Prerequisites

- Git installed and configured
- Python `3.13.x` virtual environment at `.venv`
- `Data/house_prices.csv` is **gitignored** (because it is `101.05 MB` and exceeds GitHub's `100 MB` limit). When cloning onto a new machine, run `python Data/data_download.py` to download it from Kaggle (`juhibhojani/house-price`) into `Data/house_prices.csv`. (For most public Kaggle datasets `kagglehub` downloads directly; if prompted for auth, configure `~/.kaggle/kaggle.json` or `KAGGLE_USERNAME`/`KAGGLE_KEY`.)

---

## 2. Environment Setup on a Fresh Clone

Activate the virtual environment in Windows PowerShell:

```powershell
cd d:\Room_Project\house_price_prediction
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install --no-build-isolation --no-deps -e .
python --version
```

Verify installed packages:

```powershell
.\.venv\Scripts\python.exe -m pip list
```

---

## 3. Running Without vs. With the Dataset

- **Without `Data/house_prices.csv`**:
  - Linting (`python -m ruff check src tests`), unit/integration/model tests (`python -m pytest -v`), and `docker build --target runtime .` work out of the box using deterministic synthetic test fixtures.
  - Note: Without a trained `models/house_price_pipeline.joblib`, the FastAPI `/health` endpoint starts in `degraded` mode (`model_loaded: false`) and `/predict` returns `503` until training runs or a model artifact is provided via `MODEL_PATH`.
- **With `Data/house_prices.csv` (Full Training & Serving)**:
  1. Download and stage the CSV:
     ```powershell
     .\.venv\Scripts\python.exe Data/data_download.py
     ```
  2. Verify dataset loading (`(187531, 21)`):
     ```powershell
     .\.venv\Scripts\python.exe -m src.data.load_data
     ```
  3. Generate `models/house_price_pipeline.joblib` and `models/metadata.json`:
     ```powershell
     .\.venv\Scripts\python.exe -m src.pipeline.training_pipeline
     ```

---

## 4. Test Execution `[Verified]`

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

---

## 5. Serving & Docker Startup

- **Local FastAPI server**:
  ```powershell
  .\.venv\Scripts\python.exe -m uvicorn src.api.app:app --reload
  ```
- **Docker Compose (API + MLflow)**:
  ```powershell
  docker compose up -d --build
  ```
