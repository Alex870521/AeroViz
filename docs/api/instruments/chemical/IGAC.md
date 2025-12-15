# In-situ Gas and Aerosol Composition Monitor (IGAC)

The IGAC monitor provides real-time measurements of water-soluble inorganic ions in particulate matter.

::: AeroViz.rawDataReader.script.IGAC.Reader

## Data Format

- File format: CSV file
- Sampling frequency: 1 hour
- File naming pattern: `*.csv`
- Data structure:
    - Datetime index
    - Ion concentration columns
    - PM2.5 mass concentration
    - Special values: '-' treated as NA

## Measurement Parameters

The IGAC provides measurements of water-soluble ions:

### Cations

| Ion | Unit | Description |
|-----|------|-------------|
| Na+ | μg/m³ | Sodium |
| NH4+ | μg/m³ | Ammonium |
| K+ | μg/m³ | Potassium |
| Mg2+ | μg/m³ | Magnesium |
| Ca2+ | μg/m³ | Calcium |

### Anions

| Ion | Unit | Description |
|-----|------|-------------|
| Cl- | μg/m³ | Chloride |
| NO2- | μg/m³ | Nitrite |
| NO3- | μg/m³ | Nitrate |
| PO43- | μg/m³ | Phosphate |
| SO42- | μg/m³ | Sulfate |

## Data Processing

### Data Reading

- Processes CSV files with datetime index
- Handles special values as NA
- Standardizes column names
- Converts measurements to numeric format
- Removes duplicate timestamps

### Quality Control

The IGAC reader uses the declarative **QCFlagBuilder** system with the following rules:

```
+-----------------------------------------------------------------------+
|                         QC Thresholds                                 |
+-----------------------------------------------------------------------+
| MDL (Minimum Detection Limits):                                       |
|   Cations: Na+ 0.06, NH4+ 0.05, K+ 0.05, Mg2+ 0.12, Ca2+ 0.07 μg/m³   |
|   Anions:  Cl- 0.07, NO2- 0.05, NO3- 0.11, SO42- 0.08 μg/m³           |
| Main Ions: NH4+, SO42-, NO3- (must be present)                        |
| Ion Balance: 0.8 < cation/anion ratio < 1.2                           |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
|                            _QC() Pipeline                             |
+-----------------------------------------------------------------------+
|                                                                       |
|  [Pre-process] Calculate ion sum, cation/anion equivalents            |
|       |                                                               |
|       v                                                               |
|  +---------------------------+    +---------------------------+       |
|  | Rule: Mass Closure        |    | Rule: Missing Main        |       |
|  +---------------------------+    +---------------------------+       |
|  | Ion sum > PM2.5 mass      |    | NH4+, SO42-, or NO3-      |       |
|  | (physically impossible)   |    | is missing                |       |
|  +---------------------------+    +---------------------------+       |
|           |                                |                          |
|           v                                v                          |
|  +---------------------------+    +---------------------------+       |
|  | Rule: Below MDL           |    | Rule: Ion Balance         |       |
|  +---------------------------+    +---------------------------+       |
|  | Any ion below its         |    | Cation/Anion ratio        |       |
|  | detection limit           |    | outside 0.8-1.2 range     |       |
|  +---------------------------+    +---------------------------+       |
|                                                                       |
+-----------------------------------------------------------------------+
```

#### QC Rules Applied

| Rule | Condition | Description |
|------|-----------|-------------|
| **Mass Closure** | Ion sum > PM2.5 | Total ion mass exceeds PM2.5 (physically impossible) |
| **Missing Main** | NH4+, SO42-, or NO3- is NaN | Primary ion species are missing |
| **Below MDL** | Value < MDL | Measurement below minimum detection limit |
| **Ion Balance** | Ratio < 0.8 OR > 1.2 | Cation/Anion equivalent ratio imbalance |

#### Minimum Detection Limits

| Ion | MDL (μg/m³) |
|-----|-------------|
| Na+ | 0.06 |
| NH4+ | 0.05 |
| K+ | 0.05 |
| Mg2+ | 0.12 |
| Ca2+ | 0.07 |
| Cl- | 0.07 |
| NO2- | 0.05 |
| NO3- | 0.11 |
| SO42- | 0.08 |

#### Ion Balance Check

```
    Cation/Anion Ratio
         ^
     1.2 +-------------------------------- Upper limit
         |   +-----------------------+
         |   |    VALID RANGE        |
     1.0 +---|       (balanced)      |
         |   +-----------------------+
     0.8 +-------------------------------- Lower limit
         +----------------------------> Sample
```

## Output Data

The processed data contains:

| Column | Unit | Description |
|--------|------|-------------|
| Na+, NH4+, K+, Mg2+, Ca2+ | μg/m³ | Cation concentrations |
| Cl-, NO2-, NO3-, PO43-, SO42- | μg/m³ | Anion concentrations |

!!! note "QC_Flag Handling"

    - The intermediate file (`_read_igac_qc.pkl/csv`) contains the `QC_Flag` column
    - The final output has invalid data set to NaN and `QC_Flag` column removed

## Notes

- Critical for secondary inorganic aerosol analysis
- Significant contributor to PM2.5 mass
- Comprehensive quality control procedures
- Ion balance validation ensures data integrity
- Main ion species (NH4+, SO42-, NO3-) typically dominate