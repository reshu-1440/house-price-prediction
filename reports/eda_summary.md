# Exploratory Data Analysis Summary

## 1. Dataset Dimensions & Duplicate Profile
- **Rows**: 187,531
- **Columns**: 21
- **Unique Locations**: 81
- **Exact Duplicates (All Columns)**: 0
- **Duplicates Excluding `Index`**: 119,339
- **Unique Rows Excluding `Index`**: 68,192

## 2. Target (`Price_in_rupees` Parsed from `Amount(in rupees)`) Profile
- **Valid Numeric Price Count**: 177,847
- **`Call for Price` Excluded Count**: 9,684
- **Median Price (INR)**: 7800000.0
- **Mean Price (INR)**: 11981344.19
- **P25 / P75 / P99 (INR)**: 4840000.0 / 14500000.0 / 70000000.0
- **Min / Max (INR)**: 100000.0 / 14003000000.0

## 3. Data Quality Findings
- **100% Null Columns**: ['Dimensions', 'Plot Area']
- **Area Coverage**: Carpet only=106,858, Super only=79,846, Both=0, Neither=827
- **`> 10` String Counts**: Bathroom=35, Balcony=22
- **Transaction Counts**: `{'Resale': 144172, 'New Property': 42565, 'Other': 709, 'nan': 83, 'Rent/Lease': 2}`

## 4. Top 10 Cities by Listing Volume
- `new-delhi`: 27,599
- `bangalore`: 24,030
- `kolkata`: 22,380
- `gurgaon`: 20,070
- `ahmedabad`: 12,750
- `hyderabad`: 12,300
- `chennai`: 10,500
- `jaipur`: 8,490
- `greater-noida`: 4,710
- `faridabad`: 3,840

## 5. Generated Figures
- `missing_values.png`
- `target_distribution.png`
- `categorical_distributions.png`
- `numerical_distributions.png`
- `correlation_matrix.png`
- `price_by_location.png`
