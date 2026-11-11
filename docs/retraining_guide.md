# Automated Model Retraining & Versioning Guide

This guide documents the automated retraining workflow implemented in `src/retraining/` and configured via [`config/retraining.yaml`](../config/retraining.yaml).

---

## 1. Retraining Triggers (`check_retraining_trigger`)

Retraining is triggered automatically when any configured condition holds:
1. **Data Drift (`retrain_on_data_drift`)**: `detect_data_drift()` flags covariate shift exceeding `max_drifted_feature_share`.
2. **Performance Degradation (`retrain_on_performance_alert`)**: `alert_on_degradation()` flags `R²`, `MAE`, `MAPE`, or baseline `R²` drop breaching thresholds.
3. **Model Staleness (`max_model_age_days`)**: Days elapsed since `trained_at_utc` in `models/metadata.json` exceeds `30` days.

---

## 2. Champion vs. Challenger Approval Gate (`approve_model`)

Every candidate model trained by `retrain_model()` must satisfy both absolute quality floors and non-regression rules against the active champion before replacing production:
- `candidate_r2 >= 0.75`
- `candidate_mae <= ₹2,800,000`
- `candidate_r2 - champion_r2 >= -0.005`
- `candidate_mae` regression `<= 2.0%`

If rejected, the existing production artifact remains untouched.

---

## 3. Semantic Versioning & Safe Rollback (`versioning.py`)

- Approved models are archived as immutable snapshots under `models/versions/vX.Y.Z/` (`pipeline.joblib` + `metadata.json`) and indexed in `models/versions/registry.json`.
- Production replacement uses atomic `os.replace()` swaps so concurrent API readers never observe partial files.
- To roll back to a previous version:

```python
from pathlib import Path
from src.retraining.versioning import rollback_model

rollback_model(
    target_version="0.1.0",
    versions_dir=Path("models/versions"),
    production_path=Path("models/house_price_pipeline.joblib"),
)
```

---

## 4. Scheduled Execution

```powershell
# Evaluate triggers without running training
.\.venv\Scripts\python.exe -m src.retraining.scheduler --dry-run

# Force retraining and champion/challenger promotion
.\.venv\Scripts\python.exe -m src.retraining.scheduler --force
```
