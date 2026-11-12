import type { HousePredictionRequest } from "../types/api";

export type ValidationErrors = Partial<Record<keyof HousePredictionRequest, string>>;

export function normalizeLocationSlug(value: string): string {
  return value.trim().toLowerCase();
}

export function formatCityLabel(slug: string): string {
  return slug
    .split("-")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function formatInrCurrency(amountInr: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amountInr);
}

export function formatCompactInr(amountInr: number): string {
  if (amountInr >= 1e7) {
    return `₹${(amountInr / 1e7).toFixed(2)} Cr`;
  }
  return `₹${(amountInr / 1e5).toFixed(2)} Lac`;
}

export function sanitizePredictionRequest(req: HousePredictionRequest): HousePredictionRequest {
  return {
    ...req,
    location: normalizeLocationSlug(req.location),
    facing: req.facing.trim() || "Missing",
    society: req.society.trim() || "Missing",
    overlooking: req.overlooking.trim() || "Missing",
  };
}

/**
 * Mirrors Pydantic v2 constraints in `src/api/schemas.py` (`HousePredictionRequest`).
 */
export function validatePredictionRequest(req: HousePredictionRequest): ValidationErrors {
  const errors: ValidationErrors = {};
  const loc = normalizeLocationSlug(req.location);

  if (!loc) {
    errors.location = "City / location is required.";
  } else if (loc.length > 100) {
    errors.location = "Location must be 100 characters or fewer.";
  }

  if (!Number.isFinite(req.area_sqft) || req.area_sqft <= 0 || req.area_sqft > 100_000) {
    errors.area_sqft = "Area must be greater than 0 and at most 100,000 sq.ft.";
  }

  if (!Number.isInteger(req.bhk) || req.bhk < 1 || req.bhk > 20) {
    errors.bhk = "BHK must be an integer between 1 and 20.";
  }

  if (!Number.isInteger(req.bathroom) || req.bathroom < 1 || req.bathroom > 20) {
    errors.bathroom = "Bathrooms must be an integer between 1 and 20.";
  }

  if (!Number.isInteger(req.balcony) || req.balcony < 0 || req.balcony > 20) {
    errors.balcony = "Balconies must be an integer between 0 and 20.";
  }

  if (!Number.isInteger(req.floor_number) || req.floor_number < -2 || req.floor_number > 150) {
    errors.floor_number = "Floor number must be between -2 (Lower Basement) and 150.";
  }

  if (!Number.isInteger(req.total_floors) || req.total_floors < 1 || req.total_floors > 150) {
    errors.total_floors = "Total floors must be an integer between 1 and 150.";
  }

  if (
    Number.isInteger(req.floor_number) &&
    Number.isInteger(req.total_floors) &&
    req.floor_number > req.total_floors
  ) {
    errors.floor_number = `Floor (${req.floor_number}) cannot exceed total floors (${req.total_floors}).`;
  }

  if (!Number.isInteger(req.parking_count) || req.parking_count < 0 || req.parking_count > 50) {
    errors.parking_count = "Parking count must be an integer between 0 and 50.";
  }

  if (req.facing.trim().length > 50) {
    errors.facing = "Facing must be 50 characters or fewer.";
  }

  if (req.society.trim().length > 120) {
    errors.society = "Society must be 120 characters or fewer.";
  }

  if (req.overlooking.trim().length > 120) {
    errors.overlooking = "Overlooking must be 120 characters or fewer.";
  }

  return errors;
}
