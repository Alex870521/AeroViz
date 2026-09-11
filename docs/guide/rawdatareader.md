# RawDataReader Usage

RawDataReader is the core data reading component of AeroViz, providing a unified interface for reading various aerosol instrument data.

!!! warning "Behaviour change"
    `mean_freq` no longer defaults to `'1h'`. The default is now **no
    resampling** — data is returned at its native resolution. Pass
    `mean_freq='1h'` (or `'30min'`, `'1D'`) explicitly to average. `start` and
    `end` are also optional now (previously both were required); omit them to
    read the files' full coverage.

## Basic Usage

```python
from pathlib import Path
from AeroViz import RawDataReader

# Minimal: read the files' full coverage at native resolution
data = RawDataReader(
    instrument='AE33',           # Instrument type
    path=Path('/path/to/data'),  # Data path
)
```

```python
from datetime import datetime

# Bounded range with hourly averaging
data = RawDataReader(
    instrument='AE33',
    path=Path('/path/to/data'),
    start=datetime(2024, 1, 1),  # optional start time
    end=datetime(2024, 12, 31),  # optional end time
    mean_freq='1h'               # optional — resample to hourly means
)
```

## Parameter Description

!!! danger "Pass `start` / `end` as keywords"
    The third and fourth *positional* parameters are `reset` and `qc`, not
    `start` and `end`. `RawDataReader('AE33', path, start=start, end=end)` does **not**
    raise — it silently sets `reset=start`, `qc=end` and applies no date
    filter. Always write `start=..., end=...`.

