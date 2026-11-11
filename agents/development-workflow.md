# Development Workflow

## 1. One-Phase-at-a-Time Lifecycle

For every phase `N`:
1. **Plan & Inspect**:
   - Check `docs/implementation-plan.md` for Phase `N` deliverables and verification gate.
   - Read any existing related modules (including legacy `Data/data_check.py` / `Data/data_cleaning.py` during Phases 1–3).
2. **Environment Check**:
   - Ensure required dependencies for Phase `N` are installed in `.venv` and recorded in `requirements.txt` (starting Phase 1).
3. **Implement**:
   - Write clean, modular code under `src/`, `config/`, `tests/`, etc.
   - Write unit/integration tests alongside the implementation.
4. **Verify**:
   - Run all phase verification commands, scripts, and `pytest` tests.
   - Do **not** proceed to commit if any test or script fails.
5. **Document**:
   - Update `docs/implementation-plan.md` (mark Phase `N` `Completed`).
   - Append exact verified outcomes, commands run, and outputs to `docs/implementation-results.md`.
   - Record any architectural/design choices in `docs/technical-decisions.md` and `agents/decision-log.md`.
6. **Commit**:
   - Run `git status` and `git diff --stat` to verify clean staging.
   - Stage relevant files (`git add ...`) and commit with message: `Phase N: <concise description>`.

---

## 2. Handling Legacy Prototype Scripts (`Data/`)

- `Data/data_download.py`, `Data/data_check.py`, and `Data/data_cleaning.py` exist from initial exploration.
- Do not delete `Data/house_prices.csv` or break `Data/data_download.py`.
- During Phases 1–3, refactor useful parsing/cleaning logic from `Data/data_check.py` and `Data/data_cleaning.py` into `src/data/` modules rather than keeping duplicate business logic.
