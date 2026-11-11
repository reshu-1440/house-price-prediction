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

## 2. Repository Structure (Current & Planned)

- `AGENTS.md` & `agents/` — AI coding agent instructions, standards, workflows, and decision log
- `docs/` — Project documentation, architecture, roadmap, data schemas, and verified implementation results
- `config/config.yaml` — Central project configuration
- `Data/house_prices.csv` — Immutable raw dataset
- `src/` — Modular ML engineering package (`utils/`, `data/`, and upcoming `features/`, `models/`, `pipeline/`, `api/`, `monitoring/`, `retraining/`)
- `tests/` — Automated tests (expanded phase by phase)

---

## 3. Quickstart (Windows PowerShell)

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install package in editable mode
pip install -e .

# Verify configuration and raw dataset loading
python -m src.data.load_data
```

---

## 4. Phased Roadmap

Development strictly follows the 17-phase roadmap (`Phase 0` through `Phase 16`) tracked in [`docs/implementation-plan.md`](docs/implementation-plan.md) and [`docs/implementation-results.md`](docs/implementation-results.md).
