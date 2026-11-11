# Project Documentation Index (`docs/`)

Welcome to the central knowledge base for the **House Price Prediction** end-to-end machine learning project.

> **Maintenance Principle**: Documentation evolves alongside the codebase. Every file clearly separates **Implemented** functionality from **Planned** work. No assumptions or unverified numbers are recorded as facts.

---

## Document Directory

| Document | Purpose | Status |
|----------|---------|--------|
| [architecture.md](architecture.md) | High-level system architecture, component responsibilities, and end-to-end data/ML/serving flows | Living (Phase 0 baseline + Planned Phases 1–16) |
| [implementation-plan.md](implementation-plan.md) | Full 17-phase roadmap (Phase 0–16), deliverables, dependencies, verification gates, and progress checklist | Living |
| [implementation-results.md](implementation-results.md) | Record of completed phases, files created, verification commands run, and observed metrics | Living |
| [technical-decisions.md](technical-decisions.md) | Architectural and technical decisions (`TD-*`), options considered, and rationale | Living |
| [data-schema.md](data-schema.md) | Verified raw CSV schema (21 columns), target derivation, cleaned/engineered schemas, and file/MLflow/monitoring storage schemas *(replaces generic SQL `database-schema.md` because this project uses file + MLflow persistence rather than an RDBMS)* | Living |
| [api-documentation.md](api-documentation.md) | FastAPI REST contract, request/response schemas, status codes, and integration notes | Planned (Phase 11) |
| [setup-guide.md](setup-guide.md) | Local development environment setup (`.venv`, Python 3.13.15, git, dataset verification) | Living |
| [known-issues.md](known-issues.md) | Confirmed dataset quirks, legacy prototype script limitations, and pending improvements | Living |
| `deployment_guide.md` | AWS infrastructure & production deployment instructions | Planned (Phase 14) |
| `retraining_guide.md` | Automated retraining triggers, champion/challenger approval, and rollback instructions | Planned (Phase 16) |

---

## Related Agent Instructions

AI coding agent rules, standards, workflows, and decision logs live in [`agents/`](../agents/AGENTS.md), with the canonical entry point at [`AGENTS.md`](../AGENTS.md) in the repository root.

---

## Documentation Maintenance Rules

1. Update relevant `docs/` and `agents/` files at the end of every phase before committing.
2. Record every significant technical or architectural choice in [technical-decisions.md](technical-decisions.md) and [../agents/decision-log.md](../agents/decision-log.md).
3. Keep [implementation-plan.md](implementation-plan.md) and [implementation-results.md](implementation-results.md) synchronized with actual repository state.
4. Distinguish **Implemented** vs. **Planned** vs. **Pending** explicitly.
5. Link between documents instead of duplicating content.
6. Never include secrets, tokens, passwords, or private credentials.
