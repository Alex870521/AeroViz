# RawDataReader Pipeline (Internals)

> **Who is this for?** Contributors and advanced users who want to understand or
> modify how the reader works internally. If you just want to *use* the reader,
> start with the [RawDataReader Tutorial](rawdatareader.md) — you don't need
> anything on this page.

How `RawDataReader` turns raw instrument files into the final resampled DataFrame.

---

## Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                  RawDataReader(inst, path, start, end, qc=True)             │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  1. _raw_reader()                                                           │
│     ├─ Read raw files (*.dat, *.txt, *.csv)                                 │
│     ├─ Time resolution: instrument-native (1min/5min/6min/1h)               │
│     └─ Columns: every column from the source file (no pre-selection)        │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  2. _timeIndex_process()                                                    │
│     ├─ Align to standard time grid (freq inferred or via raw_freq kwarg)    │
│     └─ Warn on off-grid timestamps before snapping                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  3. _QC()                                                                   │
│     ├─ QCFlagBuilder applies declarative QC rules                           │
│     ├─ Adds `QC_Flag` column ("Valid" / "Status Error" / "Insufficient"...) │
│     └─ Stores QC Summary (emitted by _process or directly here)             │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  4. _process()  (optional, BC / scattering / size-distribution instruments) │
│     ├─ Derive parameters (Abs, AAE, eBC, GMD, GSD, ...)                     │
│     ├─ Apply additional QC (e.g. Invalid AAE) and update `QC_Flag`          │
│     └─ Emit combined QC Summary                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  5. _save_data()                                                            │
│     ├─ _read_{inst}_raw.{pkl,csv}  — pre-QC frame                           │
│     └─ _read_{inst}_qc.{pkl,csv}   — post-QC frame with `QC_Flag`           │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  6. __call__() — apply QC                                                   │
│     ├─ Rows where `QC_Flag != "Valid"` → NaN                                │
│     └─ Drop `QC_Flag` from public output                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  7. _generate_report()                                                      │
│     ├─ Acquisition rate: periods with data / expected periods               │
│     ├─ Yield rate:       periods passing QC / periods with data             │
│     └─ Total rate:       periods passing QC / expected periods              │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  8. Final output                                                            │
│     ├─ resample(mean_freq) — only if mean_freq given (default: no resample) │
│     ├─ output_{inst}.csv                                                    │
│     ├─ output_{inst}_dN/dS/dVdlogDp.csv (SMPS/APS)                          │
│     ├─ report.json                                                          │
│     └─ return DataFrame                                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Column Evolution

| Stage         | AE33 example                  | APS example                          |
|---------------|-------------------------------|--------------------------------------|
| `_raw_reader` | BC1–7, ATN, Flow, Status, ... | size bins (0.5–20 μm) + metadata     |
| `_QC`         | + `QC_Flag`                   | + `QC_Flag`                          |
| `_process`    | + abs_370–950, AAE, eBC       | + total, GMD, GSD, mode (num/surf/vol) |
| `__call__`    | invalid rows → NaN, drop `QC_Flag` | invalid rows → NaN, drop `QC_Flag` |
| Final output  | BC, abs, AAE                  | statistics (size bins removed)       |

`_raw_reader` deliberately keeps *all* source columns so downstream consumers
have access to instrument metadata (flow, temperature, pressure, RH, etc.).
Column selection happens in `_QC` / `_process` per-instrument.

---

## File Output Structure

```
{instrument}_outputs/
├── _read_{instrument}_raw.pkl     # Raw frame (no QC_Flag)
├── _read_{instrument}_raw.csv
├── _read_{instrument}_qc.pkl      # Post-QC frame (with QC_Flag)
├── _read_{instrument}_qc.csv
├── output_{instrument}.csv        # Resampled, invalid → NaN, QC_Flag dropped
├── output_{instrument}_dN/dS/dVdlogDp.csv   # SMPS / APS only
├── report.json                    # Quality report (rates + summary)
└── {instrument}.log               # Processing log
```

---

## QC System

### QC methods (`AeroViz/rawDataReader/core/qc.py`)

