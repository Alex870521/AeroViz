# RawDataReader Pipeline (Internals)

> **Who is this for?** Contributors and advanced users who want to understand or
> modify how the reader works internally. If you just want to *use* the reader,
> start with the [RawDataReader Tutorial](rawdatareader.md) — you don't need
> anything on this page.
>
> **See also:** [Data Levels (L0–L3)](data-levels.md) for the level contracts
> (what each stage may add or destroy, what is cacheable, where new code goes)
> and the list of known non-conformances;
> [Raw Formats & Status Codes](../api/instruments/raw-formats-and-status.md) for
> per-instrument parsing recipes and the authoritative status/error-code tables.

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
| `_process`    | + abs_370–950, AAE, eBC       | keeps size bins + `QC_Flag` only     |
| `__call__`    | invalid rows → NaN, drop `QC_Flag` | invalid rows → NaN, drop `QC_Flag` |
| Final output  | BC, abs, AAE                  | dN/dlogDp matrix; statistics go to `_stats.csv` |

For SMPS/APS the **size distribution is the output**: `_process` drops the raw
status column and returns the bins, and the derived statistics (total / GMD /
GSD / mode) are written to `{prefix}_stats.csv` alongside the N/S/V distribution
files. Pass `append_stats=True` to also append them to the returned frame.

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
  TEOM, BAM1020, OCEC, IGAC, Xact, GRIMM, EPA
  (Q-ACSM has no reader yet)

Instruments with _process() method:
  AE33, AE43, BC1054, MA350, NEPH, Aurora, SMPS, APS, TEOM
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

Two patterns: readers whose `_process` adds further rules (AE33, AE43, BC1054,
MA350 — `Invalid AAE`) store the partial summary in `self._qc_summary` and emit
the combined output from `_process`; everyone else (OCEC, BAM1020, TEOM, EPA,
IGAC, Xact) emits it directly inside `_QC`. SMPS/APS/NEPH/Aurora have a
`_process` but add no rules, so they just log the stored summary unchanged.

---

## Per-Instrument QC Procedures

> The diagrams below are a visual overview. The **authoritative** per-instrument
> tables — file patterns, header layouts, status columns, error-code meanings,
> whitelist semantics and known coverage gaps — are in
> [Raw Formats & Status Codes](../api/instruments/raw-formats-and-status.md).

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
│  │       (AE43 only)   │                                            │
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

Note: AE33 deliberately excludes 128 / 256 / 384 (tape-LOW warnings — the data
is still valid); AE43 still lists 384. See Data Levels §7 (P1-f).
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
│   Returns the dN/dlogDp bins + QC_Flag (raw status column dropped)  │
│                                                                     │
│  STAGE 3: __call__ → finalize_size_dist()  [L3 sidecars]            │
│   {prefix}_dNdlogDp.csv / _dSdlogDp.csv / _dVdlogDp.csv             │
│   {prefix}_stats.csv   (psd_stats: total / GMD / GSD / mode)        │
│   append_stats=True also appends the statistics to the returned df  │
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
│   Returns the dN/dlogDp bins + QC_Flag (raw status column dropped)  │
│                                                                     │
│  STAGE 3: __call__ → finalize_size_dist()  [L3 sidecars]            │
│   same four CSVs as SMPS; diameters in µm                           │
└─────────────────────────────────────────────────────────────────────┘
```

#### GRIMM

```
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 1: _QC()                                                     │
│  ┌────────────────────────┐  ┌────────────────────────┐             │
│  │ Rule: No Data          │  │ Rule: Negative Conc    │             │
│  ├────────────────────────┤  ├────────────────────────┤             │
│  │ All channels NaN       │  │ Any channel < 0        │             │
│  └────────────────────────┘  └────────────────────────┘             │
│  ┌────────────────────────┐                                         │
│  │ Rule: Insufficient     │  < 50% hourly data (uses the DETECTED   │
│  └────────────────────────┘  frequency, not the config value)       │
│                                                                     │
│  No concentration range check: no sample corpus to calibrate one    │
│  against, and a wrong threshold silently deletes good data.         │
└─────────────────────────────────────────────────────────────────────┘
Output: size channels, QC_Flag
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
  STATUS_OK = 0       (status is a 32-bit bitfield; tested bitwise)

┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 1: _QC()                                                     │
│  ┌────────────────────────┐                                         │
│  │ Rule: Status Error     │  Any non-whitelisted warning bit set    │
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
│  │ Rule: Above MR         │  ┌────────────────────────┐             │
│  ├────────────────────────┤  │ Rule: Ion Balance      │             │
│  │ Conc > measurement     │  ├────────────────────────┤             │
│  │ range (from config)    │  │ Cation/Anion ratio     │             │
│  └────────────────────────┘  │ outside valid range    │             │
│                              └────────────────────────┘             │
│  Below MDL → per-species DIAGNOSTIC in the log, not a flag          │
└─────────────────────────────────────────────────────────────────────┘
Output: every spec species present (gases included), QC_Flag
```

MDL and MR come from `meta['IGAC']` (the vendor spec) — the reader used to carry
a second, disagreeing copy of the 9 aerosol ions and drop the gas species
entirely. Below-MDL is reported per species instead of flagged, because a
non-`Valid` flag NaNs the whole row and would take the other species with it.

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
| IGAC       | Yes           | 4     | Mass Closure, Missing Main, Above MR, Ion Balance                |
| EPA        | Yes           | 1     | Negative                                                         |
| Xact       | Yes           | 5     | Calibration Mode, Instrument Error, Upscale Warning, Invalid Value, Internal Std Drift |
| GRIMM      | Yes           | 3     | No Data, Negative Conc, Insufficient                             |
| Q-ACSM     | —             | —     | reader not implemented yet (registered as *pending*)             |

!!! info "Every reader now produces a `QC_Flag`"
    GRIMM used to be a pass-through, which crashed the default `qc=True` path
    with `AttributeError: … 'report_dict'`. It now has three rules, and
    `self.report_dict` defaults to `{}` so a future flag-less reader degrades to
    a rate-less report instead of raising.

    `VOC` and `Minion` used to share that problem; both were **removed** from the
    reader (pre-aggregated second-hand data with no raw log to parse) and now
    raise a `KeyError` with migration advice.

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
| GRIMM      | 6 min       | size-channel concentrations                  |
| TEOM       | 6 min       | PM_Total, PM_NV, Volatile_Fraction          |
| BAM1020    | 1 h         | PM mass concentration                       |
| OCEC       | 1 h         | thermal / optical OC & EC                   |
| IGAC       | 1 h         | ion concentrations (9 species)              |
| Xact       | 1 h         | element concentrations                      |
| EPA        | 1 h         | air-quality reference data                  |
