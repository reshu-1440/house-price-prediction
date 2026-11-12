import { useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  Building2,
  Calculator,
  ChevronDown,
  ChevronUp,
  Pin,
  RotateCcw,
  Trash2,
} from "lucide-react";
import {
  AREA_TYPE_OPTIONS,
  DEFAULT_PREDICTION_REQUEST,
  FACING_OPTIONS,
  FURNISHING_OPTIONS,
  OWNERSHIP_OPTIONS,
  PARKING_TYPE_OPTIONS,
  PROPERTY_PRESETS,
  STATUS_OPTIONS,
  TRANSACTION_OPTIONS,
} from "../constants/modelOptions";
import { ApiError, predictSingle } from "../services/apiClient";
import type {
  AreaType,
  FurnishingType,
  HousePredictionRequest,
  HousePredictionResponse,
  OwnershipType,
  ParkingType,
  SavedPrediction,
  StatusType,
  TransactionType,
} from "../types/api";
import {
  formatCityLabel,
  formatInrCurrency,
  sanitizePredictionRequest,
  validatePredictionRequest,
} from "../utils/validation";
import { CitySelector } from "./CitySelector";

interface SinglePredictorProps {
  cities: string[];
  modelLoaded: boolean;
  onBackendReachable?: () => void;
}

