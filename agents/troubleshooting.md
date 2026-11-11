# Troubleshooting Guide

## 1. Windows PowerShell & Virtual Environment
- **Running Python without activating**: Always invoke `.\.venv\Scripts\python.exe` (or `.\.venv\Scripts\python.exe -m pytest`) so global Python never gets mixed up with project `.venv`.
- **ExecutionPolicy blocks `Activate.ps1`**: If `.\.venv\Scripts\Activate.ps1` is blocked by PowerShell policy, run executables directly via `.\.venv\Scripts\python.exe` and `.\.venv\Scripts\pip.exe`.

## 2. Dataset & CSV Issues
- **`DtypeWarning` / mixed column types on `Data/house_prices.csv`**: Pass `low_memory=False` to `pd.read_csv(...)`.
- **`FileNotFoundError: house_prices.csv`**: Legacy scripts (`Data/data_check.py`, `Data/data_cleaning.py`) assumed working directory `Data/`. Phase 1+ modules resolve `Data/house_prices.csv` relative to repo root via `config/config.yaml`.
- **`> 10` in `Bathroom` / `Balcony`**: Handle `'> 10'` explicitly before numeric casting (`str.replace('>', '', regex=False)` or mapping `'> 10'` -> `11`).
- **Comma-formatted areas (`1,000 sqft`)**: Strip commas before numeric regex extraction.

## 3. Plotting & Headless Runs
- **Tkinter / GUI thread errors in matplotlib**: Set `matplotlib.use("Agg")` at module import time before `import matplotlib.pyplot as plt` when generating saved figures in scripts/tests.

## 4. Python 3.13 Package Compatibility
- Check wheel availability when adding ML packages (`scikit-learn`, `xgboost`, `lightgbm`, `optuna`, `mlflow`, `fastapi`) in Phases 1–9; record any version constraints discovered in [`docs/known-issues.md`](../docs/known-issues.md).
