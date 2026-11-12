import { useCallback, useEffect, useState } from "react";
import { BarChart3, Building2, FileSpreadsheet, RefreshCw } from "lucide-react";
import { BatchPredictor } from "./components/BatchPredictor";
import { ModelInsights } from "./components/ModelInsights";
import { SinglePredictor } from "./components/SinglePredictor";
import { FALLBACK_TRAINED_CITIES } from "./constants/modelOptions";
import {
  ApiError,
  fetchHealth,
  fetchLocations,
  fetchModelInfo,
} from "./services/apiClient";
import type { HealthResponse, ModelInfoResponse } from "./types/api";

type ActiveTab = "single" | "batch" | "insights";

export function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>("single");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [modelInfo, setModelInfo] = useState<ModelInfoResponse | null>(null);
  const [cities, setCities] = useState<string[]>(FALLBACK_TRAINED_CITIES);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const loadStatus = useCallback(async () => {
    setRefreshing(true);
    setStatusError(null);
    try {
      const h = await fetchHealth();
      setHealth(h);

      if (h.model_loaded) {
        const [infoRes, locRes] = await Promise.allSettled([
          fetchModelInfo(),
          fetchLocations(),
        ]);

        if (infoRes.status === "fulfilled") {
          setModelInfo(infoRes.value);
        }
        if (locRes.status === "fulfilled" && locRes.value.locations.length > 0) {
          setCities(locRes.value.locations);
        }
      } else {
        setModelInfo(null);
      }
    } catch (err) {
      setHealth(null);
      setModelInfo(null);
      setStatusError(
        err instanceof ApiError
          ? err.message
          : "Backend API is unreachable right now. Click Refresh in a moment.",
      );
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void loadStatus();
  }, [loadStatus]);

  const handleBackendReachable = useCallback(() => {
    if (health?.status !== "healthy" || !health.model_loaded) {
      void loadStatus();
    }
  }, [health, loadStatus]);

  const modelLoaded = Boolean(health?.model_loaded);

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="header-inner">
          <div className="brand-block">
            <div className="brand-icon">
              <Building2 size={20} />
            </div>
            <div>
              <h1>House Price Estimator</h1>
              <p className="brand-subtitle">Indian Residential Property Valuation</p>
            </div>
          </div>

          <div className="status-controls">
            <span
              className={`status-pill ${
                health?.status === "healthy"
                  ? "pill-ok"
                  : health?.status === "degraded"
                    ? "pill-warn"
                    : "pill-offline"
              }`}
            >
              <span className="dot" />
              {health?.status === "healthy"
                ? `Connected · ${health.model_name ?? "model"} v${health.model_version ?? "?"}`
                : health?.status === "degraded"
                  ? "Model Not Loaded"
                  : "API Offline"}
            </span>

            <button
              type="button"
              className="ghost-btn"
              onClick={() => void loadStatus()}
              disabled={refreshing}
            >
              <RefreshCw size={14} className={refreshing ? "spin" : ""} />
              Refresh
            </button>
          </div>
        </div>

        <nav className="tab-bar" aria-label="Primary views">
          <button
            type="button"
            className={`tab-btn ${activeTab === "single" ? "active" : ""}`}
            onClick={() => setActiveTab("single")}
          >
            <Building2 size={15} />
            Price Estimator
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === "batch" ? "active" : ""}`}
            onClick={() => setActiveTab("batch")}
          >
            <FileSpreadsheet size={15} />
            Batch CSV
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === "insights" ? "active" : ""}`}
            onClick={() => setActiveTab("insights")}
          >
            <BarChart3 size={15} />
            Model Info
          </button>
        </nav>
      </header>

      <main className="main-content">
        {statusError && (
          <div className="alert-banner alert-warn global-banner">
            <span>{statusError}</span>
          </div>
        )}

        {activeTab === "single" && (
          <SinglePredictor
            cities={cities}
            modelLoaded={modelLoaded}
            onBackendReachable={handleBackendReachable}
          />
        )}
        {activeTab === "batch" && (
          <BatchPredictor
            cities={cities}
            modelLoaded={modelLoaded}
            onBackendReachable={handleBackendReachable}
          />
        )}
        {activeTab === "insights" && (
          <ModelInsights
            health={health}
            modelInfo={modelInfo}
            cities={cities}
            error={statusError}
          />
        )}
      </main>
    </div>
  );
}

export default App;
