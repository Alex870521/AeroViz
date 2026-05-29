# RawDataReader Tutorial

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

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `instrument` | str | Instrument name | Required |
| `path` | Path | Data folder path | Required |
| `start` | datetime | Start time (optional) | `None` (files' first record) |
| `end` | datetime | End time (optional) | `None` (files' last record) |
| `mean_freq` | str | Averaging frequency ('1h', '30min', '1D'); omit for native resolution | `None` (no resampling) |
| `fill_missing` | bool | `True` pads output to the requested range; `False` clamps to data coverage | `True` |
| `reset` | bool | Force re-read (ignore cache) | `False` |
| `qc` | bool/str | Quality control on/off, or QC report frequency ('1MS', '1D') | `True` |

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
data = RawDataReader('AE33', path, start, end)

# Hourly means
hourly = RawDataReader('AE33', path, start, end, mean_freq='1h')

# 30-minute means
half_hourly = RawDataReader('AE33', path, start, end, mean_freq='30min')
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
| `mean_freq`, `qc_applied`, `qc_freq` | qc on | output frequency + QC mode |
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
ae33 = RawDataReader('AE33', path, start, end)

# AE43 - Real-time black carbon
ae43 = RawDataReader('AE43', path, start, end)

# BC1054 - MetOne high resolution
bc1054 = RawDataReader('BC1054', path, start, end)

# MA350 - AethLabs multi-angle
ma350 = RawDataReader('MA350', path, start, end)
```

### Scattering

```python
# NEPH - TSI integrating nephelometer
neph = RawDataReader('NEPH', path, start, end)

# Aurora - Ecotech 3-wavelength
aurora = RawDataReader('Aurora', path, start, end)
```

### Size Distribution

```python
# SMPS - Scanning Mobility Particle Sizer
smps = RawDataReader('SMPS', path, start, end, size_range=(11.8, 593.5))

# APS - Aerodynamic Particle Sizer
aps = RawDataReader('APS', path, start, end)

# GRIMM - Optical Particle Sizer
grimm = RawDataReader('GRIMM', path, start, end)
```

### Chemical Composition

```python
# IGAC - Ion Chromatograph
igac = RawDataReader('IGAC', path, start, end)

# OCEC - Organic Carbon/Elemental Carbon Analyzer
ocec = RawDataReader('OCEC', path, start, end)

# Xact - Xact 625i XRF Analyzer
xact = RawDataReader('Xact', path, start, end)

# VOC - Volatile Organic Compounds Monitor
# (deprecated — read VOC CSVs with pandas and pass to voc_potentials; see VOC docs)
voc = RawDataReader('VOC', path, start, end)
```

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
> Processing: 2024-01-01 to 2024-01-31
    > BC Mass Conc. (880 nm)
        +-- Sample Rate    :  100.0%
        +-- Valid  Rate    :   99.5%
        +-- Total  Rate    :   99.5%
```

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

After processing, files are generated in `{instrument}_outputs/`:

| File | Description |
|------|-------------|
| `_read_{inst}_raw.csv` | Merged raw data |
| `_read_{inst}_raw.pkl` | Raw data (pickle) |
| `_read_{inst}.csv` | QC processed data |
| `_read_{inst}.pkl` | QC data (pickle) |
| `Output_{inst}` | Final processed data |
| `{inst}.log` | Processing log |

## Advanced Usage

### Specify Size Range (SMPS/APS)

```python
smps = RawDataReader(
    instrument='SMPS',
    path=path,
    start=start,
    end=end,
    size_range=(10, 500)  # nm
)
```

### Multi-instrument Integration

```python
# Read multiple instruments
ae33 = RawDataReader('AE33', path_ae33, start, end)
neph = RawDataReader('NEPH', path_neph, start, end)
smps = RawDataReader('SMPS', path_smps, start, end)

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

### Insufficient Memory

For large datasets, read in segments:

```python
# Read by month
for month in range(1, 13):
    start = datetime(2024, month, 1)
    end = datetime(2024, month + 1, 1) if month < 12 else datetime(2025, 1, 1)
    data = RawDataReader('AE33', path, start, end)
    # Process...
```

## Related Topics

- [API Reference](../api/RawDataReader/index.md)
- [Supported Instruments List](../api/instruments/index.md)
