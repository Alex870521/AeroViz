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

Pre-built wheels are published for Linux, macOS (Apple Silicon) and Windows, so
a normal install needs no compiler. Building **from source** — including an
editable `pip install -e .` for development, or any platform without a wheel —
compiles the bundled ISORROPIA II Fortran extension and therefore requires a
Fortran compiler (`gfortran`) plus `meson`/`ninja`:

```bash
# macOS:          brew install gcc
# Debian/Ubuntu:  sudo apt-get install gfortran
# Windows:        use the MSYS2 / mingw-w64 toolchain
pip install -e ".[test]"
```

## Quick Start

```python
from AeroViz import RawDataReader

# Read AE33 Aethalometer data (black carbon)
df = RawDataReader(
    instrument='AE33',
    path='/path/to/data',
    start='2024-01-01',  # optional — omit to read the files' full coverage
    end='2024-12-31',    # optional
    mean_freq='1h',      # optional — '1h' resamples to hourly; omit for native resolution
    qc=True              # Apply quality control
)

# Output: DataFrame with columns like BC1-BC7, abs_370-abs_950, AAE, eBC
print(df[['eBC', 'AAE']].describe())

# Read everything the files contain, at native resolution (no date range, no resample)
df_all = RawDataReader('AE33', '/path/to/data')
print(df_all.attrs['coverage_start'], '→', df_all.attrs['coverage_end'])
```

> [!IMPORTANT]
> **Behaviour change:** `mean_freq` no longer defaults to `'1h'`. The default is
> now **no resampling** — data is returned at its native resolution. Pass
> `mean_freq='1h'` (or `'30min'`, `'1D'`) explicitly if you want averaging.
> `start` / `end` are also optional now (previously required).

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
| `start` | str/datetime | Start date (`'2024-01-01'` or `datetime`); omit to start at the files' first record | `None` (optional) |
| `end` | str/datetime | End date; omit to end at the files' last record | `None` (optional) |
| `mean_freq` | str | Output frequency: `'1h'`, `'30min'`, `'1D'`. Omit for native resolution (no resampling) | `None` (no resample) |
| `qc` | bool/str | Quality control: `True`, `False`, or `'MS'` for monthly stats | `True` |
| `reset` | bool/str | `True` to reprocess, `'append'` to add new data | `False` |
| `size_range` | tuple | Size range in nm for SMPS/APS: `(min, max)` | `None` |
| `fill_missing` | bool | `True` pads the output to the requested `[start, end]` range; `False` clamps the grid to the data's actual coverage (no NaN blow-up) | `True` |

> `start`, `end`, and `mean_freq` are all optional. Omit `start`/`end` to read
> the files' full coverage (pass just one side to bound only that end), and omit
> `mean_freq` to keep the native resolution.

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

## Reader Metadata (`df.attrs`)

Every `RawDataReader` result carries provenance and coverage metadata in
`df.attrs`. With the default `fill_missing=True` the frame is padded to the
*requested* range and can be mostly NaN, so `df.attrs['coverage_*']` is the
quickest way to learn what the files **actually** contained:

```python
df = RawDataReader('AE33', '/data/AE33', start='2024-01-01', end='2024-12-31')

df.attrs['coverage_start']   # first row backed by real data
df.attrs['coverage_end']     # last row backed by real data (None if none in range)
df.attrs['requested_start']  # what you asked for (omitted when not given)
df.attrs['n_files']          # how many raw files were read
df.attrs['raw_freq']         # native resolution, auto-detected per file
df.attrs['total_rate']       # overall % valid (only when qc is on)
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

### `fill_missing`: pad vs. clamp

```python
# Default: pad the output to the full requested range (NaN where files have gaps)
padded = RawDataReader('AE33', '/data/AE33', start='2024-01-01', end='2024-12-31')

# Clamp the grid to the data's actual coverage — no leading/trailing NaN rows
trimmed = RawDataReader(
    'AE33', '/data/AE33',
    start='2024-01-01', end='2024-12-31',
    fill_missing=False,
)
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

Quick interactive look at a reader result (Plotly) — one trace per column, click
the legend to toggle which columns are shown:

```python
from AeroViz import RawDataReader
from AeroViz.plot import timeseries_interactive

df = RawDataReader('AE33', '/data/AE33')              # native resolution, full coverage
timeseries_interactive(df, columns=['eBC', 'BC1', 'BC6', 'AAE'])
timeseries_interactive(df, save='ae33.html', show=False)   # export standalone HTML
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

### Development setup

AeroViz builds a native Fortran extension, so an editable install needs
`gfortran` (see [Installation](#installation)) in addition to the Python tools:

```bash
pip install -e ".[test,dev]"
pytest
```

### Commits & releases

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/)
(`type(scope): subject`, e.g. `fix(reader): ...`). Releases are cut with
[Commitizen](https://commitizen-tools.github.io/commitizen/), which derives the
next version from the commit history, updates `docs/CHANGELOG.md`, and tags
`vX.Y.Z` — run the **Bump version** workflow (or `cz bump` locally). Pushing the
tag triggers the Release workflow, which builds and publishes the wheels.

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
