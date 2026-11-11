# Project Context & Domain Rules

## 1. Business Problem
Build an end-to-end, production-ready machine learning system that accurately estimates residential property sale prices (`Price_in_rupees`) across **81 Indian cities** from property listing attributes (location, area, BHK configuration, floor level, transaction type, furnishing, ownership, parking, bathrooms, balconies).

## 2. Indian Real Estate Domain Rules (Verified on `Data/house_prices.csv`)
- **Currency Units (`Amount(in rupees)`)**:
  - `1 Lac` / `1 Lakh` = `100,000` INR (`1e5`)
  - `1 Cr` / `1 Crore` = `10,000,000` INR (`1e7`)
  - `Call for Price` (`9,684` rows) represents an undisclosed price and MUST be excluded from training/evaluation targets.
- **Sale vs. Non-Sale Listings (`Transaction`)**:
  - Keep `Resale` and `New Property` only. Exclude `Rent/Lease`, `Other`, and missing transaction types because rental rates use a fundamentally different monetary scale.
- **Area Measurements (`Carpet Area` & `Super Area`)**:
  - Both contain numeric values + units (`sqft`, `sqyrd`, `sqm`, `marla`, `acre`, `kanal`, `ground`, `cent`, `bigha`, etc.) and comma-formatted numbers (e.g., `1,000 sqft`).
  - `Carpet Area` (~43% null) and `Super Area` (~57% null) complement each other; resolve into a unified `sqft` representation (`carpet_area_sqft`, `super_area_sqft`, `effective_area_sqft`).
- **Configuration & Floors**:
  - `Title` typically starts with `<N> BHK` (e.g., `3 BHK`, `2 BHK`, `4 BHK`).
  - `Floor` uses `<level> out of <total>` where `<level>` may be `'Ground'`, `'Lower Basement'`, `'Upper Basement'`, or integer.
- **Categorical Counts**:
  - `Bathroom` and `Balcony` contain `'> 10'` string entries alongside `'1'`..`'10'`.

For verified column counts and null profiles, see [`docs/data-schema.md`](../docs/data-schema.md) and [`docs/known-issues.md`](../docs/known-issues.md).
