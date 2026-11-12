import { describe, expect, it } from "vitest";
import {
  DEFAULT_PREDICTION_REQUEST,
  FALLBACK_TRAINED_CITIES,
} from "../constants/modelOptions";
import {
  buildBatchResultsCsv,
  buildSampleBatchCsv,
  parseBatchCsv,
} from "./csv";
import {
  formatCompactInr,
  sanitizePredictionRequest,
  validatePredictionRequest,
} from "./validation";

describe("HousePredictionRequest client validation", () => {
  it("accepts valid default request and normalizes location", () => {
    const sanitized = sanitizePredictionRequest({
      ...DEFAULT_PREDICTION_REQUEST,
      location: "  Bangalore  ",
    });
    expect(sanitized.location).toBe("bangalore");
    expect(validatePredictionRequest(sanitized)).toEqual({});
  });

  it("rejects non-positive area and floor_number > total_floors", () => {
    const errors = validatePredictionRequest({
      ...DEFAULT_PREDICTION_REQUEST,
      area_sqft: -50,
      floor_number: 15,
      total_floors: 10,
    });
    expect(errors.area_sqft).toBeDefined();
    expect(errors.floor_number).toBeDefined();
  });

  it("includes all 81 trained Indian cities", () => {
    expect(FALLBACK_TRAINED_CITIES).toHaveLength(81);
    expect(FALLBACK_TRAINED_CITIES).toContain("new-delhi");
    expect(FALLBACK_TRAINED_CITIES).toContain("bangalore");
    expect(FALLBACK_TRAINED_CITIES).toContain("zirakpur");
  });

  it("formats INR values in Lac and Cr matching backend format_inr_price", () => {
    expect(formatCompactInr(14_742_100)).toBe("₹1.47 Cr");
    expect(formatCompactInr(7_800_000)).toBe("₹78.00 Lac");
  });
});

describe("Batch CSV helpers", () => {
  it("parses the generated sample CSV cleanly with zero errors", () => {
    const csv = buildSampleBatchCsv();
    const parsed = parseBatchCsv(csv);
    expect(parsed.errors).toEqual([]);
    expect(parsed.items).toHaveLength(3);
    expect(parsed.items[0].location).toBe("bangalore");
  });

  it("exports batch predictions to CSV", () => {
    const csv = buildSampleBatchCsv();
    const { items } = parseBatchCsv(csv);
    const fakePreds = items.map(() => ({
      predicted_price_inr: 10_000_000,
      predicted_price_lakhs: 100,
      formatted_price: "₹1.00 Cr",
      model_name: "lightgbm",
      model_version: "0.1.0",
    }));
    const exported = buildBatchResultsCsv(items, fakePreds);
    expect(exported).toContain("predicted_price_inr");
    expect(exported).toContain("₹1.00 Cr");
  });
});
