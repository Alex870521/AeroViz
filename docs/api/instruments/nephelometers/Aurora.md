# Aurora Integrating Nephelometer

The Aurora is an integrating nephelometer used for measuring light scattering properties of aerosols at multiple wavelengths.

::: AeroViz.rawDataReader.script.Aurora.Reader

## Raw format

- File pattern: `*.csv`
- Native frequency: `1min` (config fallback; the grid actually used is
  detected per file and reported as `df.attrs['raw_freq']`)
- Timestamp column: the first column (`Data_Time` on the production Ecotech
  export, `Date / time local` on others), used as the index and coerced to
  datetime; `Raw_Data_Time` is dropped as redundant
- Column naming conventions (all are rewritten to the standard names below):
    - `0°σspB`, `0°σspG`, `0°σspR` → `B`, `G`, `R`; `90°σspB`, `90°σspG`,
      `90°σspR` → `BB`, `BG`, `BR`
    - `Blue`, `Green`, `Red` → `B`, `G`, `R`; `B_Blue`, `B_Green`, `B_Red` →
      `BB`, `BG`, `BR`
    - the production CSV layout is `Data_Time, Raw_Data_Time, Red, Green,
      Blue, B_Red, B_Green, B_Blue, T1, T2, RH, P, S1, S2`
- Every other source column (`T1`, `T2`, `RH`, `P`, `S2`, …) is kept

### Parse recipe

- `read_csv(low_memory=False, index_col=0)`; column names are stripped of
  surrounding spaces before the aliases are applied
- The first column found among `Status`, `status`, `Error`, `error`, `Flag`,
  `flag`, **`S1`** is renamed to `Status`
- Rows with an unparseable or duplicated timestamp are dropped

## Measurement parameters

The Aurora provides measurements at three wavelengths (Ecotech Aurora 3000
bands, as used by the SAE / `sca_550` computation):

| Column | Wavelength | Description |
|--------|------------|-------------|
| B | 450 nm | Total scattering (blue) |
| G | 525 nm | Total scattering (green) |
| R | 635 nm | Total scattering (red) |
| BB | 450 nm | Backscattering (blue) |
| BG | 525 nm | Backscattering (green) |
| BR | 635 nm | Backscattering (red) |

## Status & error codes

Column `Status` (after the rename above), mode `numeric` with `ok_value=0`
(see
[status modes](../../../guide/reader-reference.md#3-how-a-status-judgement-is-made)):
a row is an error when the status is not `0` and not NaN. Only `0` (normal
operation, ambient sampling) is defined; there is no register table, so
`df.attrs['status_conditions']` is not produced. A missing status column is
logged by `check_status_columns` and leaves the rule inert.

**`S1` is the status.** The production CSV contains none of the *obvious*
status names — the status is `S1`. Evidence from 120 one-minute scans
(2025-01-01): `S1 ∈ {0, 4}`; the 17 rows with `S1 == 4` are **contiguous**
(00:06–00:22) and their scattering decays 185 → 0.78 Mm⁻¹ while `S1 == 0`
rows average 193 Mm⁻¹ — the signature of the **zero/span check**, where the
instrument samples filtered air. Those rows pass the 0–2000 range check, so
before `S1` was recognised they were averaged into ambient means: on that
fixture, dropping them raises the green-channel mean from 170.8 to
193.2 Mm⁻¹, a **13 % low bias** removed.

**`S2`** moves in step (`0x07` while ambient, `0xAB`/`0xA8` during the
check) and is evidently a bitfield. Its bits are **not** decoded — no manual
to hand, and guessing bit meanings would be worse than leaving it as data. It
is carried through to the output unchanged.

To treat a code as OK (for example if a site wants the zero/span rows kept),
whitelist its numeric value:

```python
RawDataReader('Aurora', path, ignored_status_errors=[4])
```

## QC rules

| Rule | Condition | Severity |
|------|-----------|----------|
| **Status Error** | `Status` ≠ 0 and not NaN (see above) | error |
| **No Data** | all six scattering columns (`B`, `G`, `R`, `BB`, `BG`, `BR`) are NaN | error |
| **Invalid Scat Value** | any scattering column ≤ 0 or > 2 000 Mm⁻¹ (`MIN_SCAT_VALUE` / `MAX_SCAT_VALUE`) | error |
| **Invalid Scat Rel** | `B < G` **and** `G < R` — inverted wavelength dependence (physically blue should scatter most) | error |
| **Insufficient** | an hour holds < 50 % of the points it could have held at the detected frequency (edge hours scaled by coverage) | advisory (`WARNING`) — recorded, data kept |

SAE and `sca_550` are computed in `_process` after QC, not checked by a rule.

## Output

`_process` runs `_scaCoe` on `B`, `G`, `R` (using the 450/525/635 nm bands)
to add `sca_550` and `SAE`, then re-attaches every non-scattering column.

| Column | Unit | Description |
|--------|------|-------------|
| B, G, R | Mm⁻¹ | Total scattering coefficients |
| BB, BG, BR | Mm⁻¹ | Backscattering coefficients |
| sca_550 | Mm⁻¹ | Scattering at 550nm |
| SAE | - | Scattering Angstrom Exponent (positive by convention) |
| T1, T2, RH, P, Status (from `S1`), S2, … | as exported | All other source columns, carried through unchanged |

Files written per read are listed in
[RawDataReader Reference §1](../../../guide/reader-reference.md#files-written).

## Notes

- Provides real-time measurement of aerosol scattering
- Same QC rules as NEPH nephelometer
- Wavelength dependence follows Rayleigh scattering principle
