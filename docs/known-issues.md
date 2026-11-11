# Known Issues & Dataset Quirks

> Tracks confirmed data anomalies, prototype limitations, and pending engineering improvements.

---

## 1. Confirmed Dataset Issues (`Data/house_prices.csv`)

| ID | Issue | Impact | Planned Resolution |
|----|-------|--------|--------------------|
| KI-001 | **`Index` masks `119,339` duplicate listings**: Full-row `df.duplicated()` returns `0`, while `df.drop(columns=['Index']).duplicated()` returns `119,339` (~63.6% of 187,531 rows). | Severe train/test leakage and artificially inflated metrics if not deduplicated before splitting. | Phase 3 (`cleaning.py`) removes duplicates excluding `Index`; Phase 5 (`split.py`) asserts zero duplicate overlap. |
| KI-002 | **`Price (in rupees)` is a derived price/sqft column** (`17,665` nulls). | Direct target leakage if included as a model feature. | Phase 3 drops `Price (in rupees)` from features; enforced in Phase 5 & `agents/data-guidelines.md`. |
| KI-003 | **`Amount(in rupees)` contains `9,684` `Call for Price` strings** and mixed `Lac` / `Cr` units. | Cannot train regression directly on string target. | Phase 3 parses `Lac`/`Lakh` (`1e5`) and `Cr`/`Crore` (`1e7`) and drops `Call for Price`. |
| KI-004 | **Area columns (`Carpet Area`, `Super Area`) have commas and mixed units** (`sqft`, `sqyrd`, `sqm`, `marla`, `acre`, `kanal`, `ground`, `cent`, `bigha`, `biswa2`, `aankadam`). | Naive regex or unit-less numeric extraction produces wrong scale by orders of magnitude (e.g., acres vs sqft, or `1,000`). | Phase 3 strips commas and converts all recognized area units to square feet (`sqft`). |
| KI-005 | **`Bathroom` and `Balcony` contain `'> 10'` string values**. | `pd.to_numeric(..., errors='coerce')` turns `'> 10'` into `NaN` unless handled explicitly. | Phase 3 parses `'> 10'` cleanly (e.g., capped numeric `11` or explicit handling). |
| KI-006 | **`Dimensions` and `Plot Area` are 100% null** (187,531 / 187,531). | Zero signal; adds noise if kept. | Phase 3 drops 100%-null columns automatically. |
| KI-007 | **`Transaction` includes `Rent/Lease` and `Other`** alongside `Resale` and `New Property`. | Rental prices follow a completely different scale than sale prices. | Phase 3 filters to sale transactions (`Resale`, `New Property`). |
| KI-008 | **Extreme price outliers (`max = 14,003,000,000 INR`, i.e., 1,400.3 Cr vs. P99 = 7 Cr)** and mutually exclusive areas (`Carpet only = 106,858`, `Super only = 79,846`, `Both = 0`, `Neither = 827`). | Extreme prices distort RMSE/linear models; single-area columns leave ~43–57% nulls individually. | Phase 3 handles outliers and unifies `Carpet Area` + `Super Area` into `effective_area_sqft` + `area_type`. |

---

## 2. Existing Prototype Script Limitations (`Data/`)

- `Data/data_check.py` and `Data/data_cleaning.py` use relative path `"house_prices.csv"`, requiring execution inside `Data/`.
- `Data/data_cleaning.py` restricts analysis to 3 cities (`new-delhi`, `bangalore`, `ahmedabad`) and performs no area parsing, deduplication, or outlier filtering.
- Both scripts are exploratory prototypes and will be superseded by modular code in `src/data/` during Phases 1–3 (kept or archived cleanly without breaking git history).
