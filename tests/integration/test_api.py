"""Integration tests for FastAPI prediction endpoints and middleware."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import model_state

pytestmark = pytest.mark.integration


def test_health_and_model_info(api_client: TestClient) -> None:
    health = api_client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"
    assert health.json()["model_loaded"] is True

    health_head = api_client.head("/health")
    assert health_head.status_code == 200

    info = api_client.get("/model/info")
    assert info.status_code == 200
    payload = info.json()
    assert payload["model_name"] == "lightgbm"
    assert "r2" in payload["metrics"]

    locs = api_client.get("/locations")
    assert locs.status_code == 200
    locs_payload = locs.json()
    assert locs_payload["count"] == len(locs_payload["locations"])
    assert "bangalore" in locs_payload["locations"]


def test_predict_and_batch_endpoints(api_client: TestClient) -> None:
    single = api_client.post(
        "/predict",
        json={
            "location": "bangalore",
            "area_sqft": 1500.0,
            "bhk": 3,
            "bathroom": 3,
            "balcony": 2,
            "floor_number": 5,
            "total_floors": 12,
            "transaction": "New Property",
            "furnishing": "Semi-Furnished",
        },
    )
    assert single.status_code == 200
    body = single.json()
    assert body["predicted_price_inr"] > 0
    assert body["predicted_price_lakhs"] == pytest.approx(body["predicted_price_inr"] / 1e5, rel=1e-2)
    assert "X-Process-Time-Ms" in single.headers

    batch = api_client.post(
        "/predict/batch",
        json={
            "items": [
                {"location": "new-delhi", "area_sqft": 1200.0, "bhk": 2, "bathroom": 2},
                {"location": "mumbai", "area_sqft": 1800.0, "bhk": 3, "bathroom": 3},
                {"location": "unseen-city", "area_sqft": 1000.0, "bhk": 2, "bathroom": 2},
            ]
        },
    )
    assert batch.status_code == 200
    batch_body = batch.json()
    assert batch_body["count"] == 3
    assert all(item["predicted_price_inr"] > 0 for item in batch_body["predictions"])


def test_predict_validation_and_503_when_unloaded(api_client: TestClient) -> None:
    bad_area = api_client.post(
        "/predict",
        json={"location": "pune", "area_sqft": -100, "bhk": 2, "bathroom": 2},
    )
    assert bad_area.status_code == 422

    bad_floor = api_client.post(
        "/predict",
        json={
            "location": "pune",
            "area_sqft": 1000,
            "bhk": 2,
            "bathroom": 2,
            "floor_number": 10,
            "total_floors": 5,
        },
    )
    assert bad_floor.status_code == 422

    model_state.clear()
    health_degraded = api_client.get("/health")
    assert health_degraded.status_code == 200
    assert health_degraded.json()["status"] == "degraded"

    unavail = api_client.post(
        "/predict",
        json={"location": "pune", "area_sqft": 1000, "bhk": 2, "bathroom": 2},
    )
    assert unavail.status_code == 503
