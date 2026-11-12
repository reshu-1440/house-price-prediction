"""FastAPI application entrypoint for house price prediction serving."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import Depends, FastAPI

from src.api.dependencies import ModelRegistryState, get_model_state, model_state
from src.api.middleware import configure_middleware
from src.api.schemas import (
    BatchPredictionRequest,
    BatchPredictionResponse,
    HealthResponse,
    HousePredictionRequest,
    HousePredictionResponse,
    LocationsResponse,
    ModelInfoResponse,
    format_inr_price,
)
from src.pipeline.inference_pipeline import predict_from_raw
from src.utils.config import load_config, resolve_path


def load_production_settings(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load production API settings from ``config/production.yaml`` with env overrides."""
    target = Path(config_path) if config_path is not None else resolve_path("config/production.yaml")
    settings: dict[str, Any] = load_config(target) if target.exists() else {}

    env_origins = os.getenv("ALLOWED_ORIGINS")
    if env_origins:
        settings.setdefault("cors", {})["allowed_origins"] = [
            o.strip() for o in env_origins.split(",") if o.strip()
        ]
    return settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Load serialized ML pipeline once on startup and release cleanly on shutdown."""
    if model_state.pipeline is None:
        model_state.load()
    yield


def create_app(allowed_origins: list[str] | None = None) -> FastAPI:
    """Create and configure the FastAPI application instance."""
    application = FastAPI(
        title="House Price Prediction API",
        version="0.1.0",
        description="End-to-end ML inference service for Indian residential real estate prices (INR).",
        lifespan=lifespan,
    )
    configure_middleware(application, allowed_origins=allowed_origins)

    @application.get("/health", response_model=HealthResponse, tags=["System"])
    def health_check() -> HealthResponse:
        loaded = model_state.pipeline is not None
        return HealthResponse(
            status="healthy" if loaded else "degraded",
            model_loaded=loaded,
            model_name=model_state.metadata.get("model_name"),
            model_version=model_state.metadata.get("model_version"),
        )

    @application.get("/model/info", response_model=ModelInfoResponse, tags=["Model"])
    def model_info(state: ModelRegistryState = Depends(get_model_state)) -> ModelInfoResponse:
        meta = state.metadata
        return ModelInfoResponse(
            model_name=str(meta.get("model_name", "lightgbm")),
            model_version=str(meta.get("model_version", "0.1.0")),
            trained_at_utc=meta.get("trained_at_utc"),
            feature_count=meta.get("feature_count"),
            known_locations_count=meta.get("known_locations_count"),
            metrics={str(k): float(v) for k, v in meta.get("metrics", {}).items()},
        )

    @application.get("/locations", response_model=LocationsResponse, tags=["Model"])
    def list_locations(state: ModelRegistryState = Depends(get_model_state)) -> LocationsResponse:
        locations: list[str] = []
        named_steps = getattr(state.pipeline, "named_steps", {})
        preprocessor = named_steps.get("preprocessor")
        if preprocessor is not None and hasattr(preprocessor, "named_steps"):
            loc_encoder = preprocessor.named_steps.get("location_encoder")
            target_map = getattr(loc_encoder, "target_map_", None)
            if isinstance(target_map, dict):
                locations = sorted(str(city) for city in target_map.keys())
        return LocationsResponse(count=len(locations), locations=locations)

    @application.post("/predict", response_model=HousePredictionResponse, tags=["Prediction"])
    def predict_price(
        payload: HousePredictionRequest,
        state: ModelRegistryState = Depends(get_model_state),
    ) -> HousePredictionResponse:
        preds = predict_from_raw(state.pipeline, payload.to_raw_dict())
        inr = float(preds[0])
        return HousePredictionResponse(
            predicted_price_inr=round(inr, 2),
            predicted_price_lakhs=round(inr / 1e5, 2),
            formatted_price=format_inr_price(inr),
            model_name=str(state.metadata.get("model_name", "lightgbm")),
            model_version=str(state.metadata.get("model_version", "0.1.0")),
        )

    @application.post("/predict/batch", response_model=BatchPredictionResponse, tags=["Prediction"])
    def predict_price_batch(
        payload: BatchPredictionRequest,
        state: ModelRegistryState = Depends(get_model_state),
    ) -> BatchPredictionResponse:
        raw_rows = [item.to_raw_dict() for item in payload.items]
        preds = predict_from_raw(state.pipeline, raw_rows)
        model_name = str(state.metadata.get("model_name", "lightgbm"))
        model_version = str(state.metadata.get("model_version", "0.1.0"))

        responses = [
            HousePredictionResponse(
                predicted_price_inr=round(float(val), 2),
                predicted_price_lakhs=round(float(val) / 1e5, 2),
                formatted_price=format_inr_price(float(val)),
                model_name=model_name,
                model_version=model_version,
            )
            for val in preds
        ]
        return BatchPredictionResponse(count=len(responses), predictions=responses)

    return application


def _default_allowed_origins() -> list[str] | None:
    if os.getenv("APP_ENV", "").strip().lower() == "production":
        settings = load_production_settings()
        return settings.get("cors", {}).get("allowed_origins")
    return None


def run_production_server(config_path: str | Path | None = None) -> None:
    """Start uvicorn using production server settings from ``config/production.yaml``."""
    settings = load_production_settings(config_path)
    srv = settings.get("server", {})
    uvicorn.run(
        "src.api.app:app",
        host=str(srv.get("host", "0.0.0.0")),
        port=int(srv.get("port", 8000)),
        workers=int(srv.get("workers", 2)),
        log_level=str(srv.get("log_level", "info")),
        timeout_keep_alive=int(srv.get("timeout_keep_alive", 30)),
    )


app = create_app(allowed_origins=_default_allowed_origins())


if __name__ == "__main__":
    run_production_server()
