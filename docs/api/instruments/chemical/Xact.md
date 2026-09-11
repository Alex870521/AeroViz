# Xact 625i XRF Analyzer

The Xact 625i is a continuous X-ray fluorescence (XRF) analyzer for real-time elemental analysis of particulate matter.

::: AeroViz.rawDataReader.script.Xact.Reader
    options:
      show_root_heading: true
      heading_level: 3

## Instrument Overview

| Specification | Value |
|---------------|-------|
| Manufacturer | Cooper Environmental Services |
| Model | Xact 625i |
| Measurement | Elemental composition (ng/m3) |
| Time Resolution | Hourly |
| Elements | 72 elements (Mg to U) |

## Raw format

- **File pattern**: `*.csv`
- **Native frequency**: `1h`
- **Encoding**: read as UTF-8 with undecodable bytes ignored
- **Time format**: `TIME` column, `MM/DD/YYYY HH:MM:SS` (`%m/%d/%Y %H:%M:%S`)
- **Header layout**: **two** header rows — line 0 is the element names in
  capitals (`MAGNESIUM,,ALUMINIUM,,…`), line 1 is the real header. Data rows
  carry one extra trailing field, absorbed as `_extra_` and dropped.
- **Data structure**: element concentrations with uncertainties + environmental
  parameters

### Column Structure

The raw data file contains:

1. **Element concentrations**: `Element AtomicNumber (ng/m3)` (e.g., `Mg 12 (ng/m3)`)
2. **Uncertainties**: `Element Uncert (ng/m3)` (e.g., `Mg uncert (ng/m3)`)
3. **Environmental parameters**: Temperature, pressure, flow, RH, etc.
4. **Alarm codes**: Instrument status indicators

### Parse recipe

1. `TIME` is parsed straight into the index; duplicate and NaT indices are
   removed.
2. Rows with `Sample Type != 1` are dropped **before** rounding to `1h`
   (`1` = normal sample, `2` = calibration). The instrument runs a daily QA
   check at 00:00–00:30; dropping it first stops that row from displacing a
   valid 00:30 sample when both round to 00:00.
3. The index is rounded to `1h`.
4. Element columns are matched by pattern: `Mg 12 (ng/m3)` → `Mg`,
   `Al Uncert (ng/m3)` → `Al_uncert` (case-insensitive `uncert`).
5. Environment columns are renamed to short forms — `AT (C)` → `AT`,
   `SAMPLE (C)` → `SAMPLE_T`, `BP (mmHg)` → `BP`, `TAPE (mmHg)` → `TAPE`,
   `FLOW 25 (slpm)` → `FLOW_25`, `FLOW ACT (lpm)` → `FLOW_ACT`,
   `FLOW STD (slpm)` → `FLOW_STD`, `VOLUME (L)` → `VOLUME`, `TUBE (C)` →
   `TUBE_T`, `ENCLOSURE (C)` → `ENCLOSURE_T`, `FILAMENT (V)` → `FILAMENT_V`,
   `SDD (C)` → `SDD_T`, `DPP (C)` → `DPP_T`, `RH (%)` → `RH`, `WIND (m/s)` →
   `WIND`, `WIND DIR (deg)` → `WIND_DIR`, `SAMPLE TIME (min)` → `SAMPLE_TIME`,
   `Sample Type` → `SAMPLE_TYPE` (the full list is the Environmental Columns
   table below).
6. `_extra_`, `TIME`, `PUMP START TIME`, `Output Pin 7 (True=ON)` and `XC VER`
   are dropped.
7. The modal `SAMPLE_TIME` of the file is remembered (`reader._sample_time`);
   it selects which column of the manual's detection-limit table applies.
8. Every remaining column is kept (~75 per file).

## Supported Elements

```python
ELEMENTS = [
    'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar', 'K', 'Ca', 'Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe',
    'Co', 'Ni', 'Cu', 'Zn', 'Ga', 'Ge', 'As', 'Se', 'Br', 'Rb', 'Sr', 'Y', 'Zr', 'Nb', 'Mo',
    'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In', 'Sn', 'Sb', 'Te', 'I', 'Cs', 'Ba', 'La', 'Ce',
    'Pr', 'Nd', 'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu',
    'Hf', 'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg', 'Tl', 'Pb', 'Bi', 'Th', 'Pa', 'U'
]
```

