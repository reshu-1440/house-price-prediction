# AI Agent Operating Guide (`agent.md`)

## 1. Agent Responsibilities

As an AI coding agent working in this repository, you are responsible for:
- Delivering clean, modular, verified Python ML engineering code phase by phase.
- Preserving data integrity and preventing train/test or target leakage at every stage.
- Keeping `docs/` and `agents/` synchronized with actual implementation progress.
- Running all relevant checks after your final edit in a phase before committing.

---

## 2. Standard Execution Approach

1. **Read Context First**:
   - Read root `AGENTS.md`.
   - Check `docs/implementation-plan.md` and `docs/implementation-results.md` to confirm which phase is active and what already exists.
   - Check `docs/technical-decisions.md` and `docs/known-issues.md` before designing changes.
2. **Inspect Before Editing**:
   - Read target files/functions directly; never assume file contents or symbol names from memory.
3. **Implement Only the Current Phase**:
   - Follow the single-phase discipline: complete, verify, document, and commit Phase `N` before starting Phase `N+1`.
   - Reuse existing utilities (`src/utils/`, `config/`) rather than duplicating helpers.
4. **Verify Strictly**:
   - Run imports, scripts, linters, and `pytest` checks using `.venv\Scripts\python.exe`.
   - Confirm outputs on disk (`reports/`, `data/processed/`, `models/`, etc.) and inspect exact stdout/stderr.
5. **Sync Documentation**:
   - Update `docs/implementation-plan.md` (status), `docs/implementation-results.md` (verified results), and any affected schemas/decisions/guides.
6. **Commit Cleanly**:
   - Review `git status` and `git diff` to ensure no stray temporary files or secrets are staged.
   - Commit with a descriptive phase message (e.g., `Phase 1: ...`).

---

## 3. Quality & Accuracy Contract

- **No Fabricated Claims**: Only cite file paths, function names, metrics, and test outcomes directly observed in files you read/wrote or tool output from the current session.
- **No Shortcuts**: Do not skip validation checks, relax assertions to pass broken tests, or include leaky columns (`Price (in rupees)`) to inflate metrics.
- **Clear Status Boundaries**: Keep implemented behavior strictly separated from planned future phases.
