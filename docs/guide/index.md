# User Guide

Welcome to AeroViz! This guide will help you get started quickly.

## Installation

```bash
pip install "AeroViz[plot]"      # drop [plot] if you only read and process data
```

Python 3.10+; wheels for Linux, macOS and Windows. Extras, building from
source and common install problems: [Installation](../installation.md).

---

## Quick Start

### 1. Reading Data

```python
from datetime import datetime
from pathlib import Path
from AeroViz import RawDataReader

# Read AE33 black carbon data
data = RawDataReader(
    instrument='AE33',
    path=Path('/path/to/data'),
    start=datetime(2024, 1, 1),
    end=datetime(2024, 12, 31),
    mean_freq='1h'
)

# View data
print(data.head())
print(data.columns)
```

### 2. Data Processing

```python
from AeroViz import psd_stats, reconstruct_mass

# Size distribution processing
result = psd_stats(df_pnsd)

# Chemical composition processing
result = reconstruct_mass(df_chem)
```

### 3. Visualization

```python
from AeroViz import plot

# Time series plot (y = column name or list of columns)
plot.timeseries(data, y='BC')

# Scatter plot (x / y are column names)
plot.scatter(data, x='BC', y='PM25')
```

---

## Core Concepts

### RawDataReader

A unified data reading interface supporting multiple aerosol instruments:

| Category | Instruments |
|----------|-------------|
| Black Carbon | AE33, AE43, BC1054, MA350 |
| Scattering | NEPH, Aurora |
| Size Distribution | SMPS, APS, GRIMM |
| Chemical | IGAC, OCEC, Xact |
| Mass | TEOM, BAM1020 |
| External / reference | EPA (Taiwan EPA hourly export) |

`Q-ACSM` is registered but its reader is not implemented yet. `VOC` and
`Minion` are **not** readable through `RawDataReader` (removed in v0.4.0):
read them with pandas and go straight to the analysis functions.

See [RawDataReader Usage](rawdatareader.md)

### Post-Processing Functions

Top-level functions organized into four namespaces:

| Namespace | Function |
|-----------|----------|
| `size` | Size distribution processing, merging, conversion |
| `chemistry` | Mass reconstruction, ion balance, kappa calculation |
| `optical` | Mie calculation, IMPROVE, RI retrieval |
| `voc` | OFP, SOAP calculation |

See [Post-Processing Functions Tutorial](dataprocess.md)

### Plot

The visualization module provides various chart types:

- Basic charts: scatter, bar, box, violin, pie
- Time analysis: timeseries, timeseries_interactive, diurnal_pattern
- Advanced charts: contour, corr_matrix, meteorology.wind_rose, meteorology.CBPF

See [Visualization Tutorial](visualization.md)

---

## Examples

| Example | Description |
|---------|-------------|
| [RawDataReader Usage](rawdatareader.md) | Reading each instrument, date range, resampling, QC report, output files |
| [Size Distribution Analysis](size_distribution.md) | SMPS-APS merging, distribution conversion, statistical calculation |
| [Optical Closure Analysis](optical_closure.md) | Mie calculation, IMPROVE, refractive index retrieval |
| [Chemical Composition Analysis](chemical_analysis.md) | Mass reconstruction, ion balance, kappa calculation |
| [VOC Analysis](voc_analysis.md) | OFP, SOAP calculation |

---

## Next Steps

- Read the [Theoretical Background](../theory/index.md) to understand calculation principles
- Refer to the [API Documentation](../api/index.md) for detailed parameters
