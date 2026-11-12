import type { HealthResponse, ModelInfoResponse } from "../types/api";
import { formatCityLabel, formatInrCurrency } from "../utils/validation";

interface ModelInsightsProps {
  health: HealthResponse | null;
  modelInfo: ModelInfoResponse | null;
  cities: string[];
  error: string | null;
}

export function ModelInsights({ health, modelInfo, cities, error }: ModelInsightsProps) {
  const metrics = modelInfo?.metrics ?? {};

  return (
    <div className="insights-layout">
      <section className="card">
        <div className="card-header">
          <div>
            <h2>Model Summary</h2>
            <p className="muted-text">Live metadata and held-out test metrics from the active model.</p>
          </div>
          <span className={`status-pill ${health?.status === "healthy" ? "pill-ok" : "pill-warn"}`}>
            {health?.status ?? "offline"}
          </span>
        </div>

        {error ? (
          <p className="field-error">{error}</p>
        ) : !modelInfo ? (
          <p className="muted-text">Model metadata unavailable while API is offline.</p>
        ) : (
          <div className="metrics-grid">
            <div className="metric-tile">
              <span>Model</span>
              <strong>
                {modelInfo.model_name} v{modelInfo.model_version}
              </strong>
            </div>
            <div className="metric-tile">
              <span>R² Score</span>
              <strong>{metrics.r2 !== undefined ? metrics.r2.toFixed(4) : "—"}</strong>
            </div>
            <div className="metric-tile">
              <span>Mean Absolute Error</span>
              <strong>{metrics.mae !== undefined ? formatInrCurrency(metrics.mae) : "—"}</strong>
            </div>
            <div className="metric-tile">
              <span>Median Error</span>
              <strong>
                {metrics.median_ae !== undefined ? formatInrCurrency(metrics.median_ae) : "—"}
              </strong>
            </div>
            <div className="metric-tile">
              <span>Within ±20%</span>
              <strong>
                {metrics.within_20pct !== undefined ? `${metrics.within_20pct.toFixed(1)}%` : "—"}
              </strong>
            </div>
            <div className="metric-tile">
              <span>Features / Cities</span>
              <strong>
                {modelInfo.feature_count ?? "—"} / {modelInfo.known_locations_count ?? cities.length}
              </strong>
            </div>
          </div>
        )}
      </section>

      <section className="card">
        <div className="card-header">
          <div>
            <h3>Covered Indian Cities ({cities.length})</h3>
            <p className="muted-text">Cities included in the trained model.</p>
          </div>
        </div>
        <div className="city-tag-cloud">
          {cities.map((slug) => (
            <span key={slug} className="city-tag">
              {formatCityLabel(slug)}
            </span>
          ))}
        </div>
      </section>
    </div>
  );
}