## Usage

```python
from datetime import datetime
from pathlib import Path
from AeroViz import RawDataReader

# Read Xact data
data = RawDataReader(
    instrument='Xact',
    path=Path('/path/to/xact/data'),
    start=datetime(2024, 1, 1),
    end=datetime(2024, 12, 31),
    mean_freq='1h'
)

# View available elements
print(data.columns.tolist())
# ['Mg', 'Al', 'Si', 'S', 'K', 'Ca', 'Fe', 'Pb', ...]
```

## Status & error codes

Column `ALARM`, matched by **exact code** — Xact is the one reader that does
not go through `filter_error_status`, so none of the
[status modes](../../../guide/reader-reference.md#3-how-a-status-judgement-is-made)
apply and `ignored_status_errors` has no effect on it. `0` = normal.
`Reader.decode_alarm(code)` turns a code into its text (unknown codes come back
as `Unknown Alarm (<code>)`). Error codes (100–110) fire `Instrument Error`
and invalidate the row; warning codes (200–203) fire the advisory
`Upscale Warning` — the instrument's own distinction between an error and a
channel near the top of its calibration, honoured as such.

### Alarm Codes

**Error Codes (100-110)** - Invalidate data:

| Code | Description |
|------|-------------|
| 100 | X-ray Voltage Error |
| 101 | X-ray Current Error |
| 102 | Tube Temperature Error |
| 103 | Enclosure Temperature Error |
| 104 | Tape Error |
| 105 | Pump Error |
| 106 | Filter Wheel Error |
| 107 | Dynamic Rod Error |
| 108 | Nozzle Error |
| 109 | Energy Calibration Error |
| 110 | Software Error |

**Warning Codes (200-203)** - Upscale warnings:

| Code | Description |
|------|-------------|
| 200 | Upscale Cr Warning |
| 201 | Upscale Pb Warning |
| 202 | Upscale Cd Warning |
| 203 | Upscale Nb Warning |

## QC rules

Each rule is registered only if its source column exists in the file.

| Rule | Condition | Severity |
|------|-----------|----------|
| `Calibration Mode` | `SAMPLE_TYPE != 1` (and not NaN) — catches any calibration row that survived the L1 filter | error |
| `Instrument Error` | `ALARM` in 100–110 | error |
| `Upscale Warning` | `ALARM` in 200–203 | advisory |
| `Invalid Value` | any element concentration `< 0` (`MIN_VALUE`) or `> 100,000` ng/m³ (`MAX_VALUE`) | error |
| `High Uncertainty` | a normally-quantitative element with a published limit reports `value >= MDL` while `value < 3σ` (`σ` = its `_uncert`, `> 0`) | advisory |
| `Internal Std Drift` | `Nb` outside ±20 % (`INTERNAL_STD_TOLERANCE`) of its median over the read | error |

### Detection limits

`reader.MDL` is the **manual's own table** (Xact 625i Operation Manual,
Appendix "Minimum Detection Limits", p.73, encoded as `Reader.MANUAL_MDL`) for
the 29 elements it covers, selected by the file's `SAMPLE_TIME`: the limits vary
~8× between a 15-min and a 240-min sample, so one fixed number is right for only
one configuration. `meta['Xact']['MDL']` in `config/supported_instruments.py`
supplies the other 16 (Ga, Ge, Rb, Sr, Y, Zr, Nb, Mo, Pd, Te, Cs, La, Ce, W,
Pt, Au), for which CES publishes nothing. Exposed as `reader.MDL` /
`reader.manual_mdl(minutes)`; a sample time between two tabulated ones takes
the *longer* column (the conservative direction), and with no observed sample
time 60 min is assumed.

Manual 1σ detection limits (ng/m³) by sample time (min):