| Method                       | Description                              |
|------------------------------|------------------------------------------|
| `n_sigma`                    | N standard-deviation filter              |
| `iqr`                        | Interquartile-range filter               |
| `time_aware_rolling_iqr`     | Rolling-window IQR                       |
| `time_aware_std_QC`          | Rolling-window standard deviation        |
| `bidirectional_trend_std_QC` | Trend-aware standard deviation           |
| `filter_error_status`        | Status-code filter                       |
| `hourly_completeness_QC`     | Data-completeness check (≥ 50% per hour) |
| `spike_detection`            | Vectorised spike detection (change rate) |

### QCFlagBuilder architecture

```
┌──────────────────┐     ┌──────────────────┐
│     QCRule       │     │  QCFlagBuilder   │
├──────────────────┤     ├──────────────────┤
│ - name           │     │ - rules[]        │
│ - condition()    │────►│ + add_rule()     │
│ - description    │     │ + add_rules()    │
└──────────────────┘     │ + apply()        │
                         │ + get_summary()  │
                         └──────────────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │   DataFrame      │
                         ├──────────────────┤
                         │ + QC_Flag column │
                         │   "Valid" or     │
                         │   "Rule1, Rule2" │
                         └──────────────────┘

Instruments using QCFlagBuilder:
  AE33, AE43, BC1054, MA350, SMPS, APS, NEPH, Aurora,
  TEOM, BAM1020, OCEC, IGAC, EPA

Instruments with _process() method:
  AE33, AE43, BC1054, MA350, NEPH, Aurora, SMPS, APS
```

### QC_Flag lifecycle

```
_QC()              → builds QC_Flag, stores partial summary
_process()         → may add more rules (e.g. Invalid AAE) and emit combined summary
_generate_report() → uses QC_Flag to compute rates
__call__()         → marks non-"Valid" rows as NaN, then drops QC_Flag
```

### QC Summary format

```
AE33 QC Summary:
  Status Error: 24312 (4.9%)
  Invalid BC: 29265 (5.9%)
  Insufficient: 105481 (21.1%)
  Invalid AAE: 25948 (5.2%)
  Valid: 356025 (71.2%)
```

For instruments with `_process()`: `_QC` stores the summary in
`self._qc_summary`, `_process` adds any extra rules and emits the combined
output. For instruments without `_process()` (OCEC, BAM1020, TEOM, EPA, IGAC),
the summary is emitted directly inside `_QC`.

---

## Per-Instrument QC Procedures

### Black Carbon Instruments

#### AE33 / AE43 Aethalometer

```
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 1: _QC()                                                     │
│  ┌─────────────────────┐  ┌─────────────────────┐                   │
│  │ Rule: Status Error  │  │ Rule: Invalid BC    │                   │
│  ├─────────────────────┤  ├─────────────────────┤                   │
│  │ Status contains:    │  │ BC ≤ 0  OR          │                   │
│  │   1   Tape adv.     │  │ BC > 20000 ng/m³    │                   │
│  │   2   First meas.   │  └─────────────────────┘                   │
│  │   3   Stopped       │  ┌─────────────────────┐                   │
│  │   4   Flow error    │  │ Rule: Insufficient  │                   │
│  │   16  LED calib.    │  ├─────────────────────┤                   │
│  │   32  Calib. error  │  │ < 50% hourly data   │                   │
│  │   384 Tape error    │  └─────────────────────┘                   │
│  │   1024 Stability    │                                            │
│  │   2048 Clean air    │                                            │
│  │   4096 Optical      │                                            │
│  └─────────────────────┘                                            │
│                                                                     │
│  STAGE 2: _process()                                                │
│  ┌─────────────────────┐  ┌─────────────────────┐                   │
│  │ Calculate:          │  │ Rule: Invalid AAE   │                   │
│  │ - _absCoe()         │─►├─────────────────────┤                   │
│  │ - abs_370…abs_950   │  │ AAE < -2.0  OR      │                   │
│  │ - AAE, eBC          │  │ AAE > -0.7          │                   │
│  └─────────────────────┘  └─────────────────────┘                   │
└─────────────────────────────────────────────────────────────────────┘
Output: BC1-BC7, abs_370-950, abs_550, AAE, eBC, QC_Flag
```

#### BC1054

