# Scanning Mobility Particle Sizer (SMPS)

The SMPS is an instrument used for measuring particle size distributions in the nanometer range.

::: AeroViz.rawDataReader.script.SMPS.Reader

## Data Format

- File format:
    - .txt files (tab-delimited) from older AIM versions (8.x, 9.x)
    - .csv files (comma-delimited) from newer AIM versions (10.x+)
- Sampling frequency: 6 minutes (typical)
- File naming pattern: `*.txt` or `*.csv`
- Timestamp formats:
    - mm/dd/yy HH:MM:SS (US format, older versions)
    - mm/dd/yyyy HH:MM:SS (US format, newer versions)
    - dd/mm/yyyy HH:MM:SS (EU format)

## Measurement Parameters

The SMPS provides particle size distribution measurements:

| Parameter | Value | Description |
|-----------|-------|-------------|
| Size range | 11.8-593.5 nm | Default particle diameter range |
| Output | dN/dlogDp | Number concentration per size bin |
| Unit | #/cm³ | Particle number concentration |

## Data Processing

### Data Reading

- Automatically detects and skips header rows
- Supports multiple date formats based on AIM version
- Handles transposed data formats
- Extracts and sorts particle size columns numerically
- Validates size range against expected settings

### Quality Control

The SMPS reader uses the declarative **QCFlagBuilder** system with the following rules:

```
+-----------------------------------------------------------------------+
|                         QC Thresholds                                 |
+-----------------------------------------------------------------------+
| MIN_HOURLY_COUNT  = 5        measurements per hour                    |
| MIN_TOTAL_CONC    = 2000     #/cm³                                    |
| MAX_TOTAL_CONC    = 1e7      #/cm³                                    |
| MAX_LARGE_BIN_CONC= 4000     dN/dlogDp (DMA water ingress indicator)  |
| LARGE_BIN_THRESH  = 400      nm                                       |
| STATUS_OK         = "Normal Scan"                                     |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
|                            _QC() Pipeline                             |
+-----------------------------------------------------------------------+
|                                                                       |
|  [Pre-process] Apply size range filter, calculate total concentration |
|       |                                                               |
|       v                                                               |
|  +-------------------------+                                          |
|  | Rule: Status Error      |                                          |
|  +-------------------------+                                          |
|  | Status Flag !=          |                                          |
|  | "Normal Scan"           |                                          |
|  +-------------------------+                                          |
|           |                                                           |
|           v                                                           |
|  +-------------------------+    +-------------------------+           |
|  | Rule: Insufficient      |    | Rule: Invalid Number    |           |
|  +-------------------------+    |       Conc              |           |
|  | < 5 measurements        |    +-------------------------+           |
|  | per hour                |    | Total conc. outside     |           |
|  +-------------------------+    | range (2000-1e7 #/cm³)  |           |
|                                 +-------------------------+           |
|           |                              |                            |
|           v                              v                            |
|           |                     +-------------------------+           |
|           |                     | Rule: DMA Water Ingress |           |
|           |                     +-------------------------+           |
|           |                     | Bins > 400nm with       |           |
|           |                     | conc. > 4000 dN/dlogDp  |           |
|           |                     | (indicates water in DMA)|           |
|           |                     +-------------------------+           |
|                                                                       |
+-----------------------------------------------------------------------+
```

#### QC Rules Applied

| Rule | Condition | Description |
|------|-----------|-------------|
| **Status Error** | Status Flag ≠ "Normal Scan" | Instrument reported error (e.g., "Conditioner Temperature Error") |
| **Insufficient** | < 5 measurements/hour | Less than 5 measurements per hour |
| **Invalid Number Conc** | Total < 2000 OR > 1e7 #/cm³ | Total number concentration outside valid range |
| **DMA Water Ingress** | Bins >400nm > 4000 dN/dlogDp | Water contamination in DMA column |

#### Size Distribution QC Visualization

```
    dN/dlogDp
       ^
       |
  4000 +                              ........... MAX_LARGE_BIN_CONC
       |      ___                     :          (DMA water ingress)
       |     /   \                    :
       |    /     \____               :
       +---+------+-------+-------+---+---> Dp (nm)
          11.8   100     400    593.5
                          ^
                    LARGE_BIN_THRESHOLD
```

## Output Data

The processed data contains:

| Column | Unit | Description |
|--------|------|-------------|
| Size bins | dN/dlogDp | Number concentration for each particle size |

!!! note "QC_Flag Handling"

    - The intermediate file (`_read_smps_qc.pkl/csv`) contains the `QC_Flag` column
    - The final output has invalid data set to NaN and `QC_Flag` column removed

## Notes

- Different AIM software versions may produce different file formats
- Size range validation ensures data quality
- DMA water ingress detection: High concentrations in bins >400nm indicate water contamination in the DMA column
- Automatic format detection and parsing
