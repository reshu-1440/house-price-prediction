"""FastAPI application entrypoint for house price prediction serving."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from src.api.dependencies import ModelRegistryState, get_model_state, model_state
from src.api.middleware import configure_middleware
from src.api.schemas import (
    BatchPredictionRequest,
    BatchPredictionResponse,
    HealthResponse,
    HousePredictionRequest,
    HousePredictionResponse,
    ModelInfoResponse,
    format_inr_price,
)
from src.pipeline.inference_pipeline import predict_from_raw


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


app = create_app()
