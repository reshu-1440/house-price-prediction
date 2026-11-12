import { useState } from "react";
import { AlertCircle, Download, FileSpreadsheet, Play, Plus, Trash2, Upload } from "lucide-react";
import {
  BATCH_MAX_ITEMS,
  DEFAULT_PREDICTION_REQUEST,
} from "../constants/modelOptions";
import { ApiError, predictBatch } from "../services/apiClient";
import type { HousePredictionRequest, HousePredictionResponse } from "../types/api";
import {
  buildBatchResultsCsv,
  buildSampleBatchCsv,
  parseBatchCsv,
} from "../utils/csv";
import {
  formatCityLabel,
  formatCompactInr,
  formatInrCurrency,
  sanitizePredictionRequest,
  validatePredictionRequest,
} from "../utils/validation";

interface BatchPredictorProps {
  cities: string[];
  modelLoaded: boolean;
  onPredictionSuccess?: (modelName: string, modelVersion: string) => void;
  onBackendReachable?: () => void;
}

function downloadTextFile(filename: string, content: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export function BatchPredictor({
  cities,
  modelLoaded,
  onPredictionSuccess,
  onBackendReachable,
}: BatchPredictorProps) {
  const [items, setItems] = useState<HousePredictionRequest[]>([
    { ...DEFAULT_PREDICTION_REQUEST },
    {
      ...DEFAULT_PREDICTION_REQUEST,
      location: "new-delhi",
      area_sqft: 1100,
      bhk: 2,
      bathroom: 2,
      transaction: "Resale",
      furnishing: "Unfurnished",
    },
  ]);
  const [predictions, setPredictions] = useState<HousePredictionResponse[] | null>(null);
  const [parseErrors, setParseErrors] = useState<string[]>([]);
  const [apiError, setApiError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const text = String(reader.result ?? "");
      const parsed = parseBatchCsv(text);
      setParseErrors(parsed.errors);
      setPredictions(null);
      setApiError(null);
      if (parsed.items.length > 0 && parsed.errors.length === 0) {
        setItems(parsed.items);
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  }

  function handleAddRow() {
    if (items.length >= BATCH_MAX_ITEMS) return;
    setItems((prev) => [...prev, { ...DEFAULT_PREDICTION_REQUEST }]);
    setPredictions(null);
  }

  function handleRemoveRow(idx: number) {
    setItems((prev) => prev.filter((_, i) => i !== idx));
    setPredictions(null);
  }

  function updateRow<K extends keyof HousePredictionRequest>(
    idx: number,
    key: K,
    value: HousePredictionRequest[K],
  ) {
    setItems((prev) => prev.map((row, i) => (i === idx ? { ...row, [key]: value } : row)));
    setPredictions(null);
  }

  async function handleRunBatch() {
    setApiError(null);
    setParseErrors([]);

    if (items.length === 0) {
      setApiError("Add at least 1 property row before predicting.");
      return;
    }

    const rowErrors: string[] = [];
    const sanitized = items.map((row, idx) => {
      const clean = sanitizePredictionRequest(row);
      const errs = validatePredictionRequest(clean);
      const messages = Object.values(errs).filter(Boolean);
      if (messages.length > 0) {
        rowErrors.push(`Row ${idx + 1}: ${messages.join(" ")}`);
      }
      return clean;
    });

    if (rowErrors.length > 0) {
      setParseErrors(rowErrors);
      return;
    }

    setLoading(true);
    try {
      const res = await predictBatch({ items: sanitized });
      setPredictions(res.data.predictions);
      if (res.data.predictions.length > 0) {
        const first = res.data.predictions[0];
        onPredictionSuccess?.(first.model_name, first.model_version);
      }
      onBackendReachable?.();
    } catch (err) {
      if (err instanceof ApiError) {
        setApiError(err.message);
      } else {
        setApiError("Unable to complete batch prediction.");
      }
    } finally {
      setLoading(false);
    }
  }

  const summary =
    predictions && predictions.length > 0
      ? (() => {
          const vals = predictions.map((p) => p.predicted_price_inr).sort((a, b) => a - b);
          const mid = Math.floor(vals.length / 2);
          const median = vals.length % 2 === 0 ? (vals[mid - 1] + vals[mid]) / 2 : vals[mid];
          return { min: vals[0], max: vals[vals.length - 1], median };
        })()
      : null;

  return (
    <section className="card">
      <div className="card-header batch-header">
        <div>
          <h2>Batch CSV Prediction</h2>
          <p className="muted-text">
            Edit rows below or upload a CSV (up to {BATCH_MAX_ITEMS} properties).
          </p>
        </div>

        <div className="batch-actions">
          <button
            type="button"
            className="ghost-btn"
            onClick={() =>
              downloadTextFile("house_price_batch_template.csv", buildSampleBatchCsv(), "text/csv")
            }
          >
            <Download size={14} />
            Sample CSV
          </button>
          <label className="ghost-btn">
            <Upload size={14} />
            Upload CSV
            <input type="file" accept=".csv,text/csv" hidden onChange={handleFileUpload} />
          </label>
          <button
            type="button"
            className="ghost-btn"
            onClick={handleAddRow}
            disabled={items.length >= BATCH_MAX_ITEMS}
          >
            <Plus size={14} />
            Add Row
          </button>
          <button
            type="button"
            className="primary-btn"
            onClick={handleRunBatch}
            disabled={loading || !modelLoaded}
          >
            <Play size={14} />
            {loading ? "Predicting..." : `Predict (${items.length})`}
          </button>
        </div>
      </div>

      {parseErrors.length > 0 && (
        <div className="alert-banner alert-error">
          <AlertCircle size={18} />
          <div>
            <strong>Please fix these row errors:</strong>
            <ul className="error-list">
              {parseErrors.slice(0, 6).map((msg, idx) => (
                <li key={idx}>{msg}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {apiError && (
        <div className="alert-banner alert-error">
          <AlertCircle size={18} />
          <span>{apiError}</span>
        </div>
      )}

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>#</th>
              <th>City</th>
              <th>Area (sqft)</th>
              <th>Type</th>
              <th>BHK</th>
              <th>Bath</th>
              <th>Transaction</th>
              <th>Estimate</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((row, idx) => {
              const pred = predictions?.[idx];
              return (
                <tr key={idx}>
                  <td>{idx + 1}</td>
                  <td>
                    <select
                      className="table-input"
                      value={cities.includes(row.location) ? row.location : ""}
                      onChange={(e) => updateRow(idx, "location", e.target.value)}
                    >
                      {!cities.includes(row.location) && (
                        <option value={row.location}>{row.location}</option>
                      )}
                      {cities.map((c) => (
                        <option key={c} value={c}>
                          {formatCityLabel(c)}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <input
                      type="number"
                      className="table-input num-input"
                      min={1}
                      max={100000}
                      value={row.area_sqft}
                      onChange={(e) => updateRow(idx, "area_sqft", Number(e.target.value))}
                    />
                  </td>
                  <td>
                    <select
                      className="table-input"
                      value={row.area_type}
                      onChange={(e) =>
                        updateRow(idx, "area_type", e.target.value as "carpet" | "super")
                      }
                    >
                      <option value="carpet">Carpet</option>
                      <option value="super">Super</option>
                    </select>
                  </td>
                  <td>
                    <input
                      type="number"
                      className="table-input small-num"
                      min={1}
                      max={20}
                      value={row.bhk}
                      onChange={(e) => updateRow(idx, "bhk", Number(e.target.value))}
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      className="table-input small-num"
                      min={1}
                      max={20}
                      value={row.bathroom}
                      onChange={(e) => updateRow(idx, "bathroom", Number(e.target.value))}
                    />
                  </td>
                  <td>
                    <select
                      className="table-input"
                      value={row.transaction}
                      onChange={(e) =>
                        updateRow(
                          idx,
                          "transaction",
                          e.target.value as "Resale" | "New Property",
                        )
                      }
                    >
                      <option value="Resale">Resale</option>
                      <option value="New Property">New Property</option>
                    </select>
                  </td>
                  <td>
                    {pred ? (
                      <div className="batch-pred-cell">
                        <strong>{pred.formatted_price}</strong>
                        <span className="muted-text small-text">
                          {formatInrCurrency(Math.round(pred.predicted_price_inr / row.area_sqft))}
                          /sqft
                        </span>
                      </div>
                    ) : (
                      <span className="muted-text">—</span>
                    )}
                  </td>
                  <td>
                    <button
                      type="button"
                      className="icon-danger-btn"
                      aria-label={`Remove row ${idx + 1}`}
                      onClick={() => handleRemoveRow(idx)}
                      disabled={items.length <= 1}
                    >
                      <Trash2 size={15} />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {summary && predictions && (
        <div className="batch-summary-footer">
          <div className="batch-kpis">
            <div className="kpi-box">
              <span className="kpi-label">Properties</span>
              <strong>{predictions.length}</strong>
            </div>
            <div className="kpi-box">
              <span className="kpi-label">Median Price</span>
              <strong>{formatCompactInr(summary.median)}</strong>
            </div>
            <div className="kpi-box">
              <span className="kpi-label">Range</span>
              <strong>
                {formatCompactInr(summary.min)} – {formatCompactInr(summary.max)}
              </strong>
            </div>
          </div>

          <button
            type="button"
            className="ghost-btn"
            onClick={() =>
              downloadTextFile(
                "house_price_predictions.csv",
                buildBatchResultsCsv(items, predictions),
                "text/csv",
              )
            }
          >
            <FileSpreadsheet size={15} />
            Export Results CSV
          </button>
        </div>
      )}
    </section>
  );
}
