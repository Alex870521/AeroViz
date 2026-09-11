# Nephelometer (NEPH)

The Nephelometer is an instrument used for measuring light scattering properties of aerosols at multiple wavelengths.

::: AeroViz.rawDataReader.script.NEPH.Reader

## Raw format

| Time Record Format | T | YYYY | MM | DD | HH | NN | SS |
|:------------------:|:-:|:----:|:--:|:--:|:--:|:--:|:--:|
|      Example       | T | 2022 | 05 | 08 | 13 | 29 | 22 |

| Data Record Format | D | mode | time |    B     |    G     |    R     |    BB    |    GB    |    RB    |
|:------------------:|:-:|:----:|:----:|:--------:|:--------:|:--------:|:--------:|:--------:|:--------:|
|      Example       | D | NBXX | 2258 | 7.527e-5 | 6.984e-5 | 4.275e-5 | 6.821e-6 | 1.070e-5 | 5.130e-6 |

| Auxiliary Record Format | Y |  x  | pressure | Sample Temp | Inlet Temp |  RH  | lamp voltage | lamp current | BNC voltage | Status |
|:-----------------------:|:-:|:---:|:--------:|:-----------:|:----------:|:----:|:------------:|:------------:|:-----------:|:------:|
|         Example         | Y | 348 |   973    |    302.8    |    300     | 91.2 |     12.5     |     5.7      |      2      |  0000  |

- File pattern: `*.dat` (raw data file, record-oriented, no header)
- Native frequency: `5min` (config fallback; the grid actually used is
  detected per file and reported as `df.attrs['raw_freq']`)
- Record types, identified by column 0:
    - `T` records: Timestamp information
    - `D` records: Scattering measurements
    - `Y` records: Status and RH information

### Parse recipe

- `read_csv(header=None, names=range(11))`, then grouped by the record type
  in column 0
- `T` = timestamp: `YYYY MM DD HH MM SS` across columns 1–6, zero-padded and
  concatenated, parsed as `%Y%m%d%H%M%S`
- `D` = data: the `NBXX` (normal scattering) sub-group is used, falling back
  to `NTXX` (total scattering); columns 3–8 × 1e6 → `B`, `G`, `R`, `BB`,
  `BG`, `BR` in Mm⁻¹
- `Y` = state: column 2 pressure, 3 temp1 (sample temperature), 4 temp2
  (inlet temperature), 5 RH, **9 status** (e.g. `0000`, coerced to a
  nullable integer). Column 1 (total counts) and column 8 (status hex) are
  present in the file but not read.
- A file containing a record type outside `{B, G, R, D, T, Y, Z}` is skipped
  with a warning naming the offending rows

**Quirk:** `Y`-row fields are attached to the data frame **positionally**
(`.values`), so a file with unequal `D` and `Y` counts misaligns or raises.

## Measurement parameters

The Nephelometer provides measurements at three wavelengths (TSI 3563 bands):

| Column | Wavelength | Description |
|--------|------------|-------------|
| B | 450 nm | Total scattering (blue) |
| G | 550 nm | Total scattering (green) |
| R | 700 nm | Total scattering (red) |
| BB | 450 nm | Backscattering (blue) |
| BG | 550 nm | Backscattering (green) |
| BR | 700 nm | Backscattering (red) |

## Status & error codes

Column `status` (from `Y` record field 9), mode `numeric` with `ok_value=0`
(see
[status modes](../../../guide/reader-reference.md#3-how-a-status-judgement-is-made)):
a row is an error when the status is not `0` and not NaN. Only `0` (normal
operation) is defined; there is no register table, so
`df.attrs['status_conditions']` is not produced. A missing status column is
logged by `check_status_columns` and leaves the rule inert.

To treat a code as OK, whitelist its numeric value:

```python
RawDataReader('NEPH', path, ignored_status_errors=[4])
```

## QC rules

| Rule | Condition | Severity |
|------|-----------|----------|
| **Status Error** | `status` ≠ 0 and not NaN (see above) | error |
| **No Data** | all six scattering columns (`B`, `G`, `R`, `BB`, `BG`, `BR`) are NaN | error |
| **Invalid Scat Value** | any scattering column ≤ 0 or > 2 000 Mm⁻¹ (`MIN_SCAT_VALUE` / `MAX_SCAT_VALUE`) | error |
| **Invalid Scat Rel** | `B < G` **and** `G < R` — inverted wavelength dependence (expected Blue > Green > Red at 450 / 550 / 700 nm) | error |
| **Insufficient** | an hour holds < 50 % of the points it could have held at the detected frequency (edge hours scaled by coverage) | advisory (`WARNING`) — recorded, data kept |

SAE and `sca_550` are computed in `_process` after QC, not checked by a rule.

## Output

`_process` runs `_scaCoe` on `B`, `G`, `R` (using the 450/550/700 nm bands)
to add `sca_550` and `SAE`, then re-attaches every non-scattering column.

| Column | Unit | Description |
|--------|------|-------------|
| B, G, R | Mm⁻¹ | Total scattering coefficients |
| BB, BG, BR | Mm⁻¹ | Backscattering coefficients |
| sca_550 | Mm⁻¹ | Scattering at 550nm |
| SAE | - | Scattering Angstrom Exponent (positive by convention) |
| RH | % | Relative humidity from the `Y` record |
| pressure | as exported | Pressure from the `Y` record |
| temp1, temp2 | as exported | Sample and inlet temperature from the `Y` record |
| status | - | Raw status code from the `Y` record, carried through unchanged |

Files written per read are listed in
[RawDataReader Reference §1](../../../guide/reader-reference.md#files-written).

## Notes

- Provides information about aerosol optical properties and size distribution
- Supports both normal and total scattering modes
- Wavelength dependence follows Rayleigh scattering principle
