# TEOM (Tapered Element Oscillating Microbalance)

The TEOM is used for continuous monitoring of PM2.5 mass concentrations using microbalance technology.

::: AeroViz.rawDataReader.script.TEOM.Reader

## Data Format

- File format: CSV file
- Sampling frequency: 6 minutes
- File naming pattern: `*.csv`
- Supported formats:
    - Remote Download Format (Time Stamp column)
    - USB Download/Auto Export Format (tmoStatusCondition_0 column)

### Remote Download Format

| Column | Mapping | Description |
|--------|---------|-------------|
| Time Stamp | time | Timestamp (DD - MM - YYYY HH:MM:SS) |
| System status | status | Instrument status |
| PM-2.5 base MC | PM_NV | Non-volatile PM2.5 |
| PM-2.5 MC | PM_Total | Total PM2.5 |
| PM-2.5 TEOM noise | noise | Measurement noise |

### USB/Auto Export Format

| Column | Mapping | Description |
|--------|---------|-------------|
| Date, Time | time | Timestamp |
| tmoStatusCondition_0 | status | Instrument status |
| tmoTEOMABaseMC_0 | PM_NV | Non-volatile PM2.5 |
| tmoTEOMAMC_0 | PM_Total | Total PM2.5 |
| tmoTEOMANoise_0 | noise | Measurement noise |

## Measurement Parameters

| Parameter | Unit | Description |
|-----------|------|-------------|
| PM_Total | μg/m³ | Total PM2.5 mass concentration |
| PM_NV | μg/m³ | Non-volatile PM2.5 concentration |
| noise | - | TEOM measurement noise |

## Data Processing

### Data Reading

- Unifies column names across different data formats
- Handles various time formats, including Chinese month name conversion
- Converts all measurement values to numeric format
- Removes duplicate timestamps and invalid indices

### Quality Control

The TEOM reader uses the declarative **QCFlagBuilder** system with the following rules:

```
+-----------------------------------------------------------------------+
|                         QC Thresholds                                 |
+-----------------------------------------------------------------------+
| MAX_NOISE          = 0.01                                             |
| MIN_VOL_FRAC       = 0.01      PM_NV / PM_Total minimum               |
| MAX_VOL_FRAC       = 0.9       PM_NV / PM_Total maximum               |
| STATUS_OK          = 0         (numeric status code)                  |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
|                            _QC() Pipeline                             |
+-----------------------------------------------------------------------+
|                                                                       |
|  [Pre-process] Calculate volatile fraction (PM_NV / PM_Total)         |
|       |                                                               |
|       v                                                               |
|  +-------------------------+                                          |
|  | Rule: Status Error      |                                          |
|  +-------------------------+                                          |
|  | Status code != 0        |                                          |
|  +-------------------------+                                          |
|           |                                                           |
|           v                                                           |
|  +-------------------------+    +-------------------------+           |
|  | Rule: High Noise        |    | Rule: Non-positive      |           |
|  +-------------------------+    +-------------------------+           |
|  | noise > 0.01            |    | PM_Total <= 0 OR        |           |
|  +-------------------------+    | PM_NV <= 0              |           |
|           |                     +-------------------------+           |
|           v                              |                            |
|  +-------------------------+             v                            |
|  | Rule: NV > Total        |    +-------------------------+           |
|  +-------------------------+    | Rule: Invalid Vol Frac  |           |
|  | PM_NV > PM_Total        |    +-------------------------+           |
|  | (physically impossible) |    | Ratio > 0.9 OR < 0.01   |           |
|  +-------------------------+    +-------------------------+           |
|           |                              |                            |
|           v                              v                            |
|  +-------------------------+    +-------------------------+           |
|  | Rule: Spike             |    | Rule: Insufficient      |           |
|  +-------------------------+    +-------------------------+           |
|  | Sudden value change     |    | < 50% hourly data       |           |
|  | (vectorized detection)  |    | completeness            |           |
|  +-------------------------+    +-------------------------+           |
|                                                                       |
+-----------------------------------------------------------------------+
```

#### QC Rules Applied

| Rule | Condition | Description |
|------|-----------|-------------|
| **Status Error** | Status ≠ 0 | Non-zero status code indicates instrument error |
| **High Noise** | noise ≥ 0.01 | Measurement noise exceeds threshold |
| **Non-positive** | PM_Total ≤ 0 OR PM_NV ≤ 0 | Non-positive concentration values |
| **NV > Total** | PM_NV > PM_Total | Non-volatile exceeds total (physically impossible) |
| **Invalid Vol Frac** | Ratio < 0 OR > 1 | Volatile fraction outside valid range (0-1) |
| **Spike** | Sudden value change | Unreasonable sudden change detected |
| **Insufficient** | < 50% hourly data | Less than 50% hourly data completeness |

## Output Data

The processed data contains the following columns:

| Column | Unit | Description |
|--------|------|-------------|
| PM_Total | μg/m³ | Total PM2.5 mass concentration |
| PM_NV | μg/m³ | Non-volatile PM2.5 concentration |

!!! note "QC_Flag Handling"

    - The intermediate file (`_read_teom_qc.pkl/csv`) contains the `QC_Flag` column
    - The final output has invalid data set to NaN and `QC_Flag` column removed

## Usage Example

```python
from datetime import datetime
from pathlib import Path

from AeroViz import RawDataReader

# Set data path and time range
data_path = Path('/path/to/your/data/folder')
start_time = datetime(2024, 2, 1)
end_time = datetime(2024, 3, 31, 23, 59, 59)

# Read and process TEOM data
teom_data = RawDataReader(
    instrument='TEOM',
    path=data_path,
    reset=True,
    qc='1MS',
    start=start_time,
    end=end_time,
    mean_freq='1h',
)

# Show processed data
print("\nProcessed TEOM data:")
print(teom_data.head())
```