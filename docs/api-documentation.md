# API Documentation

> **Status**: `Planned (Phase 11)` — No FastAPI server or prediction endpoints are implemented yet.
> This document defines the target contract to be implemented and verified in **Phase 11** and expanded with live verified examples once built.

---

## Planned Endpoints (`src/api/app.py`)

| Method | Path | Purpose | Status |
|--------|------|---------|--------|
| `GET` | `/health` | Service liveness & model readiness check | Planned (Phase 11) |
| `POST` | `/predict` | Single property price prediction from raw attributes | Planned (Phase 11) |
| `POST` | `/predict/batch` | Batch property price predictions | Planned (Phase 11) |
| `GET` | `/model/info` | Active model metadata, version, metrics, and expected schema | Planned (Phase 11) |

---

## Planned Validation & Error Behavior

- Request and response payloads will be strictly validated with **Pydantic v2** (`src/api/schemas.py`).
- Invalid payloads (missing required fields, negative area/bathrooms, invalid types) will return HTTP `422 Unprocessable Entity` with structured validation details.
- If the model artifact fails to load or is unavailable, prediction endpoints will return HTTP `503 Service Unavailable`.
- Exact JSON schemas and `curl` examples will be added upon completion of Phase 11.

For API coding conventions, see [`agents/api-guidelines.md`](../agents/api-guidelines.md).
