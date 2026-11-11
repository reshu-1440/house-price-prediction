# API Documentation

> **Status**: `Implemented (Phase 11)` — FastAPI REST inference service (`src/api/app.py`).

---

## Endpoints

| Method | Path | Purpose | Status Codes |
|--------|------|---------|--------------|
| `GET` | `/health` | Service liveness, loaded model status, model name & version | `200` |
| `GET` | `/model/info` | Active model metadata, feature count, known city count, evaluation metrics | `200`, `503` |
| `POST` | `/predict` | Single property price prediction from validated attributes | `200`, `422`, `503` |
| `POST` | `/predict/batch` | Bounded batch predictions (`1..500` items per request) | `200`, `422`, `503` |

---

## Request Schema (`POST /predict`)

Defined in [`src/api/schemas.py`](../src/api/schemas.py) (`HousePredictionRequest`):

| Field | Type | Constraints / Default |
|-------|------|-----------------------|
| `location` | `str` | Required, `1..100` chars (normalized lowercase) |
| `area_sqft` | `float` | Required, `> 0` and `<= 100,000` |
| `area_type` | `"carpet" \| "super"` | Default `"carpet"` |
| `bhk` | `int` | Required, `1..20` |
| `bathroom` | `int` | Required, `1..20` |
| `balcony` | `int` | Default `0`, `0..20` |
| `floor_number` | `int` | Default `1`, `-2..150`, must be `<= total_floors` |
| `total_floors` | `int` | Default `4`, `1..150` |
| `transaction` | `"Resale" \| "New Property"` | Default `"Resale"` |
| `status` | `"Ready to Move" \| "Missing"` | Default `"Ready to Move"` |
| `furnishing` | `"Unfurnished" \| "Semi-Furnished" \| "Furnished" \| "Missing"` | Default `"Unfurnished"` |
| `ownership` | `"Freehold" \| "Leasehold" \| "Co-operative Society" \| "Power Of Attorney" \| "Missing"` | Default `"Freehold"` |
| `facing` | `str` | Default `"Missing"` |
| `parking_count` | `int` | Default `1`, `0..50` |
| `parking_type` | `"Covered" \| "Open" \| "Other" \| "Missing"` | Default `"Covered"` |
| `society` | `str` | Default `"Missing"` |
| `overlooking` | `str` | Default `"Missing"` |

---

## Example Usage (PowerShell / HTTP)

```powershell
# Start local server
.\.venv\Scripts\python.exe -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

Sample `POST /predict` request & verified response:

```json
{
  "location": "bangalore",
  "area_sqft": 1500.0,
  "bhk": 3,
  "bathroom": 3,
  "balcony": 2,
  "transaction": "New Property",
  "furnishing": "Semi-Furnished"
}
```

```json
{
  "predicted_price_inr": 13407373.42,
  "predicted_price_lakhs": 134.07,
  "formatted_price": "₹1.34 Cr",
  "model_name": "lightgbm",
  "model_version": "0.1.0"
}
```
