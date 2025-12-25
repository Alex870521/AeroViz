# Xact 625i XRF Analyzer

The Xact 625i is a continuous X-ray fluorescence (XRF) analyzer for real-time elemental analysis of particulate matter.

## Instrument Overview

| Specification | Value |
|---------------|-------|
| Manufacturer | Cooper Environmental Services |
| Model | Xact 625i |
| Measurement | Elemental composition (ng/m3) |
| Time Resolution | Hourly |
| Elements | 72 elements (Mg to U) |

## Data Format

- **File format**: CSV
- **Time format**: `MM/DD/YYYY HH:MM:SS`
- **Data structure**: Element concentrations with uncertainties + environmental parameters

### Column Structure

The raw data file contains:

1. **Element concentrations**: `Element AtomicNumber (ng/m3)` (e.g., `Mg 12 (ng/m3)`)
2. **Uncertainties**: `Element Uncert (ng/m3)` (e.g., `Mg uncert (ng/m3)`)
3. **Environmental parameters**: Temperature, pressure, flow, RH, etc.
4. **Alarm codes**: Instrument status indicators

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

## Quality Control

### QC Rules Applied

| Rule | Condition | Description |
|------|-----------|-------------|
| Instrument Error | ALARM code 100-110 | Instrument malfunction detected |
| Upscale Warning | ALARM code 200-203 | Concentration exceeds measurement range |
| Invalid Value | < 0 or > 100,000 ng/m3 | Concentration outside valid range |
| High Uncertainty | Uncertainty > 50% of value | Measurement reliability concern |

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

## Output Data

### Element Columns

Each detected element has two columns:
- `Element` - Concentration in ng/m3 (e.g., `Pb`, `Fe`, `S`)
- `Element_uncert` - Measurement uncertainty in ng/m3

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

## API Reference

::: AeroViz.rawDataReader.script.Xact.Reader
    options:
      show_root_heading: true
      heading_level: 3
