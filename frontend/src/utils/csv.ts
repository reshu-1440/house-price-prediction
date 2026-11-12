import {
  BATCH_MAX_ITEMS,
  DEFAULT_PREDICTION_REQUEST,
} from "../constants/modelOptions";
import type {
  AreaType,
  FurnishingType,
  HousePredictionRequest,
  HousePredictionResponse,
  OwnershipType,
  ParkingType,
  StatusType,
  TransactionType,
} from "../types/api";
import { sanitizePredictionRequest, validatePredictionRequest } from "./validation";

export const BATCH_CSV_HEADERS: (keyof HousePredictionRequest)[] = [
  "location",
  "area_sqft",
  "area_type",
  "bhk",
  "bathroom",
  "balcony",
  "floor_number",
  "total_floors",
  "transaction",
  "status",
  "furnishing",
  "ownership",
  "facing",
  "parking_count",
  "parking_type",
  "society",
  "overlooking",
];

const VALID_AREA_TYPES = new Set<AreaType>(["carpet", "super"]);
const VALID_TRANSACTIONS = new Set<TransactionType>(["Resale", "New Property"]);
const VALID_STATUSES = new Set<StatusType>(["Ready to Move", "Missing"]);
const VALID_FURNISHING = new Set<FurnishingType>([
  "Unfurnished",
  "Semi-Furnished",
  "Furnished",
  "Missing",
]);
const VALID_OWNERSHIP = new Set<OwnershipType>([
  "Freehold",
  "Leasehold",
  "Co-operative Society",
  "Power Of Attorney",
  "Missing",
]);
const VALID_PARKING = new Set<ParkingType>(["Covered", "Open", "Other", "Missing"]);

function parseCsvLine(line: string): string[] {
  const cells: string[] = [];
  let current = "";
  let inQuotes = false;

  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"';
        i += 1;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (ch === "," && !inQuotes) {
      cells.push(current.trim());
      current = "";
    } else {
      current += ch;
    }
  }
  cells.push(current.trim());
  return cells;
}

function escapeCsvCell(value: string | number): string {
  const str = String(value);
  if (str.includes(",") || str.includes('"') || str.includes("\n")) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

export interface ParsedBatchCsvResult {
  items: HousePredictionRequest[];
  errors: string[];
}

export function parseBatchCsv(csvText: string): ParsedBatchCsvResult {
  const lines = csvText
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l.length > 0);

  if (lines.length < 2) {
    return {
      items: [],
      errors: ["CSV must contain a header row and at least one data row."],
    };
  }

  const headers = parseCsvLine(lines[0]).map((h) => h.trim());
  const requiredHeaders = ["location", "area_sqft", "bhk", "bathroom"];
  const missingRequired = requiredHeaders.filter((req) => !headers.includes(req));
  if (missingRequired.length > 0) {
    return {
      items: [],
      errors: [`Missing required CSV column(s): ${missingRequired.join(", ")}`],
    };
  }

  const dataLines = lines.slice(1);
  if (dataLines.length > BATCH_MAX_ITEMS) {
    return {
      items: [],
      errors: [
        `CSV has ${dataLines.length} rows, exceeding the API limit of ${BATCH_MAX_ITEMS} items per batch.`,
      ],
    };
  }

  const items: HousePredictionRequest[] = [];
  const errors: string[] = [];

  dataLines.forEach((line, idx) => {
    const rowNum = idx + 2;
    const values = parseCsvLine(line);
    const rowMap: Record<string, string> = {};
    headers.forEach((h, colIdx) => {
      rowMap[h] = values[colIdx] ?? "";
    });

    const areaTypeRaw = (rowMap.area_type || DEFAULT_PREDICTION_REQUEST.area_type).toLowerCase() as AreaType;
    const txRaw = (rowMap.transaction || DEFAULT_PREDICTION_REQUEST.transaction) as TransactionType;
    const statusRaw = (rowMap.status || DEFAULT_PREDICTION_REQUEST.status) as StatusType;
    const furnRaw = (rowMap.furnishing || DEFAULT_PREDICTION_REQUEST.furnishing) as FurnishingType;
    const ownRaw = (rowMap.ownership || DEFAULT_PREDICTION_REQUEST.ownership) as OwnershipType;
    const parkRaw = (rowMap.parking_type || DEFAULT_PREDICTION_REQUEST.parking_type) as ParkingType;

    if (!VALID_AREA_TYPES.has(areaTypeRaw)) {
      errors.push(`Row ${rowNum}: invalid area_type '${rowMap.area_type}' (use 'carpet' or 'super').`);
      return;
    }
    if (!VALID_TRANSACTIONS.has(txRaw)) {
      errors.push(`Row ${rowNum}: invalid transaction '${rowMap.transaction}' (use 'Resale' or 'New Property').`);
      return;
    }
    if (!VALID_STATUSES.has(statusRaw)) {
      errors.push(`Row ${rowNum}: invalid status '${rowMap.status}'.`);
      return;
    }
    if (!VALID_FURNISHING.has(furnRaw)) {
      errors.push(`Row ${rowNum}: invalid furnishing '${rowMap.furnishing}'.`);
      return;
    }
    if (!VALID_OWNERSHIP.has(ownRaw)) {
      errors.push(`Row ${rowNum}: invalid ownership '${rowMap.ownership}'.`);
      return;
    }
    if (!VALID_PARKING.has(parkRaw)) {
      errors.push(`Row ${rowNum}: invalid parking_type '${rowMap.parking_type}'.`);
      return;
    }

    const candidate = sanitizePredictionRequest({
      location: rowMap.location ?? "",
      area_sqft: Number(rowMap.area_sqft),
      area_type: areaTypeRaw,
      bhk: Number(rowMap.bhk),
      bathroom: Number(rowMap.bathroom),
      balcony: rowMap.balcony !== undefined && rowMap.balcony !== "" ? Number(rowMap.balcony) : DEFAULT_PREDICTION_REQUEST.balcony,
      floor_number:
        rowMap.floor_number !== undefined && rowMap.floor_number !== ""
          ? Number(rowMap.floor_number)
          : DEFAULT_PREDICTION_REQUEST.floor_number,
      total_floors:
        rowMap.total_floors !== undefined && rowMap.total_floors !== ""
          ? Number(rowMap.total_floors)
          : DEFAULT_PREDICTION_REQUEST.total_floors,
      transaction: txRaw,
      status: statusRaw,
      furnishing: furnRaw,
      ownership: ownRaw,
      facing: rowMap.facing || DEFAULT_PREDICTION_REQUEST.facing,
      parking_count:
        rowMap.parking_count !== undefined && rowMap.parking_count !== ""
          ? Number(rowMap.parking_count)
          : DEFAULT_PREDICTION_REQUEST.parking_count,
      parking_type: parkRaw,
      society: rowMap.society || DEFAULT_PREDICTION_REQUEST.society,
      overlooking: rowMap.overlooking || DEFAULT_PREDICTION_REQUEST.overlooking,
    });

    const rowErrors = validatePredictionRequest(candidate);
    const messages = Object.values(rowErrors).filter(Boolean);
    if (messages.length > 0) {
      errors.push(`Row ${rowNum}: ${messages.join(" ")}`);
      return;
    }
    items.push(candidate);
  });

  return { items, errors };
}

