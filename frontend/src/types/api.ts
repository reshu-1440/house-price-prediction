export type AreaType = "carpet" | "super";
export type TransactionType = "Resale" | "New Property";
export type StatusType = "Ready to Move" | "Missing";
export type FurnishingType =
  | "Unfurnished"
  | "Semi-Furnished"
  | "Furnished"
  | "Missing";
export type OwnershipType =
  | "Freehold"
  | "Leasehold"
  | "Co-operative Society"
  | "Power Of Attorney"
  | "Missing";
export type ParkingType = "Covered" | "Open" | "Other" | "Missing";

export interface HousePredictionRequest {
  location: string;
  area_sqft: number;
  area_type: AreaType;
  bhk: number;
  bathroom: number;
  balcony: number;
  floor_number: number;
  total_floors: number;
  transaction: TransactionType;
  status: StatusType;
  furnishing: FurnishingType;
  ownership: OwnershipType;
  facing: string;
  parking_count: number;
  parking_type: ParkingType;
  society: string;
  overlooking: string;
}

export interface HousePredictionResponse {
  predicted_price_inr: number;
  predicted_price_lakhs: number;
  formatted_price: string;
  model_name: string;
  model_version: string;
}

export interface BatchPredictionRequest {
  items: HousePredictionRequest[];
}

export interface BatchPredictionResponse {
  count: number;
  predictions: HousePredictionResponse[];
}

export interface HealthResponse {
  status: "healthy" | "degraded";
  model_loaded: boolean;
  model_name: string | null;
  model_version: string | null;
}

export interface ModelInfoResponse {
  model_name: string;
  model_version: string;
  trained_at_utc: string | null;
  feature_count: number | null;
  known_locations_count: number | null;
  metrics: Record<string, number>;
}

export interface LocationsResponse {
  count: number;
  locations: string[];
}

export interface PredictionWithTiming<T> {
  data: T;
  processTimeMs: number | null;
}

export interface SavedPrediction {
  id: string;
  createdAt: string;
  request: HousePredictionRequest;
  response: HousePredictionResponse;
  processTimeMs: number | null;
}
