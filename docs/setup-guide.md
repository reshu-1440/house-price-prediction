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

---

## 3. Dataset Verification `[Verified]`

Confirm `Data/house_prices.csv` is accessible and has shape `(187531, 21)`:

```powershell
.\.venv\Scripts\python.exe -c "import pandas as pd; df = pd.read_csv('Data/house_prices.csv', low_memory=False); print(df.shape)"
```

---

## 4. Planned Setup Steps `[Planned: Phases 1, 11–13]`

- **Phase 1**: Install project dependencies from `requirements.txt` and editable package install (`pip install -e .`).
- **Phase 11**: Run FastAPI server locally via `uvicorn src.api.app:app --reload`.
- **Phase 12**: Run test suite via `pytest`.
- **Phase 13**: Build and run containerized services via `docker compose up --build`.