export function buildSampleBatchCsv(): string {
  const sampleRows: HousePredictionRequest[] = [
    {
      ...DEFAULT_PREDICTION_REQUEST,
      location: "bangalore",
      area_sqft: 1500,
      bhk: 3,
      bathroom: 3,
    },
    {
      ...DEFAULT_PREDICTION_REQUEST,
      location: "new-delhi",
      area_sqft: 1100,
      bhk: 2,
      bathroom: 2,
      balcony: 1,
      floor_number: 2,
      total_floors: 4,
      transaction: "Resale",
      furnishing: "Unfurnished",
    },
    {
      ...DEFAULT_PREDICTION_REQUEST,
      location: "pune",
      area_sqft: 1250,
      area_type: "super",
      bhk: 2,
      bathroom: 2,
      balcony: 2,
      floor_number: 6,
      total_floors: 12,
      transaction: "New Property",
      furnishing: "Semi-Furnished",
    },
  ];

  const lines = [
    BATCH_CSV_HEADERS.join(","),
    ...sampleRows.map((row) =>
      BATCH_CSV_HEADERS.map((key) => escapeCsvCell(row[key])).join(","),
    ),
  ];
  return lines.join("\n");
}

export function buildBatchResultsCsv(
  items: HousePredictionRequest[],
  predictions: HousePredictionResponse[],
): string {
  const headers = [
    ...BATCH_CSV_HEADERS,
    "predicted_price_inr",
    "predicted_price_lakhs",
    "formatted_price",
    "estimated_price_per_sqft",
    "model_name",
    "model_version",
  ];

  const rows = items.map((item, idx) => {
    const pred = predictions[idx];
    const perSqft = pred ? Math.round(pred.predicted_price_inr / item.area_sqft) : 0;
    return [
      ...BATCH_CSV_HEADERS.map((key) => escapeCsvCell(item[key])),
      pred ? pred.predicted_price_inr : "",
      pred ? pred.predicted_price_lakhs : "",
      pred ? escapeCsvCell(pred.formatted_price) : "",
      pred ? perSqft : "",
      pred ? escapeCsvCell(pred.model_name) : "",
      pred ? escapeCsvCell(pred.model_version) : "",
    ].join(",");
  });

  return [headers.join(","), ...rows].join("\n");
}
