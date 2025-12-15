# Organic Carbon/Elemental Carbon Analyzer (OC/EC)

The OC/EC analyzer measures carbonaceous aerosol components using thermal and optical methods.

::: AeroViz.rawDataReader.script.OCEC.Reader

## Data Format

- File format: CSV file
- Sampling frequency: 1 hour
- File naming pattern: `*LCRes.csv`
- Data structure:
    - Header: 3 rows of metadata
    - Time column: Start Date/Time
    - Carbon fraction measurements
    - Sample volume information

## Measurement Parameters

The OC/EC analyzer provides measurements of:

| Parameter | Unit | Description |
|-----------|------|-------------|
| Thermal_OC | μgC/m³ | Thermal organic carbon |
| Thermal_EC | μgC/m³ | Thermal elemental carbon |
| Optical_OC | μgC/m³ | Optical organic carbon |
| Optical_EC | μgC/m³ | Optical elemental carbon |
| OC1-4 | μgC/m³ | Carbon fractions by temperature |
| PC | μgC/m³ | Pyrolyzed carbon |
| TC | μgC/m³ | Total carbon |

## Data Processing

### Data Reading

- Processes CSV files with varying header structures
- Handles 12/24 hour time formats
- Standardizes column names
- Rounds timestamps to nearest hour
- Converts raw measurements to concentration units

### Quality Control

The OCEC reader uses the declarative **QCFlagBuilder** system with the following rules:

```
+-----------------------------------------------------------------------+
|                         QC Thresholds                                 |
+-----------------------------------------------------------------------+
| MIN_VALUE = -5       μgC/m³                                           |
| MAX_VALUE = 100      μgC/m³                                           |
| MDL (Minimum Detection Limits):                                       |
|   - Thermal_OC: 0.3 μgC/m³                                            |
|   - Optical_OC: 0.3 μgC/m³                                            |
|   - Thermal_EC: 0.015 μgC/m³                                          |
|   - Optical_EC: 0.015 μgC/m³                                          |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
|                            _QC() Pipeline                             |
+-----------------------------------------------------------------------+
|                                                                       |
|  +---------------------------+    +---------------------------+       |
|  | Rule: Invalid Carbon      |    | Rule: Below MDL           |       |
|  +---------------------------+    +---------------------------+       |
|  | Value <= -5 OR            |    | Value < MDL for           |       |
|  | Value > 100 μgC/m³        |    | respective column         |       |
|  +---------------------------+    +---------------------------+       |
|           |                                |                          |
|           v                                v                          |
|  +---------------------------+    +---------------------------+       |
|  | Rule: Spike               |    | Rule: Missing OC          |       |
|  +---------------------------+    +---------------------------+       |
|  | Sudden value change       |    | Thermal_OC is NaN         |       |
|  | (vectorized detection)    |    | (primary measurement)     |       |
|  +---------------------------+    +---------------------------+       |
|                                                                       |
+-----------------------------------------------------------------------+
```

#### QC Rules Applied

| Rule | Condition | Description |
|------|-----------|-------------|
| **Invalid Carbon** | Value ≤ -5 OR > 100 μgC/m³ | Carbon value outside valid range |
| **Below MDL** | Value < MDL | Measurement below minimum detection limit |
| **Spike** | Sudden value change | Unreasonable sudden change detected |
| **Missing OC** | Thermal_OC or Optical_OC is NaN | Primary OC measurement is missing |

#### Minimum Detection Limits

| Parameter | MDL (μgC/m³) |
|-----------|--------------|
| Thermal_OC | 0.3 |
| Optical_OC | 0.3 |
| Thermal_EC | 0.015 |
| Optical_EC | 0.015 |

## Output Data

The processed data contains:

| Column | Unit | Description |
|--------|------|-------------|
| Thermal_OC | μgC/m³ | Thermal organic carbon |
| Thermal_EC | μgC/m³ | Thermal elemental carbon |
| Optical_OC | μgC/m³ | Optical organic carbon |
| Optical_EC | μgC/m³ | Optical elemental carbon |
| TC | μgC/m³ | Total carbon |

!!! note "QC_Flag Handling"

    - The intermediate file (`_read_ocec_qc.pkl/csv`) contains the `QC_Flag` column
    - The final output has invalid data set to NaN and `QC_Flag` column removed

## Notes

- Provides critical information about combustion sources
- Helps identify secondary organic aerosol formation
- Combines thermal and optical analysis methods
- Standardizes output across different instrument formats