```
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 1: _QC()                                                     │
│  [Pre-filter] Remove consecutive duplicate rows                     │
│       ▼                                                             │
│  ┌─────────────────────┐  ┌─────────────────────┐                   │
│  │ Rule: Status Error  │  │ Rule: Invalid BC    │                   │
│  ├─────────────────────┤  ├─────────────────────┤                   │
│  │ Error codes:        │  │ BC ≤ 0  OR          │                   │
│  │   1     Power       │  │ BC > 20000 ng/m³    │                   │
│  │   2     Sensor      │  └─────────────────────┘                   │
│  │   4     Tape        │  ┌─────────────────────┐                   │
│  │   8     Maint.      │  │ Rule: Insufficient  │                   │
│  │   16    Flow        │  ├─────────────────────┤                   │
│  │   32    Auto adv.   │  │ < 50% hourly data   │                   │
│  │   64    Detector    │  └─────────────────────┘                   │
│  │   256   Range       │                                            │
│  │   512   Nozzle      │                                            │
│  │   1024  SPI link    │                                            │
│  │   2048  Calib.      │                                            │
│  │   65536 Tape move   │                                            │
│  └─────────────────────┘                                            │
│                                                                     │
│  STAGE 2: _process()                                                │
│  ┌─────────────────────┐  ┌─────────────────────┐                   │
│  │ Calculate:          │  │ Rule: Invalid AAE   │                   │
│  │ - _absCoe()         │─►├─────────────────────┤                   │
│  │ - abs_370…abs_950   │  │ AAE < -2.0  OR      │                   │
│  │ - AAE, eBC          │  │ AAE > -0.7          │                   │
│  └─────────────────────┘  └─────────────────────┘                   │
└─────────────────────────────────────────────────────────────────────┘
Output: BC1-BC10, abs_370-950, abs_550, AAE, eBC, QC_Flag
```

#### MA350

```
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 1: _QC()                                                     │
│  ┌─────────────────────┐  ┌─────────────────────┐                   │
│  │ Rule: Status Error  │  │ Rule: Invalid BC    │                   │
│  ├─────────────────────┤  ├─────────────────────┤                   │
│  │ Error codes:        │  │ BC ≤ 0  OR          │                   │
│  │   1   Power         │  │ BC > 20000 ng/m³    │                   │
│  │   2   Start up      │  └─────────────────────┘                   │
│  │   4   Tape adv.     │  ┌─────────────────────┐                   │
│  │   16+ Various       │  │ Rule: Insufficient  │                   │
│  └─────────────────────┘  ├─────────────────────┤                   │
│                           │ < 50% hourly data   │                   │
│                           └─────────────────────┘                   │
│                                                                     │
│  STAGE 2: _process()                                                │
│  ┌─────────────────────┐  ┌─────────────────────┐                   │
│  │ Calculate:          │  │ Rule: Invalid AAE   │                   │
│  │ - _absCoe()         │─►├─────────────────────┤                   │
│  │ - abs_375…abs_880   │  │ AAE < -2.0  OR      │                   │
│  │ - AAE, eBC          │  │ AAE > -0.7          │                   │
│  └─────────────────────┘  └─────────────────────┘                   │
└─────────────────────────────────────────────────────────────────────┘
Output: BC1-BC5, abs_375-880, abs_550, AAE, eBC, QC_Flag
```

### Size Distribution Instruments

#### SMPS

```
QC Thresholds
  MIN_HOURLY_COUNT   = 5     measurements per hour
  MIN_TOTAL_CONC     = 2000  #/cm³
  MAX_TOTAL_CONC     = 1e7   #/cm³
  MAX_LARGE_BIN_CONC = 4000  dN/dlogDp (DMA water-ingress indicator)
  LARGE_BIN_THRESH   = 400   nm
  STATUS_OK          = "Normal Scan"

┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 1: _QC()                                                     │
│  ┌──────────────────────┐                                           │
│  │ Rule: Status Error   │  Status Flag ≠ "Normal Scan"              │
│  └──────────────────────┘                                           │
│  ┌──────────────────────┐  ┌──────────────────────┐                 │
│  │ Rule: Insufficient   │  │ Rule: Invalid Number │                 │
│  ├──────────────────────┤  │       Conc           │                 │
│  │ < 50% hourly data    │  ├──────────────────────┤                 │
│  └──────────────────────┘  │ Total outside        │                 │
│                            │ 2000-1e7 #/cm³       │                 │
│                            └──────────────────────┘                 │
│  ┌──────────────────────┐                                           │
│  │ Rule: DMA Water      │  Bins > 400 nm with conc.                 │
│  │       Ingress        │  > 4000 dN/dlogDp                         │
│  └──────────────────────┘                                           │
│                                                                     │
│  STAGE 2: _process()                                                │
│   Calculate from dN/dlogDp → dN, dS, dV distributions               │
│   For each weighting (num, surf, vol):                              │
│     total_{w}, GMD_{w}, GSD_{w}, mode_{w}                           │
│   Mode contributions (number):                                      │
│     ultra_num   fraction < 100 nm                                   │
│     accum_num   fraction 100-1000 nm                                │
└─────────────────────────────────────────────────────────────────────┘
```

