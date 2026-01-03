<div align="center">

# AeroViz

**Aerosol Data Processing and Visualization Toolkit for Atmospheric Research**

[![Python](https://img.shields.io/pypi/pyversions/aeroviz?logo=python)](https://pypi.org/project/aeroviz/)
[![PyPI](https://img.shields.io/pypi/v/aeroviz?logo=pypi)](https://pypi.org/project/aeroviz/)
[![Pytest](https://img.shields.io/github/actions/workflow/status/Alex870521/aeroviz/pytest.yml?logo=pytest&label=pytest)](https://github.com/Alex870521/AeroViz/actions)
[![Documentation](https://img.shields.io/badge/docs-MkDocs-blue?logo=materialformkdocs)](https://alex870521.github.io/AeroViz/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

</div>

AeroViz is a Python toolkit for reading, processing, and visualizing aerosol measurement data. It supports 18+ atmospheric instruments with built-in quality control, data processing, and publication-ready visualizations.

## Installation

```bash
pip install AeroViz
```

## Quick Start

```python
from AeroViz import RawDataReader

# Read AE33 Aethalometer data (black carbon)
df = RawDataReader(
    instrument='AE33',
    path='/path/to/data',
    start='2024-01-01',
    end='2024-12-31',
    mean_freq='1h',  # Hourly averages
    qc=True          # Apply quality control
)

# Output: DataFrame with columns like BC1-BC7, abs_370-abs_950, AAE, eBC
print(df[['eBC', 'AAE']].describe())
```

## Supported Instruments

### Black Carbon Monitors

| Instrument | Description | Output Columns |
|------------|-------------|----------------|
| **AE33** | Magee Aethalometer (7-wavelength) | `BC1`-`BC7`, `abs_370`-`abs_950`, `AAE`, `eBC` |
| **AE43** | Magee Aethalometer (7-wavelength) | `BC1`-`BC7`, `abs_370`-`abs_950`, `AAE`, `eBC` |
| **BC1054** | Met One Black Carbon Monitor | `BC`, `abs_880` |
| **MA350** | AethLabs microAeth (5-wavelength) | `BC1`-`BC5`, `abs_375`-`abs_880` |

```python
# Example: Read black carbon data
bc = RawDataReader('AE33', '/data/AE33', '2024-01-01', '2024-06-30')
print(f"Mean eBC: {bc['eBC'].mean():.2f} ng/m³")
print(f"Mean AAE: {-bc['AAE'].mean():.2f}")  # AAE stored as negative
```

### Particle Sizers

| Instrument | Description | Size Range | Output Columns |
|------------|-------------|------------|----------------|
| **SMPS** | Scanning Mobility Particle Sizer | 10-1000 nm | Size bins, `total_num`, `GMD_num`, `GSD_num` |
| **APS** | Aerodynamic Particle Sizer | 0.5-20 μm | Size bins, `total_num`, `GMD_num`, `GSD_num` |
| **GRIMM** | Optical Particle Counter | 0.25-32 μm | Size bins, number concentrations |

```python
# Example: Read SMPS size distribution
smps = RawDataReader(
    'SMPS', '/data/SMPS', '2024-01-01', '2024-06-30',
    size_range=(10, 500)  # Filter to 10-500 nm
)
print(f"Total number: {smps['total_num'].mean():.0f} #/cm³")
print(f"GMD: {smps['GMD_num'].mean():.1f} nm")
```

### Mass Concentration

| Instrument | Description | Output Columns |
|------------|-------------|----------------|
| **TEOM** | Tapered Element Oscillating Microbalance | `PM_NV`, `PM_Total`, `Volatile_Fraction` |
| **BAM1020** | Beta Attenuation Monitor | `PM2.5`, `PM10` |

```python
# Example: Read TEOM PM mass data
teom = RawDataReader('TEOM', '/data/TEOM', '2024-01-01', '2024-06-30')
print(f"PM2.5 (non-volatile): {teom['PM_NV'].mean():.1f} μg/m³")
print(f"PM2.5 (total): {teom['PM_Total'].mean():.1f} μg/m³")
```

### Optical Instruments

| Instrument | Description | Output Columns |
|------------|-------------|----------------|
| **NEPH** | TSI Nephelometer | `scattering_B`, `scattering_G`, `scattering_R`, `SAE` |
| **Aurora** | Ecotech Aurora 3000 | `scattering_B`, `scattering_G`, `scattering_R`, `SAE` |

```python
# Example: Read nephelometer scattering data
neph = RawDataReader('Aurora', '/data/Aurora', '2024-01-01', '2024-06-30')
print(f"Scattering (550nm): {neph['scattering_G'].mean():.1f} Mm⁻¹")
```

### Chemical Composition

| Instrument | Description | Output Columns |
|------------|-------------|----------------|
| **Xact** | Cooper XRF Heavy Metals | `Fe`, `Zn`, `Pb`, `Cu`, `Mn`, `Cr`, `Ni`, `As`, `Cd`, ... |
| **OCEC** | Sunset OC/EC Analyzer | `OC`, `EC`, `TC`, `OC1`-`OC4`, `EC1`-`EC3` |
| **IGAC** | Ion Chromatograph | `SO4²⁻`, `NO3⁻`, `Cl⁻`, `NH4⁺`, `Na⁺`, `K⁺`, ... |
| **Q-ACSM** | Aerosol Chemical Speciation Monitor | `Org`, `SO4`, `NO3`, `NH4`, `Chl` |

```python
# Example: Read XRF heavy metals data
xrf = RawDataReader('Xact', '/data/Xact', '2024-01-01', '2024-06-30')
print(f"Fe: {xrf['Fe'].mean():.1f} ng/m³")
print(f"Pb: {xrf['Pb'].mean():.2f} ng/m³")
```

### Other Instruments

| Instrument | Description |
|------------|-------------|
| **VOC** | Volatile Organic Compounds Analyzer |
| **EPA** | Taiwan EPA Air Quality Data |
| **Minion** | Low-cost Sensor Network |

## Key Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `instrument` | str | Instrument name (see tables above) | Required |
| `path` | str/Path | Directory containing raw data files | Required |
| `start` | str/datetime | Start date (`'2024-01-01'` or `datetime`) | Required |
| `end` | str/datetime | End date | Required |
| `mean_freq` | str | Output frequency: `'1h'`, `'30min'`, `'1D'` | `'1h'` |
| `qc` | bool/str | Quality control: `True`, `False`, or `'MS'` for monthly stats | `True` |
| `reset` | bool/str | `True` to reprocess, `'append'` to add new data | `False` |
| `size_range` | tuple | Size range in nm for SMPS/APS: `(min, max)` | `None` |

## Quality Control

AeroViz applies automatic QC based on instrument-specific rules. The `QC_Flag` column indicates data quality:

| Flag | Description |
|------|-------------|
| `Valid` | Data passed all QC checks |
| `Insufficient` | Not enough raw data points in period |
| `Status Error` | Instrument reported error status |
| `Invalid BC` | Black carbon outside valid range |
| `Invalid Number Conc` | Particle count outside valid range |
| `Spike` | Detected sudden unrealistic change |

```python
# Check data quality
df = RawDataReader('AE33', '/data/AE33', '2024-01-01', '2024-06-30')
print(df['QC_Flag'].value_counts())
# Valid          8000
# Insufficient    300
# Status Error     60
```

## Data Processing

Advanced analysis with specialized modules:

```python
from AeroViz import DataProcess
from pathlib import Path

# Optical property calculations
optical = DataProcess(method='Optical', path_out=Path('./results'))

# Available methods:
# - 'Chemistry': Mass reconstruction, volume calculation, kappa
# - 'Optical': Mie theory, IMPROVE extinction, RI retrieval
# - 'SizeDistr': SMPS-APS merge, mode fitting, lung deposition
# - 'VOC': OFP, SOAP, MIR calculations
```

## Visualization

Publication-ready plots:

```python
from AeroViz import plot

# Time series, diurnal patterns, wind rose, polar plots, etc.
```

## File Structure

AeroViz expects data organized by station and instrument:

```
/data/
├── Station_Instrument/
│   ├── raw_file_001.dat
│   ├── raw_file_002.dat
│   └── instrument_outputs/    # Auto-generated
│       ├── output_instrument.csv
│       ├── _read_instrument_qc.csv
│       └── report.json
```

## Documentation

- [Full Documentation](https://alex870521.github.io/AeroViz/)
- [API Reference](https://alex870521.github.io/AeroViz/api/RawDataReader/)
- [Changelog](docs/CHANGELOG.md)

## Contributing

Contributions are welcome! Please see our [GitHub Issues](https://github.com/Alex870521/AeroViz/issues) for bug reports and feature requests.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Citation

If you use AeroViz in your research, please cite:

```
AeroViz: Aerosol Data Processing and Visualization Toolkit
https://github.com/Alex870521/AeroViz
```

<div align="center">

## Contributors

<a href="https://github.com/Alex870521"><img src="https://github.com/Alex870521.png" width="40" height="40" alt="Alex870521" style="border-radius: 50%;"></a>
<a href="https://github.com/yrr-Su"><img src="https://github.com/yrr-Su.png" width="40" height="40" alt="yrr-Su" style="border-radius: 50%;"></a>
<a href="https://github.com/Masbear"><img src="https://github.com/Masbear.png" width="40" height="40" alt="Masbear" style="border-radius: 50%;"></a>

</div>
