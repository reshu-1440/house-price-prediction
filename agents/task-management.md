# Task Management & Progress Reporting

## 1. Breaking Down a Phase
Before implementing Phase `N`:
1. Review the Phase `N` deliverables and verification gate in [`docs/implementation-plan.md`](../docs/implementation-plan.md) and [`agents/implementation-plan.md`](implementation-plan.md).
2. Break the phase into small, testable modules/functions.
3. Inspect existing code and configs first so new code integrates seamlessly.

## 2. Updating Progress Records
When Phase `N` finishes verification:
- Update the status table in `docs/implementation-plan.md` from `Pending`/`In Progress` to `Completed`.
- Add a dated section in `docs/implementation-results.md` listing:
  - Deliverables created/modified
  - Exact verification commands executed
  - Observed outputs/metrics (never extrapolated or estimated)
  - Commit hash / commit message

## 3. Reporting to the User
Every phase completion report MUST state accurately:
- What files were created or modified (clickable `file://` links).
- Exact verification commands run and their observed pass/fail outcomes.
- Confirmation of the git commit hash and message.
- Any caveats, environment limitations, or discovered quirks recorded in `docs/known-issues.md`.
