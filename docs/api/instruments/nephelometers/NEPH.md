# Nephelometer (NEPH)

The Nephelometer is an instrument used for measuring light scattering properties of aerosols at multiple wavelengths.

::: AeroViz.rawDataReader.script.NEPH.Reader

## Data Format

| Time Record Format | T | YYYY | MM | DD | HH | NN | SS |
|:------------------:|:-:|:----:|:--:|:--:|:--:|:--:|:--:|
|      Example       | T | 2022 | 05 | 08 | 13 | 29 | 22 |

| Data Record Format | D | mode | time |    B     |    G     |    R     |    BB    |    GB    |    RB    |
|:------------------:|:-:|:----:|:----:|:--------:|:--------:|:--------:|:--------:|:--------:|:--------:|
|      Example       | D | NBXX | 2258 | 7.527e-5 | 6.984e-5 | 4.275e-5 | 6.821e-6 | 1.070e-5 | 5.130e-6 |

| Auxiliary Record Format | Y |  x  | pressure | Sample Temp | Inlet Temp |  RH  | lamp voltage | lamp current | BNC voltage | Status |
|:-----------------------:|:-:|:---:|:--------:|:-----------:|:----------:|:----:|:------------:|:------------:|:-----------:|:------:|
|         Example         | Y | 348 |   973    |    302.8    |    300     | 91.2 |     12.5     |     5.7      |      2      |  0000  |

- File format: Raw data file (.dat)
- Sampling frequency: 5 minutes
- File naming pattern: `*.dat`
- Record types:
    - T records: Timestamp information
    - D records: Scattering measurements
    - Y records: Status and RH information

## Measurement Parameters

The Nephelometer provides measurements at three wavelengths:

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

- Processes different record types (T, D, Y)
- Extracts timestamp from T records
- Extracts scattering measurements from D records
- Extracts status and RH from Y records
- Converts raw scattering values to Mm⁻¹
- Handles both normal (NBXX) and total (NTXX) scattering modes

### Quality Control

The NEPH reader uses the declarative **QCFlagBuilder** system with the following rules:

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
|  | (from Y record col 9)     |                                        |
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
| **Status Error** | Status ≠ 0 | Non-zero status code indicates instrument error |
| **No Data** | All columns NaN | All scattering columns are missing |
| **Invalid Scat Value** | Value ≤ 0 OR > 2000 Mm⁻¹ | Scattering outside valid range |
| **Invalid Scat Rel** | B < G < R | Wavelength dependence violation |
| **Insufficient** | < 50% hourly data | Less than 50% hourly data completeness |

#### Wavelength Dependence Check

```
    Scattering (Mm⁻¹)
       ^
       |     Expected: Blue > Green > Red
       |
       |  B *
       |      \
       |       G *
       |           \
       |            R *
       +----+----+----+-----> Wavelength
           450  550  700
```

## Output Data

The processed data contains the following columns:

| Column | Unit | Description |
|--------|------|-------------|
| B, G, R | Mm⁻¹ | Total scattering coefficients |
| BB, BG, BR | Mm⁻¹ | Backscattering coefficients |
| sca_550 | Mm⁻¹ | Scattering at 550nm |
| SAE | - | Scattering Angstrom Exponent |

!!! note "QC_Flag Handling"

    - The intermediate file (`_read_neph_qc.pkl/csv`) contains the `QC_Flag` column
    - The final output has invalid data set to NaN and `QC_Flag` column removed

## Notes

- Provides information about aerosol optical properties and size distribution
- Supports both normal and total scattering modes
- Wavelength dependence follows Rayleigh scattering principle
