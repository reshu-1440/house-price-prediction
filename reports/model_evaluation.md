# Model Evaluation Report — `lightgbm_tuned`

- **Held-out Test Samples**: 12,892
- **Feature Count**: 50

## 1. Overall Test Metrics
- **R²**: 0.8128
- **Adjusted R²**: 0.8121
- **MAE**: ₹2,206,793.51
- **Median AE**: ₹1,011,185.35
- **RMSE**: ₹4,827,094.43
- **MAPE**: 22.12%
- **Predictions within ±20%**: 58.38%

## 2. Error Segmentation by Price Tier

| Price Tier | Count | MAE (INR) | RMSE (INR) | MAPE (%) | R² |
|------------|-------|-----------|------------|----------|----|
| 50 Lac - 1 Cr | 4,878 | 1,363,757.82 | 1,930,560.27 | 18.97% | -0.9682 |
| < 50 Lac | 4,628 | 792,124.50 | 1,142,532.13 | 25.03% | -0.2021 |
| 1 Cr - 2.5 Cr | 2,529 | 3,465,856.83 | 4,857,270.88 | 22.25% | -0.4127 |
| > 2.5 Cr | 857 | 10,929,366.52 | 15,894,401.63 | 23.99% | 0.2826 |

## 3. Error Segmentation Across Top 15 Cities

| City | Count | MAE (INR) | RMSE (INR) | MAPE (%) | R² |
|------|-------|-----------|------------|----------|----|
| faridabad | 581 | 1,377,397.01 | 2,149,232.38 | 16.21% | 0.8459 |
| bangalore | 580 | 3,359,175.67 | 7,101,700.54 | 25.01% | 0.6830 |
| chennai | 576 | 3,238,198.80 | 7,533,266.11 | 28.04% | 0.6445 |
| greater-noida | 574 | 1,289,838.13 | 2,506,346.86 | 16.81% | 0.7868 |
| gurgaon | 570 | 5,804,642.39 | 9,351,378.35 | 24.30% | 0.7163 |
| kolkata | 565 | 2,174,913.36 | 4,705,305.24 | 25.60% | 0.8131 |
| ahmedabad | 554 | 2,416,597.14 | 4,772,811.00 | 21.99% | 0.8094 |
| hyderabad | 543 | 2,645,686.76 | 5,052,193.46 | 18.91% | 0.8559 |
| jaipur | 543 | 1,493,042.00 | 2,757,413.64 | 21.16% | 0.7033 |
| new-delhi | 540 | 4,980,247.31 | 9,045,288.92 | 26.75% | 0.8077 |
| vadodara | 470 | 1,024,079.97 | 1,865,325.33 | 20.93% | 0.6885 |
| pune | 434 | 2,218,988.80 | 4,021,081.15 | 22.88% | 0.8297 |
| surat | 431 | 1,563,075.09 | 3,765,269.06 | 17.34% | 0.8256 |
| visakhapatnam | 342 | 1,622,372.54 | 2,653,360.84 | 22.85% | 0.6752 |
| zirakpur | 295 | 1,162,032.06 | 1,673,539.24 | 16.91% | 0.6641 |

## 4. Error Segmentation by Transaction Type

| Transaction | Count | MAE (INR) | RMSE (INR) | MAPE (%) | R² |
|-------------|-------|-----------|------------|----------|----|
| Resale | 9,535 | 2,149,478.93 | 4,678,443.66 | 23.29% | 0.7985 |
| New Property | 3,357 | 2,369,586.01 | 5,226,303.44 | 18.80% | 0.8348 |

## 5. Top 10 Features by Importance

| Feature | Importance |
|---------|------------|
| `area_per_bhk` | 6949.00 |
| `location_target_enc` | 6103.00 |
| `effective_area_sqft` | 5802.00 |
| `floor_ratio` | 4852.00 |
| `location_log_target_enc` | 4685.00 |
| `total_floors` | 4519.00 |
| `location_freq` | 4433.00 |
| `bhk_x_log_area` | 3327.00 |
| `floor_number` | 2585.00 |
| `total_rooms_proxy` | 1818.00 |

## 6. Diagnostic Figures
- `residuals.png`
- `actual_vs_predicted.png`
- `feature_importance.png`
