# RawDataReader Tutorial

RawDataReader is the core data reading component of AeroViz, providing a unified interface for reading various aerosol instrument data.

## Basic Usage

```python
from datetime import datetime
from pathlib import Path
from AeroViz import RawDataReader

data = RawDataReader(
    instrument='AE33',           # Instrument type
    path=Path('/path/to/data'),  # Data path
    start=datetime(2024, 1, 1),  # Start time
    end=datetime(2024, 12, 31),  # End time
    mean_freq='1h'               # Averaging frequency
)
```

## Parameter Description

| Parameter | Type | Description |
|-----------|------|-------------|
| `instrument` | str | Instrument name |
| `path` | Path | Data folder path |
| `start` | datetime | Start time |
| `end` | datetime | End time |
| `mean_freq` | str | Averaging frequency ('1h', '30min', '1D') |
| `reset` | bool | Force re-read (ignore cache) |
| `qc` | str | QC report frequency ('1MS', '1D') |

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