#### APS

```
QC Thresholds
  MIN_HOURLY_COUNT = 5      measurements per hour
  MIN_TOTAL_CONC   = 1      #/cm³
  MAX_TOTAL_CONC   = 700    #/cm³
  STATUS_OK        = "0000 0000 0000 0000"  (16-bit binary, all zeros)

Status flag bit definitions (TSI RF command)
  Bit 0  Laser fault                    Bit 5  Autocal failed
  Bit 1  Total flow out of range        Bit 6  Internal temp < 10 °C
  Bit 2  Sheath flow out of range       Bit 7  Internal temp > 40 °C
  Bit 3  Excessive sample concentration Bit 8  Detector voltage ±10 % Vb
  Bit 4  Accumulator clipped (>65535)   Bit 9  Reserved

┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 1: _QC()                                                     │
│  ┌──────────────────────┐                                           │
│  │ Rule: Status Error   │  Status Flags ≠ all zeros                 │
│  └──────────────────────┘                                           │
│  ┌──────────────────────┐  ┌──────────────────────┐                 │
│  │ Rule: Insufficient   │  │ Rule: Invalid Number │                 │
│  ├──────────────────────┤  │       Conc           │                 │
│  │ < 50% hourly data    │  ├──────────────────────┤                 │
│  └──────────────────────┘  │ Total outside 1-700  │                 │
│                            │ #/cm³                │                 │
│                            └──────────────────────┘                 │
│                                                                     │
│  STAGE 2: _process()                                                │
│   Calculate from dN/dlogDp → dN, dS, dV distributions               │
│   Totals at size cutoffs (num, surf, vol):                          │
│     total_{w}_1um, total_{w}_2.5um, total_{w}_all                   │
│   Full-range statistics:                                            │
│     GMD_{w}, GSD_{w}, mode_{w}                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Scattering Instruments

#### NEPH / Aurora

```
QC Thresholds
  MIN_SCAT_VALUE = 0     Mm⁻¹
  MAX_SCAT_VALUE = 2000  Mm⁻¹
  STATUS_OK      = 0     (numeric status code)

┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 1: _QC()                                                     │
│  ┌────────────────────────┐                                         │
│  │ Rule: Status Error     │  Status ≠ 0 (if column present)         │
│  └────────────────────────┘                                         │
│  ┌────────────────────────┐  ┌────────────────────────┐             │
│  │ Rule: No Data          │  │ Rule: Invalid Scat     │             │
│  ├────────────────────────┤  ├────────────────────────┤             │
│  │ All columns NaN        │  │ Value ≤ 0  OR          │             │
│  └────────────────────────┘  │ Value > 2000 Mm⁻¹      │             │
│  ┌────────────────────────┐  └────────────────────────┘             │
│  │ Rule: Invalid Scat Rel │  Blue < Green < Red                     │
│  ├────────────────────────┤  (violates physics)                     │
│  │ Wavelength ordering    │                                         │
│  └────────────────────────┘                                         │
│  ┌────────────────────────┐                                         │
│  │ Rule: Insufficient     │  < 50% hourly data                      │
│  └────────────────────────┘                                         │
│                                                                     │
│  STAGE 2: _process()                                                │
│   Calculate _scaCoe() → sca_550, SAE                                │
└─────────────────────────────────────────────────────────────────────┘

Wavelength dependence check — expected ordering:
  Scattering ↑
    B *
       \
        G *
           \
            R *
    ──┴────┴────┴── Wavelength →
     450  550  700
```

### Mass Concentration Instruments

#### TEOM

```
QC Thresholds
  MAX_NOISE = 0.01
  STATUS_OK = 0       (numeric status code)

┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 1: _QC()                                                     │
│  ┌────────────────────────┐                                         │
│  │ Rule: Status Error     │  Status ≠ 0                             │
│  └────────────────────────┘                                         │
│  ┌────────────────────────┐  ┌────────────────────────┐             │
│  │ Rule: High Noise       │  │ Rule: Non-positive     │             │
│  ├────────────────────────┤  ├────────────────────────┤             │
│  │ noise ≥ 0.01           │  │ PM_NV ≤ 0  OR          │             │
│  └────────────────────────┘  │ PM_Total ≤ 0           │             │
│  ┌────────────────────────┐  └────────────────────────┘             │
│  │ Rule: NV > Total       │                                         │
│  ├────────────────────────┤                                         │
│  │ PM_NV > PM_Total       │                                         │
│  │ (physically impossible)│                                         │
│  └────────────────────────┘                                         │
│  ┌────────────────────────┐  ┌────────────────────────┐             │
│  │ Rule: Spike            │  │ Rule: Insufficient     │             │
│  ├────────────────────────┤  ├────────────────────────┤             │
│  │ Sudden value change    │  │ < 50% hourly data      │             │
│  │ (vectorised)           │  │                        │             │
│  └────────────────────────┘  └────────────────────────┘             │
│                                                                     │
│  STAGE 2: _process()                                                │
│   Volatile_Fraction = (PM_Total - PM_NV) / PM_Total                 │
└─────────────────────────────────────────────────────────────────────┘
Output: PM_NV, PM_Total, Volatile_Fraction, QC_Flag
```

#### BAM1020

```
QC Thresholds
  MIN_CONC = 0    µg/m³
  MAX_CONC = 500  µg/m³

┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 1: _QC()                                                     │
│  ┌────────────────────────┐  ┌────────────────────────┐             │
│  │ Rule: Invalid Conc     │  │ Rule: Spike            │             │
│  ├────────────────────────┤  ├────────────────────────┤             │
│  │ Conc ≤ 0  OR           │  │ Sudden value change    │             │
│  │ Conc > 500 µg/m³       │  │ (vectorised)           │             │
│  └────────────────────────┘  └────────────────────────┘             │
└─────────────────────────────────────────────────────────────────────┘
Output: Conc, QC_Flag
```

### Chemical Composition Instruments

#### OCEC

```
QC Thresholds              Detection Limits (MDL)
  MIN_VALUE = -5  µgC/m³     Thermal_OC : 0.3   µgC/m³
  MAX_VALUE = 100 µgC/m³     Thermal_EC : 0.015 µgC/m³
                             Optical_OC : 0.3   µgC/m³
                             Optical_EC : 0.015 µgC/m³

┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 1: _QC()                                                     │
│  ┌────────────────────────┐  ┌────────────────────────┐             │
│  │ Rule: Invalid Carbon   │  │ Rule: Below MDL        │             │
│  ├────────────────────────┤  ├────────────────────────┤             │
│  │ Value ≤ -5  OR         │  │ Below method detection │             │
│  │ Value > 100 µgC/m³     │  │ limit                  │             │
│  └────────────────────────┘  └────────────────────────┘             │
│  ┌────────────────────────┐  ┌────────────────────────┐             │
│  │ Rule: Spike            │  │ Rule: Missing OC       │             │
│  ├────────────────────────┤  ├────────────────────────┤             │
│  │ Sudden value change    │  │ Thermal_OC/Optical_OC  │             │
│  │ (vectorised)           │  │ missing                │             │
│  └────────────────────────┘  └────────────────────────┘             │
└─────────────────────────────────────────────────────────────────────┘
Output: Thermal_OC, Thermal_EC, Optical_OC, Optical_EC, TC, OC1-4, PC, QC_Flag
```

#### IGAC

```
Detection Limits (MDL, µg/m³)
  Na+  0.06   NH4+ 0.05   K+   0.05   Mg2+ 0.12   Ca2+ 0.07
  Cl-  0.07   NO2- 0.05   NO3- 0.11   SO4²⁻ 0.08

┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 1: _QC()                                                     │
│  ┌────────────────────────┐  ┌────────────────────────┐             │
│  │ Rule: Mass Closure     │  │ Rule: Missing Main     │             │
│  ├────────────────────────┤  ├────────────────────────┤             │
│  │ Total ions > PM2.5     │  │ NH4+/SO4²⁻/NO3-        │             │
│  └────────────────────────┘  │ missing                │             │
│  ┌────────────────────────┐  └────────────────────────┘             │
│  │ Rule: Below MDL        │  ┌────────────────────────┐             │
│  ├────────────────────────┤  │ Rule: Ion Balance      │             │
│  │ Concentration < MDL    │  ├────────────────────────┤             │
│  └────────────────────────┘  │ Cation/Anion ratio     │             │
│                              │ outside valid range    │             │
│                              └────────────────────────┘             │
└─────────────────────────────────────────────────────────────────────┘
Output: ion columns, QC_Flag
```

### Other Data Sources

#### EPA

```
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 1: _QC()                                                     │
│  ┌────────────────────────┐                                         │
│  │ Rule: Negative Value   │  Any measurement value < 0              │
│  └────────────────────────┘                                         │
└─────────────────────────────────────────────────────────────────────┘
Output: all columns, QC_Flag
```

---

## QC Summary Table

| Instrument | QCFlagBuilder | Rules | Key Checks                                                       |
|------------|---------------|-------|------------------------------------------------------------------|
| AE33       | Yes           | 4     | Status, Invalid BC, Invalid AAE, Insufficient                    |
| AE43       | Yes           | 4     | Status, Invalid BC, Invalid AAE, Insufficient                    |
| BC1054     | Yes           | 4     | Status, Invalid BC, Invalid AAE, Insufficient                    |
| MA350      | Yes           | 4     | Status, Invalid BC, Invalid AAE, Insufficient                    |
| SMPS       | Yes           | 4     | Status, Invalid Number Conc, DMA Water, Insufficient             |
| APS        | Yes           | 3     | Status, Invalid Number Conc, Insufficient                        |
| NEPH       | Yes           | 5     | Status, No Data, Invalid Scat, Invalid Rel, Insufficient         |
| Aurora     | Yes           | 5     | Status, No Data, Invalid Scat, Invalid Rel, Insufficient         |
| TEOM       | Yes           | 6     | Status, High Noise, Non-pos, NV>Total, Spike, Insufficient       |
| BAM1020    | Yes           | 2     | Invalid Conc, Spike                                              |
| OCEC       | Yes           | 4     | Invalid Carbon, Below MDL, Spike, Missing OC                     |
| IGAC       | Yes           | 4     | Mass Closure, Missing Main, Below MDL, Ion Balance               |
| EPA        | Yes           | 1     | Negative                                                         |
| VOC        | —             | 0     | not implemented                                                  |
| XRF / Xact | —             | 0     | not implemented                                                  |
| GRIMM      | —             | 0     | not implemented                                                  |

---

## Rate Calculation

The `report.json` contains three rates, all computed from `QC_Flag`. A period
(week or month) counts as *Valid* when more than 50 % of its data points have
`QC_Flag == "Valid"`.

| Rate              | Definition                                |
|-------------------|-------------------------------------------|
| Acquisition Rate  | periods with data / expected periods      |
| Yield Rate        | periods passing QC / periods with data    |
| Total Rate        | periods passing QC / expected periods     |

---

## Native Time Resolution

| Instrument | Native freq | Main outputs                                |
|------------|------------:|---------------------------------------------|
| AE33       | 1 min       | BC, abs coef, AAE                           |
| AE43       | 1 min       | BC, abs coef, AAE                           |
| BC1054     | 1 min       | BC, abs coef, AAE                           |
| MA350      | 1 min       | BC, abs coef, AAE                           |
| Aurora     | 1 min       | scattering (RGB), sca_550, SAE              |
| NEPH       | 5 min       | scattering (RGB), sca_550, SAE              |
| SMPS       | 6 min       | total, GMD, GSD, mode (num/surf/vol)        |
| APS        | 6 min       | totals at cutoffs, GMD, GSD, mode           |
| GRIMM      | 6 min       | size-distribution statistics                |
| TEOM       | 6 min       | PM_Total, PM_NV, Volatile_Fraction          |
| BAM1020    | 1 h         | PM mass concentration                       |
| OCEC       | 1 h         | thermal / optical OC & EC                   |
| IGAC       | 1 h         | ion concentrations (9 species)              |
| Xact       | 1 h         | element concentrations                      |
| VOC        | 1 h         | VOC concentrations                          |
| EPA        | 1 h         | air-quality reference data                  |