Parameters in signature order:

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `instrument` | str | Instrument name (see [Supported Instruments](#supported-instruments)) | Required |
| `path` | Path / str | Data folder path | Required |
| `reset` | bool / str | `False` use cache; `True` re-read every raw file; `'append'` parse only new files and extend the cache | `False` |
| `qc` | bool / str | `True` apply QC; `False` return the parsed (L1) frame — no masking, no `outlier.json`, no report (`mean_freq` is still honoured); a pandas offset (`'W'`, `'MS'`, `'2MS'`) also logs rates per period | `True` |
| `start` | datetime / str | Start time; omit to begin at the files' first record | `None` |
| `end` | datetime / str | End time; omit to end at the files' last record | `None` |
| `mean_freq` | str | Averaging frequency (`'1h'`, `'30min'`, `'1D'`); omit for native resolution | `None` (no resampling) |
| `size_range` | tuple | SMPS only (accepted but ignored by APS / GRIMM): `(first_bin, last_bin)` in nm — a file whose grid does not match **exactly** is rejected, so pass the instrument's real endpoints, e.g. `(11.8, 593.5)` | `None` |
| `append_stats` | bool | SMPS / APS only: append the `psd_stats` columns to the returned frame (the `_stats.csv` sidecar is written regardless) | `False` |
| `fill_missing` | bool | `True` pads output to the requested range; `False` clamps to data coverage | `True` |
| `ignored_status_errors` | list | Status codes / tokens / bits that should **not** count as `Status Error` — see [RawDataReader Reference §3](reader-reference.md#3-how-a-status-judgement-is-made) | `None` |
| `flag_severity` | dict | Reclassify QC rules for this run, `{'Insufficient': 'error'}` / `{'Invalid AAE': 'warning'}` — see [RawDataReader Reference §2](reader-reference.md#severity-not-every-flag-is-fatal) | `None` |
| `output_dir` | Path / str | Where every output file goes | `path/{inst}_outputs/` |
| `output_prefix` | str | File-name prefix for the final CSV and its sidecars | `output_{inst}` |
| `save_pkl` | bool | Write the `_read_*` pickle caches (existing ones are still read) | `True` |
| `save_intermediate_csv` | bool | Write `_read_*_raw.csv` / `_read_*_qc.csv` | `True` |
| `save_report` | bool | Write `report.json` | `True` |
| `quiet` | bool | Suppress console output (the log file is still written) | `False` |
| `log_level` | str | `'DEBUG'` / `'INFO'` / `'WARNING'` / `'ERROR'` for the log file | `'INFO'` |
| `**kwargs` | — | Reader-specific: e.g. SMPS `cpc_max_conc=`, `min_total_conc=`; any reader `raw_freq=` (force the native grid), `drop_outlier_dates=True` | — |

### Optional date range

`start` and `end` are independent. Omit both to read everything the files
contain, or pass just one side to bound only that end:

```python
# Full coverage of the files in the folder
data = RawDataReader('AE33', path)

# Everything from a start date onwards (no upper bound)
data = RawDataReader('AE33', path, start=datetime(2024, 6, 1))

# Everything up to an end date (no lower bound)
data = RawDataReader('AE33', path, end=datetime(2024, 6, 30))
```

### Native resolution (`mean_freq`)

By default no resampling is applied and the data keeps the instrument's native
time resolution (e.g. 1 min, 5 min, 1 h). Pass `mean_freq` only when you want
averaged output:

```python
# Native resolution (default) — no resampling
data = RawDataReader('AE33', path, start=start, end=end)

# Hourly means
hourly = RawDataReader('AE33', path, start=start, end=end, mean_freq='1h')

# 30-minute means
half_hourly = RawDataReader('AE33', path, start=start, end=end, mean_freq='30min')
```

### Reading result metadata (`df.attrs`)

Every result carries provenance and coverage metadata in `df.attrs`. Because the
default `fill_missing=True` pads the frame to the *requested* range (so it may be
mostly NaN), `df.attrs['coverage_*']` is the quickest way to see what the files
**actually** contained:

```python
df = RawDataReader('AE33', path, start='2024-01-01', end='2024-12-31')

df.attrs['coverage_start']   # first row backed by real data
df.attrs['coverage_end']     # last row backed by real data (None if none in range)
df.attrs['requested_start']  # what you asked for (omitted when not given)
df.attrs['n_files']          # how many raw files were read
df.attrs['raw_freq']         # native resolution, auto-detected per file
df.attrs['total_rate']       # overall % valid (only present when qc is on)
```

| Key | When | Meaning |
|-----|------|---------|
| `instrument`, `station`, `source_path`, `n_files` | always | provenance |
| `coverage_start` / `coverage_end` | always | real data span (ignores NaN padding) |
| `requested_start` / `requested_end` | always | the range you passed (omitted when not given) |
| `raw_freq`, `freq_mixed` | always | native frequency + whether files disagreed |
| `fill_missing` | always | grid padded to the request, or clamped to coverage |
| `aeroviz_version`, `processed_at` | always | build / run stamp |
| `mean_freq` | always | output frequency (`None` = native) |
| `qc_applied`, `qc_freq` | qc on | QC mode |
| `acquisition_rate`, `yield_rate`, `total_rate` | qc on | overall rates (%) |

`attrs` survive `to_pickle`/`read_pickle` and `resample` (pandas >= 2) but are
dropped by a `concat` of frames with conflicting attrs — re-stamp if you merge.

### `fill_missing`: pad vs. clamp the time grid

```python
# Default (True): pad the output to the full requested range,
# leaving NaN where the files have no data
padded = RawDataReader('AE33', path, start='2024-01-01', end='2024-12-31')

# False: clamp the grid to the data's actual coverage —
# no leading/trailing NaN rows, no mostly-empty frame from a short file
trimmed = RawDataReader(
    'AE33', path,
    start='2024-01-01', end='2024-12-31',
    fill_missing=False,
)
```

## Supported Instruments

### Black Carbon / Absorption

```python
# AE33 - Magee Scientific 7-wavelength
ae33 = RawDataReader('AE33', path, start=start, end=end)

# AE43 - Real-time black carbon
ae43 = RawDataReader('AE43', path, start=start, end=end)

# BC1054 - MetOne high resolution
bc1054 = RawDataReader('BC1054', path, start=start, end=end)

# MA350 - AethLabs multi-angle
ma350 = RawDataReader('MA350', path, start=start, end=end)
```

### Scattering

```python
# NEPH - TSI integrating nephelometer
neph = RawDataReader('NEPH', path, start=start, end=end)

# Aurora - Ecotech 3-wavelength
aurora = RawDataReader('Aurora', path, start=start, end=end)
```

### Size Distribution

```python
# SMPS - Scanning Mobility Particle Sizer
smps = RawDataReader('SMPS', path, start=start, end=end, size_range=(11.8, 593.5))

# APS - Aerodynamic Particle Sizer
aps = RawDataReader('APS', path, start=start, end=end)

# GRIMM - Optical Particle Sizer
grimm = RawDataReader('GRIMM', path, start=start, end=end)
```

### Chemical Composition

```python
# IGAC - Ion Chromatograph
igac = RawDataReader('IGAC', path, start=start, end=end)

# OCEC - Organic Carbon/Elemental Carbon Analyzer
ocec = RawDataReader('OCEC', path, start=start, end=end)

# Xact - Xact 625i XRF Analyzer
xact = RawDataReader('Xact', path, start=start, end=end)
```

### External / Pre-aggregated

```python
# EPA - Taiwan EPA hourly station export (big5 CSV, one station per file)
epa = RawDataReader('EPA', path, start=start, end=end)
```

!!! note "Not readable through `RawDataReader`"
    `VOC` and `Minion` were **removed** in v0.4.0 — `RawDataReader('VOC', ...)`
    raises `KeyError`. They are pre-aggregated exports with no raw log to
    parse: read them with pandas and go straight to the analysis functions
    (see [VOC Analysis](voc_analysis.md)). `Q-ACSM` is registered but has no
    reader yet and raises `NotImplementedError`.

## Quality Control

### QC Report

```python
# Monthly QC report
data = RawDataReader(
    instrument='AE33',
    path=path,
    start=start,
    end=end,
    qc='1MS'  # Monthly report
)
```

Output example:
```
Period: 2024-01-01 ~ 2024-01-31
  Acquisition Rate : 100.0% (744/744 periods with data)
  Yield Rate       :  99.5% (740/744 periods passed QC)
  Total Rate       :  99.5% (740/744 valid periods)
```

The per-period block goes to the log only; `report.json` always carries a
weekly and a monthly breakdown regardless of `qc`, and the overall rates land
in `df.attrs`.

### Force Re-read

```python
# Ignore cache, re-read raw files
data = RawDataReader(
    instrument='AE33',
    path=path,
    reset=True
)
```

## Output Files

After processing, files are generated in `{inst}_outputs/` next to the raw
data (lower-case instrument name, e.g. `ae33_outputs/`; override with
`output_dir=`):

| File | Level | Description |
|------|:-----:|-------------|
| `_read_{inst}_raw.pkl` / `.csv` | L1 | Parsed measurement, every source column, native grid — the cache |
| `_read_{inst}_qc.pkl` / `.csv` | L2 | Same frame plus `QC_Flag` / `QC_Invalid` — the only place flag and value sit side by side |
| `output_{inst}.csv` | L3 | What the call returns: requested range, invalid rows NaN, resampled to `mean_freq` |
| `output_{inst}_dNdlogDp.csv` / `_dSdlogDp.csv` / `_dVdlogDp.csv` / `_stats.csv` | L3 | SMPS / APS only: the three weightings and the `psd_stats` statistics |
| `report.json` | L3 | Acquisition / yield / total rates per period plus an up/down timeline |
| `{inst}.log` | — | Processing log: parse warnings, dropped files, QC summary |

`output_prefix=` renames the `output_{inst}` stem (and the sidecars with it);
`save_pkl=False`, `save_intermediate_csv=False`, `save_report=False` switch the
respective files off. See [Data Levels (L0–L3)](data-levels.md) for what each
level may contain.

## Advanced Usage

### Pin the SMPS size grid

`size_range` is an *exact-match* guard, not a filter: a file whose first and
last bins are not precisely these values is skipped (and named in the log).
Use it to keep a folder that mixes instrument configurations on one grid.

```python
smps = RawDataReader(
    instrument='SMPS',
    path=path,
    start=start,
    end=end,
    size_range=(11.8, 593.5)  # nm — the grid's real endpoints
)
```

Without it, a mismatching grid only warns, and `_partition_compatible_scans`
keeps the dominant grid automatically.

### Multi-instrument Integration

```python
# Read multiple instruments
ae33 = RawDataReader('AE33', path_ae33, start=start, end=end)
neph = RawDataReader('NEPH', path_neph, start=start, end=end)
smps = RawDataReader('SMPS', path_smps, start=start, end=end)

# Merge using pandas
import pandas as pd
combined = pd.concat([ae33, neph, smps], axis=1)
```

## Common Issues

### Data Path Format

```python
# Correct
path = Path('/Users/name/data/AE33')

# Also works
path = Path('./data/AE33')
```

### Time Format

```python
from datetime import datetime

# Correct
start = datetime(2024, 1, 1)
end = datetime(2024, 12, 31)

# Can also specify hours, minutes, seconds
start = datetime(2024, 1, 1, 0, 0, 0)
end = datetime(2024, 12, 31, 23, 59, 59)
```

### `KeyError: Instrument name '...' is not valid`

The instrument key is not recognised. Check the exact spelling against the
[supported list](../api/instruments/index.md) (note the hyphen in `Q-ACSM`).
`VOC` and `Minion` raise a different `KeyError` on purpose — they were removed
from the reader; `Q-ACSM` raises `NotImplementedError`.

### `size_range` raised an error

`size_range` is only accepted for `SMPS`, `APS` and `GRIMM` (anything else
raises `ValueError`), and the values are validated: SMPS within 1–1000 nm, APS
within 500–20 000 nm. For SMPS it is an *exact-match* guard on the file's first
and last bin — see [Pin the SMPS size grid](#pin-the-smps-size-grid) — so a
range that passes validation but does not match the grid rejects every file and
the read fails with "All files were either empty or failed to read". APS and
GRIMM accept the argument but do not act on it.

### My SMPS / APS frame has no `total_num` (or other statistic) columns

That is intentional: the reader returns the dN/dlogDp matrix (diameters as
columns). Derive statistics with `psd_stats(df)['other']`, read the
`_stats.csv` sidecar written next to the output, or pass `append_stats=True` —
see [Size Distribution](size_distribution.md#common-issues) before you do.

### The frame is huge and mostly NaN

With `fill_missing=True` (default) the grid is padded to the full requested
`[start, end]`. Use `df.attrs['coverage_start'] / ['coverage_end']` to see what
the files actually contained, or pass `fill_missing=False` to clamp the grid to
real coverage — see [`fill_missing`](#fill_missing-pad-vs-clamp-the-time-grid).

### Insufficient Memory

For large datasets, read in segments:

```python
# Read by month. A midnight `end` is promoted to 23:59:59 of that day, so
# step back one second from the next month's first day to avoid overlap.
from datetime import timedelta

for month in range(1, 13):
    start = datetime(2024, month, 1)
    nxt = datetime(2025, 1, 1) if month == 12 else datetime(2024, month + 1, 1)
    data = RawDataReader('AE33', path, start=start, end=nxt - timedelta(seconds=1))
    # Process...
```

## Related Topics

- [API Reference](../api/RawDataReader/index.md)
- [Supported Instruments List](../api/instruments/index.md)
