# Debugging Guidelines

## 1. Systematic Investigation Workflow

1. **Reproduce with Minimal Input**: Isolate the failure using a small DataFrame slice or single API payload before touching code.
2. **Read Full Tracebacks**: Identify the exact line, dtype, or shape mismatch rather than guessing.
3. **Check Upstream Data Assumptions**: Most ML bugs trace back to unexpected raw strings (`'> 10'`, commas in `'1,000 sqft'`, `'Ground out of 7'`, `NaN` as float vs `pd.NA`).
4. **Fix Root Cause, Not Symptoms**: Add a regression test in `tests/` for every non-trivial bug fixed.

---

## 2. Common Project Failure Areas

- **Area / Price Parsing Bugs**: Check regex extraction on inputs with commas (`1,250 sqft`), decimal prices (`1.40 Cr`), trailing spaces (`'37 Lac '`), or rare units (`marla`, `kanal`, `acre`).
- **Scikit-Learn Pipeline Errors**:
  - `ValueError: could not convert string to float` -> A categorical/text column leaked into numeric pass-through or was missed by `ColumnTransformer`.
  - `clone()` failure -> Transformer `__init__` modified/renamed parameters or omitted storing them with identical attribute names.
- **Train/Test Metric Anomalies**:
  - Suspiciously high `R² > 0.98` -> Immediately inspect for `Price (in rupees)` leakage or `Index`-masked duplicate listings present in both train and test.
- **Matplotlib on Headless / Script Execution**: Always set `matplotlib.use("Agg")` before importing `pyplot` in `src/` and `notebooks/01_eda.py` to avoid GUI backend hangs on Windows/CI.
