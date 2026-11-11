"""Unit tests for Phase 11 Pydantic API schemas and FastAPI endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.api.app import app
from src.api.dependencies import model_state
from src.api.schemas import (
    BatchPredictionRequest,
    HousePredictionRequest,
    format_inr_price,
)


def test_house_prediction_request_validation_and_formatting() -> None:
    req = HousePredictionRequest(
        location="  Bangalore  ",
        area_sqft=1500.0,
        bhk=3,
        bathroom=3,
        balcony=2,
        floor_number=5,
        total_floors=12,
    )
    assert req.location == "bangalore"
    raw = req.to_raw_dict()
    assert raw["Title"] == "3 BHK Property"
    assert raw["effective_area_sqft"] == 1500.0
    assert format_inr_price(14_742_100.0) == "₹1.47 Cr"
    assert format_inr_price(7_800_000.0) == "₹78.00 Lac"

    with pytest.raises(ValidationError):
        HousePredictionRequest(location="pune", area_sqft=-50.0, bhk=2, bathroom=2)

    with pytest.raises(ValidationError):
        HousePredictionRequest(
            location="pune",
            area_sqft=1000.0,
            bhk=2,
            bathroom=2,
            floor_number=15,
            total_floors=10,
        )

    with pytest.raises(ValidationError):
        BatchPredictionRequest(items=[])


def test_api_endpoints_with_loaded_and_unloaded_model() -> None:
    model_state.clear()
    with TestClient(app) as client:
        # Lifespan loads models/house_price_pipeline.joblib automatically
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "healthy"
        assert health.json()["model_loaded"] is True

        info = client.get("/model/info")
        assert info.status_code == 200
        assert info.json()["feature_count"] == 50

        pred_resp = client.post(
            "/predict",
            json={
                "location": "bangalore",
                "area_sqft": 1500.0,
                "bhk": 3,
                "bathroom": 3,
                "balcony": 2,
                "transaction": "New Property",
            },
        )
        assert pred_resp.status_code == 200
        body = pred_resp.json()
        assert body["predicted_price_inr"] > 0
        assert "X-Process-Time-Ms" in pred_resp.headers

        batch_resp = client.post(
            "/predict/batch",
            json={
                "items": [
                    {"location": "new-delhi", "area_sqft": 1200.0, "bhk": 2, "bathroom": 2},
                    {"location": "mumbai", "area_sqft": 1600.0, "bhk": 3, "bathroom": 3},
                ]
            },
        )
        assert batch_resp.status_code == 200
        assert batch_resp.json()["count"] == 2

        invalid_resp = client.post(
            "/predict",
            json={"location": "pune", "area_sqft": -10, "bhk": 0, "bathroom": 1},
        )
        assert invalid_resp.status_code == 422

        model_state.clear()
        unavail_resp = client.post(
            "/predict",
            json={"location": "pune", "area_sqft": 1000, "bhk": 2, "bathroom": 2},
        )
        assert unavail_resp.status_code == 503
