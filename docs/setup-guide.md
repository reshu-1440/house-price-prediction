# Setup Guide

> **Verified Environment**: Windows · PowerShell · Python `3.13.15` in `.venv`

---

## 1. Prerequisites

- Git installed and configured
- Python `3.13.x` virtual environment at `.venv`
- Kaggle credentials (only needed if re-downloading `Data/house_prices.csv`; the CSV is already committed in `Data/house_prices.csv`)

---

## 2. Current Environment Setup `[Verified]`

Activate the virtual environment in Windows PowerShell:

```powershell
cd d:\Room_Project\house_price_prediction
.\.venv\Scripts\Activate.ps1
python --version
```

Verify current installed packages:

```powershell
.\.venv\Scripts\python.exe -m pip list
```

Currently verified packages in `.venv`:
- `pandas==3.1.1`
- `numpy==2.5.4`
- `kagglehub==1.0.3`
- `PyYAML==6.0.3`
- `requests==2.34.2`
- `setuptools==84.2.1`
- `wheel==0.48.0`
- `pytest==9.2.0`
- `house-price-prediction==0.1.0` (editable install via `pip install --no-build-isolation --no-deps -e .`)

---

## 3. Dataset Verification `[Verified]`

Confirm `Data/house_prices.csv` is accessible and loads via `src.data.load_data`:

```powershell
.\.venv\Scripts\python.exe -m src.data.load_data
```

---

## 4. Test Execution `[Verified]`

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

---

## 5. Planned Setup Steps `[Planned: Phases 2, 11, 13]`

- **Phase 2+**: Additional ML/visualization/API packages added incrementally per phase in `requirements.txt`.
- **Phase 11**: Run FastAPI server locally via `uvicorn src.api.app:app --reload`.
- **Phase 13**: Build and run containerized services via `docker compose up --build`.
