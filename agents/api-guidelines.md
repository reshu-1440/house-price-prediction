# API Design Guidelines (Phase 11+)

> Governs FastAPI implementation in `src/api/`. All endpoints are currently **Planned** for Phase 11 (`docs/api-documentation.md`).

---

## 1. Endpoints & Responsibilities
- `GET /health` -> Returns service status, loaded model status, and version (`200 OK`, or degraded status if model missing).
- `POST /predict` -> Accepts one `HousePredictionRequest`, returns `HousePredictionResponse` (`predicted_price_inr`, formatted `Lac`/`Cr` display helper, model version).
- `POST /predict/batch` -> Accepts a bounded list of `HousePredictionRequest` items, returns `BatchPredictionResponse`.
- `GET /model/info` -> Returns active model metadata, trained feature list, and evaluation metrics.

## 2. Schema & Validation Rules (Pydantic v2)
- Use explicit `Field(..., gt=0, description=...)` constraints on numeric inputs (`area_sqft`, `bhk`, `bathroom`).
- Reject unknown/malformed payloads with standard FastAPI `422 Unprocessable Entity` JSON responses.
- Keep API request fields aligned with raw user-knowable property attributes (never require pre-encoded features or `Price (in rupees)`).

## 3. Middleware & Lifecycle
- Load the serialized pipeline once during FastAPI `lifespan` startup in `src/api/dependencies.py` (never reload from disk per request).
- Include request latency logging and structured error handlers in `src/api/middleware.py`.
- Return `503 Service Unavailable` cleanly if inference is requested while no model artifact is loaded.
