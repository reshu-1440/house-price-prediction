# Testing Guidelines

## 1. Test Pyramid & Directory Structure (`tests/`)

| Category | Directory | Purpose | Speed Target |
|----------|-----------|---------|--------------|
| Unit Tests | `tests/unit/` | Parsing, cleaning, schema validators, feature transformers, Pydantic schemas, drift math, versioning | Fast (< 5s total) using synthetic DataFrames |
| Integration Tests | `tests/integration/` | FastAPI endpoints (`TestClient`), end-to-end training flow on sample dataset | Moderate (< 30s) |
| Model Quality Tests | `tests/model/` | Regression quality thresholds (`R²`, `MAE`), prediction sanity (monotonicity with area/BHK), cross-city consistency | Runs against saved/trained pipeline |

---

## 2. Testing Rules

1. **Never Depend on the 106 MB Raw CSV in Unit Tests**: Construct small, deterministic synthetic pandas DataFrames in `tests/conftest.py` covering edge cases (`Call for Price`, `> 10` bathrooms, `Ground out of 7`, `1,000 sqft`, `sqyrd`/`sqm`/`acre`, duplicate rows with distinct `Index`, unseen cities).
2. **Test Edge Cases Explicitly**:
   - Empty DataFrames or missing optional columns
   - `None` / `NaN` values
   - Invalid API request payloads (`422` validation check)
   - Zero/negative areas or prices
3. **Strict Truthfulness**:
   - Never mock away the logic you claim to test in unit tests, and never relax assertions just to force a green test run.
   - Only report tests as passing after running `pytest` after your final edit.
4. **Execution Commands**:
   ```powershell
   .\.venv\Scripts\python.exe -m pytest --cov=src --cov-report=term-missing -v
   .\.venv\Scripts\python.exe -m ruff check src tests
   ```