export function SinglePredictor({
  cities,
  modelLoaded,
  onBackendReachable,
}: SinglePredictorProps) {
  const [form, setForm] = useState<HousePredictionRequest>({ ...DEFAULT_PREDICTION_REQUEST });
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [submittedOnce, setSubmittedOnce] = useState(false);
  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [result, setResult] = useState<{
    request: HousePredictionRequest;
    response: HousePredictionResponse;
    processTimeMs: number | null;
  } | null>(null);
  const [history, setHistory] = useState<SavedPrediction[]>([]);
  const formTopRef = useRef<HTMLElement | null>(null);

  const errors = useMemo(() => validatePredictionRequest(form), [form]);
  const hasErrors = Object.keys(errors).length > 0;

  function updateField<K extends keyof HousePredictionRequest>(
    key: K,
    value: HousePredictionRequest[K],
  ) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmittedOnce(true);
    setApiError(null);

    if (hasErrors) {
      formTopRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }

    const sanitized = sanitizePredictionRequest(form);
    setLoading(true);
    try {
      const { data, processTimeMs } = await predictSingle(sanitized);
      setResult({
        request: sanitized,
        response: data,
        processTimeMs,
      });
      onBackendReachable?.();
    } catch (err) {
      if (err instanceof ApiError) {
        setApiError(err.message);
      } else {
        setApiError("Unable to get prediction right now. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  function handlePinResult() {
    if (!result) return;
    const entry: SavedPrediction = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      createdAt: new Date().toLocaleTimeString(),
      request: result.request,
      response: result.response,
      processTimeMs: result.processTimeMs,
    };
    setHistory((prev) => [entry, ...prev].slice(0, 6));
  }

  const impliedPerSqft =
    result && result.request.area_sqft > 0
      ? Math.round(result.response.predicted_price_inr / result.request.area_sqft)
      : null;

  return (
    <div className="predictor-layout">
      <section className="card form-card" ref={formTopRef}>
        <div className="card-header">
          <div>
            <h2>Property Details</h2>
            <p className="muted-text">
              Enter property size, city, and layout to estimate market sale price.
            </p>
          </div>
          <button
            type="button"
            className="ghost-btn"
            onClick={() => {
              setForm({ ...DEFAULT_PREDICTION_REQUEST });
              setSubmittedOnce(false);
              setApiError(null);
            }}
          >
            <RotateCcw size={14} />
            Reset
          </button>
        </div>

        <div className="presets-row">
          <span className="presets-label">Examples:</span>
          {PROPERTY_PRESETS.map((preset) => (
            <button
              key={preset.name}
              type="button"
              className="preset-pill"
              onClick={() => {
                setForm({ ...preset.payload });
                setSubmittedOnce(false);
                setApiError(null);
              }}
            >
              {preset.name}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} noValidate>
          <div className="grid-2">
            <CitySelector
              value={form.location}
              cities={cities}
              error={submittedOnce ? errors.location : undefined}
              onChange={(val) => updateField("location", val)}
            />

            <div className="field-group">
              <label htmlFor="area-sqft" className="field-label">
                Area (sq.ft) <span className="required-star">*</span>
              </label>
              <input
                id="area-sqft"
                type="number"
                step="any"
                min={1}
                max={100000}
                className={`text-input ${submittedOnce && errors.area_sqft ? "input-error" : ""}`}
                value={Number.isNaN(form.area_sqft) ? "" : form.area_sqft}
                onChange={(e) =>
                  updateField("area_sqft", e.target.value === "" ? NaN : Number(e.target.value))
                }
              />
              {submittedOnce && errors.area_sqft && (
                <p className="field-error">{errors.area_sqft}</p>
              )}
            </div>
          </div>

          <div className="grid-2">
            <div className="field-group">
              <span className="field-label">Area Type</span>
              <div className="segmented-control">
                {AREA_TYPE_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    className={`segment-btn ${form.area_type === opt.value ? "active" : ""}`}
                    onClick={() => updateField("area_type", opt.value as AreaType)}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="field-group">
              <span className="field-label">Transaction Type</span>
              <div className="segmented-control">
                {TRANSACTION_OPTIONS.map((opt) => (
                  <button
                    key={opt}
                    type="button"
                    className={`segment-btn ${form.transaction === opt ? "active" : ""}`}
                    onClick={() => updateField("transaction", opt as TransactionType)}
                  >
                    {opt}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="grid-3">
            <div className="field-group">
              <label htmlFor="bhk-input" className="field-label">
                BHK <span className="required-star">*</span>
              </label>
              <input
                id="bhk-input"
                type="number"
                min={1}
                max={20}
                step={1}
                className={`text-input ${submittedOnce && errors.bhk ? "input-error" : ""}`}
                value={Number.isNaN(form.bhk) ? "" : form.bhk}
                onChange={(e) =>
                  updateField("bhk", e.target.value === "" ? NaN : Number(e.target.value))
                }
              />
              {submittedOnce && errors.bhk && <p className="field-error">{errors.bhk}</p>}
            </div>

            <div className="field-group">
              <label htmlFor="bathroom-input" className="field-label">
                Bathrooms <span className="required-star">*</span>
              </label>
              <input
                id="bathroom-input"
                type="number"
                min={1}
                max={20}
                step={1}
                className={`text-input ${submittedOnce && errors.bathroom ? "input-error" : ""}`}
                value={Number.isNaN(form.bathroom) ? "" : form.bathroom}
                onChange={(e) =>
                  updateField("bathroom", e.target.value === "" ? NaN : Number(e.target.value))
                }
              />
              {submittedOnce && errors.bathroom && (
                <p className="field-error">{errors.bathroom}</p>
              )}
            </div>

            <div className="field-group">
              <label htmlFor="furnishing-select" className="field-label">
                Furnishing
              </label>
              <select
                id="furnishing-select"
                className="select-input"
                value={form.furnishing}
                onChange={(e) => updateField("furnishing", e.target.value as FurnishingType)}
              >
                {FURNISHING_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid-2">
            <div className="field-group">
              <label htmlFor="floor-number-input" className="field-label">
                Floor Number
              </label>
              <input
                id="floor-number-input"
                type="number"
                min={-2}
                max={150}
                step={1}
                className={`text-input ${errors.floor_number ? "input-error" : ""}`}
                value={Number.isNaN(form.floor_number) ? "" : form.floor_number}
                onChange={(e) =>
                  updateField(
                    "floor_number",
                    e.target.value === "" ? NaN : Number(e.target.value),
                  )
                }
              />
              {errors.floor_number ? (
                <p className="field-error">{errors.floor_number}</p>
              ) : (
                <p className="field-hint">0 = Ground, -1 = Basement, -2 = Lower Basement</p>
              )}
            </div>

            <div className="field-group">
              <label htmlFor="total-floors-input" className="field-label">
                Total Floors
              </label>
              <input
                id="total-floors-input"
                type="number"
                min={1}
                max={150}
                step={1}
                className={`text-input ${submittedOnce && errors.total_floors ? "input-error" : ""}`}
                value={Number.isNaN(form.total_floors) ? "" : form.total_floors}
                onChange={(e) =>
                  updateField(
                    "total_floors",
                    e.target.value === "" ? NaN : Number(e.target.value),
                  )
                }
              />
              {submittedOnce && errors.total_floors && (
                <p className="field-error">{errors.total_floors}</p>
              )}
            </div>
          </div>

          <div className="advanced-toggle-wrap">
            <button
              type="button"
              className="advanced-toggle-btn"
              onClick={() => setShowAdvanced((prev) => !prev)}
            >
              {showAdvanced ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              {showAdvanced ? "Hide Optional Details" : "More Details (Optional: Balcony, Parking, Facing, Ownership)"}
            </button>
          </div>

          {showAdvanced && (
            <div className="advanced-panel">
              <div className="grid-3">
                <div className="field-group">
                  <label htmlFor="balcony-input" className="field-label">
                    Balconies
                  </label>
                  <input
                    id="balcony-input"
                    type="number"
                    min={0}
                    max={20}
                    step={1}
                    className={`text-input ${submittedOnce && errors.balcony ? "input-error" : ""}`}
                    value={Number.isNaN(form.balcony) ? "" : form.balcony}
                    onChange={(e) =>
                      updateField("balcony", e.target.value === "" ? NaN : Number(e.target.value))
                    }
                  />
                  {submittedOnce && errors.balcony && (
                    <p className="field-error">{errors.balcony}</p>
                  )}
                </div>

                <div className="field-group">
                  <label htmlFor="parking-count-input" className="field-label">
                    Parking Spaces
                  </label>
                  <input
                    id="parking-count-input"
                    type="number"
                    min={0}
                    max={50}
                    step={1}
                    className={`text-input ${submittedOnce && errors.parking_count ? "input-error" : ""}`}
                    value={Number.isNaN(form.parking_count) ? "" : form.parking_count}
                    onChange={(e) =>
                      updateField(
                        "parking_count",
                        e.target.value === "" ? NaN : Number(e.target.value),
                      )
                    }
                  />
                  {submittedOnce && errors.parking_count && (
                    <p className="field-error">{errors.parking_count}</p>
                  )}
                </div>

                <div className="field-group">
                  <label htmlFor="parking-type-select" className="field-label">
                    Parking Type
                  </label>
                  <select
                    id="parking-type-select"
                    className="select-input"
                    value={form.parking_type}
                    onChange={(e) => updateField("parking_type", e.target.value as ParkingType)}
                  >
                    {PARKING_TYPE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid-3">
                <div className="field-group">
                  <label htmlFor="ownership-select" className="field-label">
                    Ownership
                  </label>
                  <select
                    id="ownership-select"
                    className="select-input"
                    value={form.ownership}
                    onChange={(e) => updateField("ownership", e.target.value as OwnershipType)}
                  >
                    {OWNERSHIP_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="field-group">
                  <label htmlFor="facing-select" className="field-label">
                    Facing
                  </label>
                  <select
                    id="facing-select"
                    className="select-input"
                    value={form.facing}
                    onChange={(e) => updateField("facing", e.target.value)}
                  >
                    {FACING_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="field-group">
                  <label htmlFor="status-select" className="field-label">
                    Possession Status
                  </label>
                  <select
                    id="status-select"
                    className="select-input"
                    value={form.status}
                    onChange={(e) => updateField("status", e.target.value as StatusType)}
                  >
                    {STATUS_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid-2">
                <div className="field-group">
                  <label htmlFor="society-input" className="field-label">
                    Society Name
                  </label>
                  <input
                    id="society-input"
                    type="text"
                    maxLength={120}
                    className="text-input"
                    value={form.society}
                    placeholder="Missing or society name"
                    onChange={(e) => updateField("society", e.target.value)}
                  />
                  <p className="field-hint">Used as a society-present indicator by the model.</p>
                </div>

                <div className="field-group">
                  <label htmlFor="overlooking-input" className="field-label">
                    Overlooking View
                  </label>
                  <input
                    id="overlooking-input"
                    type="text"
                    maxLength={120}
                    className="text-input"
                    value={form.overlooking}
                    placeholder="Missing or e.g. Garden/Park"
                    onChange={(e) => updateField("overlooking", e.target.value)}
                  />
                  <p className="field-hint">Used as an overlooking-view indicator by the model.</p>
                </div>
              </div>
            </div>
          )}

          {submittedOnce && hasErrors && (
            <div className="alert-banner alert-error" role="alert">
              <AlertCircle size={18} />
              <span>Please fix the highlighted fields above before predicting.</span>
            </div>
          )}

          {apiError && (
            <div className="alert-banner alert-error" role="alert">
              <AlertCircle size={18} />
              <span>{apiError}</span>
            </div>
          )}

          {!modelLoaded && (
            <div className="alert-banner alert-warn" role="status">
              <AlertCircle size={18} />
              <span>
                Backend status is offline or waking up. Click Refresh once the server is ready.
              </span>
            </div>
          )}

          <div className="submit-row">
            <button type="submit" className="primary-btn" disabled={loading}>
              <Calculator size={18} />
              {loading ? "Predicting..." : "Predict House Price"}
            </button>
          </div>
        </form>
      </section>

      <aside className="results-column">
        <section className="card result-card">
          <div className="card-header">
            <h2>Estimated Price</h2>
            {result && (
              <button type="button" className="ghost-btn" onClick={handlePinResult}>
                <Pin size={14} />
                Save
              </button>
            )}
          </div>

          {!result ? (
            <div className="empty-state">
              <Building2 size={32} className="empty-icon" />
              <p>
                Enter property details and click <strong>Predict House Price</strong>.
              </p>
            </div>
          ) : (
            <div className="valuation-body">
              <div className="price-hero">
                <span className="price-eyebrow">Estimated Market Value</span>
                <div className="price-main">{result.response.formatted_price}</div>
                <div className="price-sub">
                  {formatInrCurrency(result.response.predicted_price_inr)} (
                  {result.response.predicted_price_lakhs.toLocaleString("en-IN")} Lakhs)
                </div>
              </div>

              <div className="kpi-grid">
                <div className="kpi-box">
                  <span className="kpi-label">Price per sq.ft</span>
                  <strong className="kpi-value">
                    {impliedPerSqft !== null ? `${formatInrCurrency(impliedPerSqft)}/sqft` : "—"}
                  </strong>
                </div>
                <div className="kpi-box">
                  <span className="kpi-label">Model</span>
                  <strong className="kpi-value">
                    {result.response.model_name} v{result.response.model_version}
                  </strong>
                  {result.processTimeMs !== null && (
                    <span className="kpi-note">{result.processTimeMs.toFixed(1)} ms</span>
                  )}
                </div>
              </div>

              <div className="summary-strip">
                <span>
                  <strong>{formatCityLabel(result.request.location)}</strong> · {result.request.bhk}{" "}
                  BHK · {result.request.area_sqft} sqft ({result.request.area_type})
                </span>
                <span>
                  Floor {result.request.floor_number}/{result.request.total_floors} ·{" "}
                  {result.request.transaction} · {result.request.furnishing}
                </span>
              </div>
            </div>
          )}
        </section>

        {history.length > 0 && (
          <section className="card">
            <div className="card-header">
              <h3>Saved Comparisons ({history.length})</h3>
              <button type="button" className="link-btn" onClick={() => setHistory([])}>
                <Trash2 size={13} /> Clear
              </button>
            </div>

            <div className="history-list">
              {history.map((item) => {
                const rate = Math.round(
                  item.response.predicted_price_inr / item.request.area_sqft,
                );
                return (
                  <div key={item.id} className="history-item">
                    <div>
                      <strong>
                        {formatCityLabel(item.request.location)} · {item.request.bhk} BHK (
                        {item.request.area_sqft} sqft)
                      </strong>
                      <div className="muted-text small-text">
                        {item.request.transaction} · {item.request.furnishing}
                      </div>
                    </div>
                    <div className="history-price">
                      <strong>{item.response.formatted_price}</strong>
                      <span className="muted-text small-text">
                        {formatInrCurrency(rate)}/sqft
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}
      </aside>
    </div>
  );
}
