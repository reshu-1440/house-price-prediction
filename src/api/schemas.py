"""Pydantic v2 request and response schemas for the prediction API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


def format_inr_price(amount_inr: float) -> str:
    """Format INR numeric value into human-readable Crore or Lakh notation."""
    if amount_inr >= 1e7:
        return f"₹{amount_inr / 1e7:.2f} Cr"
    return f"₹{amount_inr / 1e5:.2f} Lac"


class HousePredictionRequest(BaseModel):
    """Validated property attributes required for a single price prediction."""

    location: str = Field(..., min_length=1, max_length=100, examples=["bangalore"])
    area_sqft: float = Field(..., gt=0, le=100_000, examples=[1500.0])
    area_type: Literal["carpet", "super"] = "carpet"
    bhk: int = Field(..., ge=1, le=20, examples=[3])
    bathroom: int = Field(..., ge=1, le=20, examples=[3])
    balcony: int = Field(default=0, ge=0, le=20, examples=[2])
    floor_number: int = Field(default=1, ge=-2, le=150, examples=[5])
    total_floors: int = Field(default=4, ge=1, le=150, examples=[12])
    transaction: Literal["Resale", "New Property"] = "Resale"
    status: Literal["Ready to Move", "Missing"] = "Ready to Move"
    furnishing: Literal["Unfurnished", "Semi-Furnished", "Furnished", "Missing"] = "Unfurnished"
    ownership: Literal[
        "Freehold",
        "Leasehold",
        "Co-operative Society",
        "Power Of Attorney",
        "Missing",
    ] = "Freehold"
    facing: str = Field(default="Missing", max_length=50)
    parking_count: int = Field(default=1, ge=0, le=50)
    parking_type: Literal["Covered", "Open", "Other", "Missing"] = "Covered"
    society: str = Field(default="Missing", max_length=120)
    overlooking: str = Field(default="Missing", max_length=120)

    @field_validator("location")
    @classmethod
    def normalize_location(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("location must not be blank.")
        return cleaned

    @model_validator(mode="after")
    def check_floor_not_above_total(self) -> HousePredictionRequest:
        if self.floor_number > self.total_floors:
            raise ValueError(
                f"floor_number ({self.floor_number}) cannot exceed total_floors ({self.total_floors})."
            )
        return self

    def to_raw_dict(self) -> dict[str, Any]:
        """Convert validated schema fields into raw inference pipeline keys."""
        parking_str = (
            f"{self.parking_count} {self.parking_type}"
            if self.parking_count > 0 and self.parking_type != "Missing"
            else None
        )
        return {
            "Title": f"{self.bhk} BHK Property",
            "location": self.location,
            "effective_area_sqft": float(self.area_sqft),
            "area_type": self.area_type,
            "Floor": f"{self.floor_number} out of {self.total_floors}",
            "Transaction": self.transaction,
            "Status": self.status,
            "Furnishing": self.furnishing,
            "Ownership": self.ownership,
            "facing": self.facing,
            "overlooking": self.overlooking,
            "Society": self.society,
            "Bathroom": str(self.bathroom),
            "Balcony": str(self.balcony),
            "Car Parking": parking_str,
        }


class HousePredictionResponse(BaseModel):
    """Single house price prediction output payload."""

    predicted_price_inr: float = Field(..., ge=0)
    predicted_price_lakhs: float = Field(..., ge=0)
    formatted_price: str
    model_name: str
    model_version: str


class BatchPredictionRequest(BaseModel):
    """Bounded batch prediction payload."""

    items: list[HousePredictionRequest] = Field(..., min_length=1, max_length=500)


class BatchPredictionResponse(BaseModel):
    """Batch prediction output payload."""

    count: int
    predictions: list[HousePredictionResponse]


class HealthResponse(BaseModel):
    """Service health and model readiness check response."""

    status: Literal["healthy", "degraded"]
    model_loaded: bool
    model_name: str | None = None
    model_version: str | None = None


class ModelInfoResponse(BaseModel):
    """Active model metadata and evaluation metrics."""

    model_name: str
    model_version: str
    trained_at_utc: str | None = None
    feature_count: int | None = None
    known_locations_count: int | None = None
    metrics: dict[str, float] = Field(default_factory=dict)
