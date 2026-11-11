# AGENTS.md — AI Coding Agent Entry Point

> **Read this file before starting any implementation, debugging, refactoring, or documentation task in this repository.**

## 1. Project Identity

- **Project**: House Price Prediction (End-to-End ML Engineering Workflow)
- **Repository Root**: `d:\Room_Project\house_price_prediction`
- **Dataset**: Kaggle `juhibhojani/house-price` stored at `Data/house_prices.csv` (187,531 rows, 21 columns, 81 Indian cities)
- **Primary Target**: `Price_in_rupees` (numeric value parsed from `Amount(in rupees)`)
- **Python Environment**: `.venv` (Python 3.13.15 on Windows)

---

## 2. Mandatory Pre-Task Checklist

Every AI coding agent working on this repository MUST:

1. Read this root `AGENTS.md`.
2. Read [agents/agent.md](agents/agent.md) and the relevant guides inside `agents/` for the task at hand (see index in [agents/AGENTS.md](agents/AGENTS.md)).
3. Read [docs/README.md](docs/README.md), [docs/implementation-plan.md](docs/implementation-plan.md), [docs/implementation-results.md](docs/implementation-results.md), and [docs/technical-decisions.md](docs/technical-decisions.md) to know the current phase and confirmed decisions.
4. Inspect existing files before modifying or adding modules; never duplicate logic or invent unverified symbol names/metrics.

---

## 3. Non-Negotiable Engineering Rules

1. **Follow the Phased Roadmap Strictly**: Build one phase at a time in order (Phase 0 through Phase 16). Do not skip phases or mix future-phase stubs into the current phase unless explicitly scheduled.
2. **Verify Before Commit**: Every phase must pass all verification checks (imports, scripts, tests, linters, schema/consistency checks) before running `git commit`.
3. **Commit Per Phase**: After verification passes for a phase, sync documentation (`docs/` and `agents/`) and commit with a clear phase-scoped commit message.
4. **Raw Data Immutability**: Never modify or overwrite `Data/house_prices.csv`. All transformations produce derived outputs or in-memory DataFrames.
5. **Zero Target Leakage**:
   - `Price (in rupees)` in the raw CSV is a derived price-per-sqft column (`17,665` nulls) and MUST NEVER be used as an input feature to predict `Price_in_rupees`.
   - `Index` hides `119,339` duplicate listings across the 187,531 rows; deduplication (excluding `Index`) MUST occur before train/test splitting and evaluation.
   - Fit encoders, scalers, imputers, and outlier bounds on training data only.
6. **Fact vs. Plan Honesty**: Never document planned features, assumed test results, or unexecuted benchmarks as implemented facts. Clearly label status as `Implemented`, `In Progress`, or `Planned`.
7. **No Secrets**: Never store Kaggle tokens, AWS credentials, API keys, passwords, or `.env` secrets in code, configs, or documentation.
8. **Keep Knowledge Synced**: Whenever you complete a phase, change architecture, or discover a dataset/code quirk, update the corresponding files in `docs/` and `agents/` before committing.

---

## 4. Quick Navigation

| Need | Location |
|------|----------|
| Project documentation index | [docs/README.md](docs/README.md) |
| Current implementation status & roadmap | [docs/implementation-plan.md](docs/implementation-plan.md) |
| Completed work & verified outcomes | [docs/implementation-results.md](docs/implementation-results.md) |
| Architecture (implemented vs. planned) | [docs/architecture.md](docs/architecture.md) |
| Technical decisions & rationale | [docs/technical-decisions.md](docs/technical-decisions.md) |
| Dataset & storage schemas | [docs/data-schema.md](docs/data-schema.md) |
| AI agent guides index | [agents/AGENTS.md](agents/AGENTS.md) |
| Coding standards & workflow | [agents/coding-standards.md](agents/coding-standards.md), [agents/development-workflow.md](agents/development-workflow.md) |