| Element | 15 | 30 | 60 | 120 | 180 | 240 |
|---------|----|----|----|-----|-----|-----|
| Al | 840 | 290 | 100 | 35 | 19 | 12 |
| Si | 150 | 51 | 17.8 | 6.3 | 3.4 | 2.2 |
| P | 44 | 15 | 5.2 | 1.8 | 0.99 | 0.64 |
| S | 26 | 9.1 | 3.16 | 1.1 | 0.6 | 0.39 |
| Cl | 15 | 5 | 1.73 | 0.61 | 0.33 | 0.21 |
| K | 9.8 | 3.4 | 1.17 | 0.41 | 0.22 | 0.14 |
| Ca | 2.5 | 0.86 | 0.3 | 0.1 | 0.057 | 0.037 |
| Ti | 1.3 | 0.46 | 0.16 | 0.056 | 0.03 | 0.02 |
| V | 1 | 0.34 | 0.12 | 0.042 | 0.023 | 0.015 |
| Cr | 0.97 | 0.33 | 0.12 | 0.041 | 0.022 | 0.014 |
| Mn | 1.2 | 0.41 | 0.14 | 0.05 | 0.027 | 0.018 |
| Fe | 1.4 | 0.49 | 0.17 | 0.061 | 0.033 | 0.021 |
| Co | 1.1 | 0.39 | 0.14 | 0.049 | 0.026 | 0.017 |
| Ni | 0.78 | 0.27 | 0.1 | 0.034 | 0.018 | 0.012 |
| Cu | 0.65 | 0.23 | 0.079 | 0.028 | 0.015 | 0.01 |
| Zn | 0.55 | 0.19 | 0.067 | 0.023 | 0.013 | 0.008 |
| As | 0.52 | 0.18 | 0.063 | 0.022 | 0.012 | 0.008 |
| Se | 0.66 | 0.23 | 0.081 | 0.029 | 0.016 | 0.01 |
| Br | 0.85 | 0.3 | 0.1 | 0.037 | 0.02 | 0.013 |
| Ag | 16 | 5.5 | 1.9 | 0.68 | 0.37 | 0.24 |
| Cd | 21 | 7.2 | 2.5 | 0.89 | 0.48 | 0.31 |
| In | 26 | 8.9 | 3.1 | 1.1 | 0.6 | 0.39 |
| Sn | 33 | 12 | 4.1 | 1.4 | 0.78 | 0.51 |
| Sb | 42 | 15 | 5.2 | 1.8 | 0.99 | 0.64 |
| Ba | 3.3 | 1.1 | 0.39 | 0.14 | 0.074 | 0.048 |
| Hg | 0.99 | 0.35 | 0.12 | 0.043 | 0.023 | 0.015 |
| Tl | 0.95 | 0.33 | 0.12 | 0.041 | 0.022 | 0.014 |
| Pb | 1 | 0.36 | 0.13 | 0.045 | 0.024 | 0.016 |
| Bi | 1.1 | 0.37 | 0.13 | 0.046 | 0.025 | 0.016 |

### Uncertainty and Currie's criteria

Every element has a paired `{element}_uncert` column. The manual's limits are
*"interference free **one sigma** detection limits … at 68 % Confidence Level
(C1σ) per US EPA IO 3.3 and Currie, 1968"*, and that uncertainty column is the
same 1σ quantity — which is what lets Currie's criteria apply to it directly:
**detected** at `value >= 3σ` (`DETECTION_SIGMA`), **quantifiable** at
`value >= 10σ` (`QUANTIFICATION_SIGMA`).

### Element reliability

`element_reliability(df)` classifies each element from the fraction of the
run's samples meeting those criteria — `quantitative` (≥ 75 % quantifiable,
`RELIABLE_FRACTION`), `semi-quantitative` (≥ 75 % detected) or
`below-detection` — and reports *separately* whether the manual publishes a
limit for it at all (`published_limit`). The two axes are independent: Nb, the
internal standard, is measured superbly and has no published limit, while an
element that is in the manual and still sits below detection is simply not
present at this site. The verdicts are written to
`{prefix}_element_reliability.csv` (columns `verdict`, `published_limit`, `n`,
`detected`, `quantifiable`, `median_rel_uncert`, `manual_mdl`, worst first) and
summarised in the log. On the test corpus: 11 quantitative (S, K, Ca, Cl, Fe,
Cu, Zn, Br, Mn, Pb, As), 7 semi-quantitative (Ti, Cr, Ni, Se, Ba, Bi, Sr), the
rest below detection.

