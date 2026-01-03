# AeroViz - AI Usage Guide

AeroViz is an aerosol data processing and visualization toolkit for air quality research.

## Quick Start

```python
from AeroViz import RawDataReader, DataProcess

# Read instrument data with automatic QC
df = RawDataReader(
    instrument='AE33',          # Instrument name
    path='/path/to/data',       # Data directory
    start='2024-01-01',         # Start date
    end='2024-12-31',           # End date
    mean_freq='1h',             # Output frequency
    qc=True                     # Apply quality control
)
```

## Supported Instruments

### Black Carbon Monitors
- **AE33** / **AE43**: Aethalometer - BC at 7 wavelengths (370-950nm)
- **BC1054**: Black carbon monitor
- **MA350**: MicroAeth portable BC monitor

### Size Distribution
- **SMPS**: Scanning Mobility Particle Sizer (10-1000nm)
- **APS**: Aerodynamic Particle Sizer (0.5-20μm)
- **GRIMM**: Optical particle counter

### Mass Concentration
- **TEOM**: Tapered Element Oscillating Microbalance
- **BAM1020**: Beta Attenuation Monitor

### Optical Properties
- **NEPH**: TSI Nephelometer - Scattering coefficients
- **Aurora**: Aurora 3000 - Scattering at RGB wavelengths

### Chemical Composition
- **OCEC**: Sunset OC/EC analyzer
- **Xact**: XRF heavy metals (Fe, Zn, Pb, Cu, Mn, etc.)
- **IGAC**: Ion chromatograph - Water-soluble ions
- **Q-ACSM**: Aerosol Chemical Speciation Monitor
- **VOC**: Volatile organic compounds

### Other
- **EPA**: Taiwan EPA air quality data
- **Minion**: Minion sensor

## Common Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `instrument` | str | Instrument name (see list above) |
| `path` | str/Path | Directory with raw data files |
| `start` | str/datetime | Start date (ISO format) |
| `end` | str/datetime | End date (ISO format) |
| `mean_freq` | str | Averaging frequency: '1h', '30min', '1D' |
| `qc` | bool/str | True=apply QC, 'MS'=monthly stats |
| `reset` | bool/str | True=reprocess, 'append'=add new data |
| `size_range` | tuple | (min_nm, max_nm) for SMPS/APS only |

## Data Processing

```python
from AeroViz import DataProcess

# Create processor for optical calculations
optical = DataProcess(method='Optical', path_out=Path('./results'))

# Available methods: 'Chemistry', 'Optical', 'SizeDistr', 'VOC'
```

## Output Columns by Instrument

### AE33/AE43
- `BC1`-`BC7`: Black carbon at 7 wavelengths (ng/m³)
- `abs_370`-`abs_950`: Absorption coefficients (Mm⁻¹)
- `AAE`: Absorption Ångström Exponent
- `eBC`: Equivalent black carbon

### SMPS/APS
- Size bins (e.g., `11.8`, `13.6`, ... nm for SMPS)
- `total_num`: Total number concentration (#/cm³)
- `total_surf`: Total surface area (μm²/cm³)
- `total_vol`: Total volume (μm³/cm³)
- `GMD_num`, `GSD_num`: Geometric mean diameter and std

### TEOM
- `PM_NV`: Non-volatile PM (μg/m³)
- `PM_Total`: Total PM (μg/m³)
- `Volatile_Fraction`: Volatile fraction (0-1)

### Aurora/NEPH
- `scattering_R`, `scattering_G`, `scattering_B`: Scattering coefficients
- `SAE`: Scattering Ångström Exponent

### Xact
- Element symbols: `Fe`, `Zn`, `Pb`, `Cu`, `Mn`, `Cr`, `Ni`, `As`, `Cd`, etc.
- `{element}_uncert`: Uncertainty values

## QC Flags

Data quality is indicated by `QC_Flag` column:
- `Valid`: Data passed all QC checks
- `Insufficient`: Not enough data points in period
- `Status Error`: Instrument status error
- `Invalid BC` / `Invalid Number Conc`: Out of range values
- `Spike`: Detected sudden value changes

## Example Workflows

### Black Carbon Analysis
```python
from AeroViz import RawDataReader

# Read AE33 data
bc_data = RawDataReader(
    instrument='AE33',
    path='/data/AE33',
    start='2024-01-01',
    end='2024-06-30'
)

# Key columns: BC1-BC7, abs_370-abs_950, AAE, eBC
print(bc_data[['eBC', 'AAE']].describe())
```

### Size Distribution Analysis
```python
# Read SMPS data with size range filter
smps = RawDataReader(
    instrument='SMPS',
    path='/data/SMPS',
    start='2024-01-01',
    end='2024-06-30',
    size_range=(10, 500)  # nm
)

# Total number concentration
print(smps['total_num'].mean())
```

### Heavy Metal Analysis
```python
# Read Xact XRF data
xrf = RawDataReader(
    instrument='Xact',
    path='/data/Xact',
    start='2024-01-01',
    end='2024-06-30'
)

# Common elements: Fe, Zn, Pb, Cu, Mn, Cr, Ni
print(xrf[['Fe', 'Zn', 'Pb']].describe())
```

## File Structure

```
/data/
├── NZ_AE33/           # Station_Instrument format
│   ├── *.dat          # Raw data files
│   └── ae33_outputs/  # Processed outputs
│       ├── output_ae33.csv
│       ├── _read_ae33_qc.csv
│       └── report.json
├── NZ_SMPS/
├── NZ_TEOM/
└── ...
```

## Tips for AI

1. Always specify `start` and `end` dates
2. Use `qc=True` for quality-controlled data
3. Use `reset=True` only when reprocessing is needed
4. Check `QC_Flag` column for data quality
5. Size distribution instruments (SMPS/APS) support `size_range` parameter
