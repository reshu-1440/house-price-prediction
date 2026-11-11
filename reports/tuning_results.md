# Hyperparameter Optimization Results

- **Cross-Validation**: 3-Fold Shuffled CV (on `51,568` training rows only)
- **Optuna Trials per Boosting Model**: 12
- **RandomizedSearchCV Iterations (RandomForest)**: 6
- **Selected Champion Model**: `lightgbm`

| Model | CV R² | Train R² | Test R² | Train-Test Gap | Test MAE (INR) | Test RMSE (INR) | Test MAPE (%) |
|-------|-------|----------|---------|----------------|----------------|-----------------|---------------|
| lightgbm | 0.8082 | 0.9318 | 0.8128 | 0.1190 | 2,206,793.51 | 4,827,094.43 | 22.12% |
| xgboost | 0.8014 | 0.9363 | 0.8102 | 0.1260 | 2,212,525.78 | 4,859,924.57 | 22.09% |
| random_forest | 0.7915 | 0.9389 | 0.8019 | 0.1370 | 2,235,657.22 | 4,965,677.59 | 22.35% |

## Best Hyperparameters

```yaml
xgboost:
  params:
    n_estimators: 500
    learning_rate: 0.06902851863975029
    max_depth: 8
    min_child_weight: 2
    subsample: 0.9424774630404985
    colsample_bytree: 0.8997327922401265
    reg_lambda: 0.8152843673110735
  cv_r2: 0.8014
  test_r2: 0.8102
  test_mae: 2212525.78
lightgbm:
  params:
    n_estimators: 550
    learning_rate: 0.09106605805411622
    num_leaves: 108
    min_child_samples: 33
    subsample: 0.8523371562065996
    colsample_bytree: 0.9258061086311944
    reg_lambda: 0.6568564419223103
  cv_r2: 0.8082
  test_r2: 0.8128
  test_mae: 2206793.51
random_forest:
  params:
    n_estimators: 150
    min_samples_leaf: 2
    max_features: 0.7
    max_depth: 22
  cv_r2: 0.7915
  test_r2: 0.8019
  test_mae: 2235657.22
best_model: lightgbm
```