### Below MDL is a diagnostic, not a flag

Same reasoning as IGAC, and more acute here: in the test fixture alone a dozen
elements sit 100 % below their limit, so an "any element below MDL" rule would
flag — and therefore NaN — every single row. The log reports the per-element
fraction below its limit instead (`log_below_mdl` over `reader.MDL`).

### Why `High Uncertainty` is scoped

The same trap. A rule firing when *any* element fails the 3σ test hits
**96–100 % of rows** on both fixtures, because a dozen elements are permanently
below detection at any real site — a property of the element, not of the row.
Scoped to elements this run measures well (`quantitative`) *and* the manual
specifies, it fires on 0 % of clean rows and 8 % of the degraded fixture, where
it caught S, K, Ca, Fe, Zn and Br degrading together: an instrument event
rather than element noise. The rule's description names the elements it is
watching; it is advisory because the reading is suspect while the rest of the
row's elements are not, and masking is per row.

## Output

L2 carries **all columns**: every element, its `_uncert`, and the environment
columns.

### Element Columns

Each detected element has two columns:
- `Element` - Concentration in ng/m3 (e.g., `Pb`, `Fe`, `S`)
- `Element_uncert` - Measurement uncertainty in ng/m3 (1σ)

### Environmental Columns

| Column | Description | Unit |
|--------|-------------|------|
| `AT` | Ambient Temperature | C |
| `SAMPLE_T` | Sample Temperature | C |
| `BP` | Barometric Pressure | mmHg |
| `TAPE` | Tape Pressure | mmHg |
| `FLOW_25` | Flow at 25C | slpm |
| `FLOW_ACT` | Actual Flow | lpm |
| `FLOW_STD` | Standard Flow | slpm |
| `VOLUME` | Sample Volume | L |
| `TUBE_T` | X-ray Tube Temperature | C |
| `ENCLOSURE_T` | Enclosure Temperature | C |
| `FILAMENT_V` | Filament Voltage | V |
| `SDD_T` | SDD Temperature | C |
| `DPP_T` | DPP Temperature | C |
| `RH` | Relative Humidity | % |
| `WIND` | Wind Speed | m/s |
| `WIND_DIR` | Wind Direction | deg |
| `SAMPLE_TIME` | Sample Time | min |
| `ALARM` | Alarm Code | - |
| `SAMPLE_TYPE` | Sample Type (1 = normal, 2 = calibration) | - |

Files written per read are listed in
[RawDataReader Reference §1](../../../guide/reader-reference.md#files-written);
Xact additionally writes `{prefix}_element_reliability.csv`.

## Example Analysis

```python
from AeroViz import RawDataReader
from pathlib import Path
from datetime import datetime

# Read data
xact = RawDataReader(
    instrument='Xact',
    path=Path('./data/xact'),
    start=datetime(2024, 1, 1),
    end=datetime(2024, 3, 31)
)

# Calculate crustal elements ratio
soil_elements = ['Al', 'Si', 'Ca', 'Fe', 'Ti']
xact['Soil'] = (
    2.20 * xact['Al'] +
    2.49 * xact['Si'] +
    1.63 * xact['Ca'] +
    2.42 * xact['Fe'] +
    1.94 * xact['Ti']
) / 1000  # Convert to ug/m3

# Heavy metals analysis
heavy_metals = ['Pb', 'Cd', 'As', 'Cr', 'Ni']
print(xact[heavy_metals].describe())
```

## Notes

- Data is automatically rounded to hourly resolution
- Duplicate timestamps are removed
- Non-numeric values are coerced to NaN
- QC flags are stored in `QC_Flag` column during processing
- Units are ng/m3 (nanograms per cubic meter)
