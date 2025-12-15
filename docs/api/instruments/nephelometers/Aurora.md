# Aurora Integrating Nephelometer

The Aurora is an integrating nephelometer used for measuring light scattering properties of aerosols at multiple wavelengths.

::: AeroViz.rawDataReader.script.Aurora.Reader

## Data Format

- File format: CSV file
- Sampling frequency: 1 minute
- File naming pattern: `*.csv`
- Timestamp column: Date / time local
- Column naming conventions:
    - UV BCc, Blue BCc, Green BCc, Red BCc, IR BCc
    - Biomass BCc, Fossil fuel BCc
    - Delta-C, AAE, BB (%)

## Measurement Parameters

The Aurora provides measurements at three wavelengths:

| Column | Wavelength | Description |
|--------|------------|-------------|
| B | 450 nm | Total scattering (blue) |
| G | 550 nm | Total scattering (green) |
| R | 700 nm | Total scattering (red) |
| BB | 450 nm | Backscattering (blue) |
| BG | 550 nm | Backscattering (green) |
| BR | 700 nm | Backscattering (red) |

## Data Processing

### Data Reading

- Parses timestamps from 'Date / time local' column
- Standardizes column names for consistent output
- Converts all measurement values to numeric format
- Handles different column naming conventions
- Maps wavelength-specific measurements to standardized names

### Quality Control

The Aurora reader uses the declarative **QCFlagBuilder** system with the following rules:

```
+-----------------------------------------------------------------------+
|                         QC Thresholds                                 |
+-----------------------------------------------------------------------+
| MIN_SCAT_VALUE = 0       Mm⁻¹                                         |
| MAX_SCAT_VALUE = 2000    Mm⁻¹                                         |
| STATUS_OK      = 0       (numeric status code)                        |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
|                            _QC() Pipeline                             |
+-----------------------------------------------------------------------+
|                                                                       |
|  [Pre-process] Calculate scattering Angstrom exponent (SAE)           |
|       |                                                               |
|       v                                                               |
|  +---------------------------+                                        |
|  | Rule: Status Error        |                                        |
|  +---------------------------+                                        |
|  | Status code != 0          |                                        |
|  | (if column available)     |                                        |
|  +---------------------------+                                        |
|           |                                                           |
|           v                                                           |
|  +---------------------------+    +---------------------------+       |
|  | Rule: No Data             |    | Rule: Invalid Scat Value  |       |
|  +---------------------------+    +---------------------------+       |
|  | All columns are NaN       |    | Value <= 0 OR             |       |
|  +---------------------------+    | Value > 2000 Mm⁻¹         |       |
|           |                       +---------------------------+       |
|           v                                |                          |
|  +---------------------------+             v                          |
|  | Rule: Invalid Scat Rel    |    +---------------------------+       |
|  +---------------------------+    | Rule: Insufficient        |       |
|  | Blue < Green < Red        |    +---------------------------+       |
|  | (violates physics)        |    | < 50% hourly data         |       |
|  +---------------------------+    +---------------------------+       |
|                                                                       |
+-----------------------------------------------------------------------+
```

#### QC Rules Applied

| Rule | Condition | Description |
|------|-----------|-------------|
| **Status Error** | Status ≠ 0 | Non-zero status code indicates instrument error (if column available) |
| **No Data** | All columns NaN | All scattering columns are missing |
| **Invalid Scat Value** | Value ≤ 0 OR > 2000 Mm⁻¹ | Scattering outside valid range |
| **Invalid Scat Rel** | B < G < R | Wavelength dependence violation |
| **Insufficient** | < 50% hourly data | Less than 50% hourly data completeness |

## Output Data

The processed data contains the following columns:

| Column | Unit | Description |
|--------|------|-------------|
| B, G, R | Mm⁻¹ | Total scattering coefficients |
| BB, BG, BR | Mm⁻¹ | Backscattering coefficients |
| sca_550 | Mm⁻¹ | Scattering at 550nm |
| SAE | - | Scattering Angstrom Exponent |

!!! note "QC_Flag Handling"

    - The intermediate file (`_read_aurora_qc.pkl/csv`) contains the `QC_Flag` column
    - The final output has invalid data set to NaN and `QC_Flag` column removed

## Notes

- Provides real-time measurement of aerosol scattering
- Same QC rules as NEPH nephelometer
- Wavelength dependence follows Rayleigh scattering principle
