import type {
  BatchPredictionRequest,
  BatchPredictionResponse,
  HealthResponse,
  HousePredictionRequest,
  HousePredictionResponse,
  LocationsResponse,
  ModelInfoResponse,
  PredictionWithTiming,
} from "../types/api";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/+$/, "") || "/api";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function parseErrorDetail(body: unknown, fallbackStatus: number): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          if (item && typeof item === "object" && "msg" in item) {
            const loc = Array.isArray((item as { loc?: unknown }).loc)
              ? (item as { loc: unknown[] }).loc.slice(1).join(".")
              : "";
            return loc ? `${loc}: ${String((item as { msg: unknown }).msg)}` : String((item as { msg: unknown }).msg);
          }
          return JSON.stringify(item);
        })
        .join(" | ");
    }
  }
  return `Request failed with HTTP ${fallbackStatus}`;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<PredictionWithTiming<T>> {
  const url = `${API_BASE_URL}${path}`;
  let response: Response;
  try {
    response = await fetch(url, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
    });
  } catch {
    const hint =
      API_BASE_URL === "/api"
        ? "Unable to reach FastAPI server. Make sure the backend is running (start.bat) on port 8000."
        : `Unable to reach API server (${API_BASE_URL}). It may be waking up — wait a few seconds and click Refresh.`;
    throw new ApiError(0, hint);
  }

  const rawTiming = response.headers.get("X-Process-Time-Ms");
  const processTimeMs = rawTiming !== null && !Number.isNaN(Number(rawTiming)) ? Number(rawTiming) : null;

  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    throw new ApiError(response.status, parseErrorDetail(payload, response.status));
  }

  return {
    data: payload as T,
    processTimeMs,
  };
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await requestJson<HealthResponse>("/health", { method: "GET" });
  return res.data;
}

export async function fetchModelInfo(): Promise<ModelInfoResponse> {
  const res = await requestJson<ModelInfoResponse>("/model/info", { method: "GET" });
  return res.data;
}

export async function fetchLocations(): Promise<LocationsResponse> {
  const res = await requestJson<LocationsResponse>("/locations", { method: "GET" });
  return res.data;
}

export async function predictSingle(
  payload: HousePredictionRequest,
): Promise<PredictionWithTiming<HousePredictionResponse>> {
  return requestJson<HousePredictionResponse>("/predict", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function predictBatch(
  payload: BatchPredictionRequest,
): Promise<PredictionWithTiming<BatchPredictionResponse>> {
  return requestJson<BatchPredictionResponse>("/predict/batch", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getConfiguredApiBaseLabel(): string {
  return API_BASE_URL === "/api" ? "Vite Proxy (/api -> http://127.0.0.1:8000)" : API_BASE_URL;
}
