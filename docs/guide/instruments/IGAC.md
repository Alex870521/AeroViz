# In-situ Gas and Aerosol Composition Monitor (IGAC)

The IGAC monitor provides real-time measurements of water-soluble inorganic ions in particulate matter.

## Data Format

- File format: CSV file
- Sampling frequency: Variable
- File naming pattern: `*.csv`
- Data structure:
    - Datetime index
    - Ion concentration columns
    - PM2.5 mass concentration
    - Special values: '-' treated as NA

## Measurement Parameters

The IGAC provides measurements of:

- Cations:
    - Sodium (Na+)
    - Ammonium (NH4+)
    - Potassium (K+)
    - Magnesium (Mg2+)
    - Calcium (Ca2+)
- Anions:
    - Chloride (Cl-)
    - Nitrite (NO2-)
    - Nitrate (NO3-)
    - Phosphate (PO43-)
    - Sulfate (SO42-)

## Data Processing

### Data Reading

- Processes CSV files with datetime index
- Handles special values as NA
- Standardizes column names
- Converts measurements to numeric format
- Removes duplicate timestamps

### Quality Control

- Applies minimum detection limits (MDL):
    - Na+: 0.06 μg/m³
    - NH4+: 0.05 μg/m³
    - K+: 0.05 μg/m³
    - Mg2+: 0.12 μg/m³
    - Ca2+: 0.07 μg/m³
    - Cl-: 0.07 μg/m³
    - NO2-: 0.05 μg/m³
    - NO3-: 0.11 μg/m³
    - SO42-: 0.08 μg/m³
- Verifies total ion mass < PM2.5 mass
- Ensures presence of main ions (NH4+, SO42-, NO3-)
- Applies log-transformed IQR filtering
- Validates ion balance (cation/anion ratio)
- Applies lower exclusion thresholds

## Output Data

The processed data contains:

- Time index: Data acquisition time
- Ion concentrations: All measured ions in μg/m³
- Quality-controlled measurements
- Validated ion balance

## Notes

- Critical for secondary inorganic aerosol analysis
- Significant contributor to PM2.5 mass
- Comprehensive quality control procedures
- Ion balance validation
- Main ion species monitoring 