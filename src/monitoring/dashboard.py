"""Self-contained HTML monitoring dashboard generator."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from src.utils.config import get_logger

logger = get_logger(__name__)


def generate_monitoring_dashboard(
    drift_report: dict[str, Any],
    prediction_report: dict[str, Any],
    performance_alert: dict[str, Any],
    output_path: Path,
) -> Path:
    """Render a standalone HTML monitoring summary dashboard."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    drift_status = "DRIFT DETECTED" if drift_report.get("overall_drift_detected") else "STABLE"
    pred_status = (
        "DRIFT DETECTED"
        if prediction_report.get("prediction_drift_detected")
        else "STABLE"
    )
    perf_status = "ALERT TRIGGERED" if performance_alert.get("alert_triggered") else "HEALTHY"

    feature_rows = "\n".join(
        f"<tr><td>{html.escape(str(r['feature']))}</td>"
        f"<td>{html.escape(str(r['kind']))}</td>"
        f"<td>{r['statistic']:.4f}</td>"
        f"<td>{r['p_value']:.6f}</td>"
        f"<td>{r['psi']:.4f}</td>"
        f"<td>{'Yes' if r['drifted'] else 'No'}</td></tr>"
        for r in drift_report.get("feature_results", [])
    )

    reasons_html = (
        "<ul>"
        + "".join(f"<li>{html.escape(r)}</li>" for r in performance_alert.get("reasons", []))
        + "</ul>"
        if performance_alert.get("reasons")
        else "<p>All metrics within thresholds.</p>"
    )

    eval_m = performance_alert.get("evaluated_metrics", {})
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>House Price Prediction — Monitoring Dashboard</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 2rem; background: #f7fafc; color: #1a202c; }}
    .cards {{ display: flex; gap: 1rem; margin-bottom: 1.5rem; }}
    .card {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1rem 1.25rem; flex: 1; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; }}
    th, td {{ padding: 0.6rem; border: 1px solid #e2e8f0; text-align: left; }}
    th {{ background: #edf2f7; }}
  </style>
</head>
<body>
  <h1>House Price Prediction — Production Monitoring Dashboard</h1>
  <div class="cards">
    <div class="card">
      <h3>Data Drift</h3>
      <p><strong>{drift_status}</strong> ({drift_report.get('drifted_feature_count', 0)} / {drift_report.get('total_features_checked', 0)} drifted)</p>
    </div>
    <div class="card">
      <h3>Prediction Drift</h3>
      <p><strong>{pred_status}</strong> (PSI={prediction_report.get('psi', 0):.4f}, Shift={prediction_report.get('mean_shift_pct', 0):.2f}%)</p>
    </div>
    <div class="card">
      <h3>Model Performance</h3>
      <p><strong>{perf_status}</strong> (R²={eval_m.get('r2', 0):.4f}, MAE=₹{eval_m.get('mae', 0):,.0f})</p>
      {reasons_html}
    </div>
  </div>
  <h2>Feature Drift Details</h2>
  <table>
    <thead><tr><th>Feature</th><th>Kind</th><th>Statistic</th><th>p-value</th><th>PSI</th><th>Drifted</th></tr></thead>
    <tbody>{feature_rows}</tbody>
  </table>
</body>
</html>
"""
    output_path.write_text(html_content, encoding="utf-8")
    logger.info("Generated monitoring dashboard at %s", output_path)
    return output_path
