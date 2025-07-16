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

- B, G, R: Total scattering coefficients at blue, green, and red wavelengths (Mm⁻¹)
- BB, BG, BR: Backscattering coefficients at blue, green, and red wavelengths (Mm⁻¹)
- RH: Relative humidity inside the nephelometer (%)

## Data Processing

### Data Reading

- Processes different record types (T, D, Y)
- Extracts timestamp from T records
- Extracts scattering measurements from D records
- Extracts status and RH from Y records
- Converts raw scattering values to Mm⁻¹
- Handles both normal (NBXX) and total (NTXX) scattering modes

### Quality Control

- Removes physically impossible values (negative or > 2000 Mm⁻¹)
- Ensures physical consistency:
    - Backscattering must be less than total scattering
    - Blue > Green > Red (Rayleigh scattering principle)
- Applies time-aware IQR filtering with 1-hour windows
- Ensures data completeness across all channels
- Filters data based on instrument status codes

## Output Data

The processed data contains the following columns:

- Time index: Data acquisition time
- B, G, R: Total scattering coefficients (Mm⁻¹)
- BB, BG, BR: Backscattering coefficients (Mm⁻¹)
- RH: Relative humidity (%)

## Notes

- Provides information about aerosol optical properties and size distribution
- Supports both normal and total scattering modes
- Maintains physical consistency between measurements
- Automatically handles different record types and data formats 