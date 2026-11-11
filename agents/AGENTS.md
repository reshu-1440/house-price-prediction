# `agents/` Directory Index

> **Canonical Entry Point**: Always start with the root [`AGENTS.md`](../AGENTS.md), then consult the specific guides below as needed for your task.

---

## Guide Map

### Core Instructions
| File | When to Read |
|------|--------------|
| [AGENTS.md](../AGENTS.md) | Mandatory first read before every task |
| [agent.md](agent.md) | Agent responsibilities, operating workflow, verification discipline, and reporting |
| [architecture.md](architecture.md) | Module layout, allowed imports, data/training/inference pipeline design |
| [implementation-plan.md](implementation-plan.md) | Phase-by-phase build checklist, dependencies, and verification gates |

### Development Guidelines
| File | When to Read |
|------|--------------|
| [coding-standards.md](coding-standards.md) | Writing or reviewing Python modules, configs, and scripts |
| [development-workflow.md](development-workflow.md) | Executing a phase end-to-end from inspection through `git commit` |
| [testing-guidelines.md](testing-guidelines.md) | Writing unit, integration, or model quality tests (`pytest`) |
| [debugging-guidelines.md](debugging-guidelines.md) | Investigating data parsing, pipeline, API, or environment errors |
| [security-guidelines.md](security-guidelines.md) | Handling credentials, model artifacts, API inputs, Docker, and AWS configs |

### Project Context & Domain Rules
| File | When to Read |
|------|--------------|
| [project-context.md](project-context.md) | Understanding business goals and Indian property domain logic |
| [technology-stack.md](technology-stack.md) | Checking verified installed libraries vs. planned stack per phase |
| [data-guidelines.md](data-guidelines.md) | Data immutability, deduplication, leakage prevention, and storage rules *(replaces SQL `database-guidelines.md`)* |
| [api-guidelines.md](api-guidelines.md) | Designing or changing FastAPI endpoints and Pydantic schemas (Phase 11+) |

### Workflow & Maintenance
| File | When to Read |
|------|--------------|
| [task-management.md](task-management.md) | Breaking down phases, tracking completion, and formatting status reports |
| [documentation-guidelines.md](documentation-guidelines.md) | Updating `docs/` and `agents/` without drift or duplication |
| [decision-log.md](decision-log.md) | Reviewing or appending architectural/engineering decisions |
| [troubleshooting.md](troubleshooting.md) | Solving Windows `.venv`, dataset encoding, matplotlib, or package quirks |
