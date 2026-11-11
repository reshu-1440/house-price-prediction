"""Unit tests for Phase 11 Pydantic API schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

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
