## <div align="center">AeroViz for Aerosol Science Visualization</div>

<div align="center">

![Python](https://img.shields.io/pypi/pyversions/aeroviz?logo=python)
![PyPI](https://img.shields.io/pypi/v/aeroviz?logo=pypi)
![Pytest](https://img.shields.io/github/actions/workflow/status/Alex870521/aeroviz/pytest.yml?logo=pytest&label=pytest)
![GitHub last commit](https://img.shields.io/github/last-commit/Alex870521/aeroviz?logo=github)
[![Material for MkDocs](https://img.shields.io/badge/Material%20for%20MkDocs-deployed-blue?logo=materialformkdocs)](https://alex870521.github.io/AeroViz/)
</div>

## <div align="center">Installation</div>

```bash
pip install AeroViz
```

## <div align="center">Key Features</div>

### 📊 Data Reading ▶ RawDataReader

Built-in `RawDataReader` supporting multiple aerosol instruments:

- **Particle Sizers**: SMPS, APS, GRIMM, OPC
- **Mass**: TEOM, BAM1020
- **Optical**: NEPH, Aurora, AE33/43, BC1054
- **Chemical Analysis**: OCEC, IGAC, XRF, VOC

> Features include quality control, data filtering, flexible resampling, and CSV export. For detailed instrument support
> and usage, check our [RawDataReader API](https://alex870521.github.io/AeroViz/api/RawDataReader/).

### 🔬 Data Processing ▶ DataProcess

Built-in `DataProcess` provides advanced aerosol analysis with specialized modules:

- **SizeDistr**: Size distribution processing, SMPS-APS merge, mode statistics, lung deposition (ICRP 66)
- **Optical**: Mie theory, IMPROVE extinction, RI retrieval, derived optical parameters
- **Chemistry**: Mass reconstruction, volume/RI calculation, kappa, partition ratios
- **VOC**: OFP, SOAP, MIR calculations

### 📈 Data Visualization ▶ plot

Comprehensive visualization tools `plot`:

- **Time Analysis**: Trends, Diurnal Patterns
- **Statistical**: Distributions, Correlations
- **Specialized**: Size Contours, Wind Rose, Polar Plots, Hysplit, CBPF

> **Note:** We are continuously adding support for more instruments and features. Contributions are welcome!

## <div align="center">Quick Start</div>

```python
from datetime import datetime
from pathlib import Path
from AeroViz import RawDataReader, DataProcess, plot

# Read data from a supported instrument
data = RawDataReader(
    instrument='NEPH',
    path=Path('/path/to/data'),
    start=datetime(2024, 2, 1),
    end=datetime(2024, 4, 30)
)
```

```pycon
> Console output
╔════════════════════════════════════════════════════════════════════════════════╗
║     Reading NEPH RAW DATA from 2024-02-01 00:00:00 to 2024-04-30 23:59:59      ║
╚════════════════════════════════════════════════════════════════════════════════╝
▶ Reading NEPH files ━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 file_name.dat
		▶ Scatter Coe. (550 nm)
			├─ Sample Rate    :   100.0%
			├─ Valid  Rate    :   100.0%
			└─ Total  Rate    :   100.0%
```

For more detailed usage instructions, please refer to our [User Guide](docs/guide).

## <div align="center">Documentation</div>

For detailed documentation, please refer to the `docs` folder, or
*[GitHub Pages](https://alex870521.github.io/AeroViz/).*


<div align="center">

| Documentation                  | Description              |
|--------------------------------|--------------------------|
| [User Guide](docs/guide)       | Basic usage instructions |
| [Changelog](docs/CHANGELOG.md) | List of changes          |

</div>

## <div align="center">Contributors</div>

<div align="center">
    <a href="https://github.com/Alex870521">
        <img src="https://github.com/Alex870521.png" width="40" height="40" alt="Alex870521" style="border-radius: 50%; object-fit: cover; margin: 0 5px;">
    </a>
    <a href="https://github.com/yrr-Su">
        <img src="https://github.com/yrr-Su.png" width="40" height="40" alt="yrr-Su" style="border-radius: 50%; object-fit: cover; margin: 0 5px;">
    </a>
    <a href="https://github.com/Masbear">
        <img src="https://github.com/Masbear.png" width="40" height="40" alt="Masbear" style="border-radius: 50%; object-fit: cover; margin: 0 5px;">
    </a>
</div>

## <div align="center">Contact</div>

For bug reports and feature requests please visit [GitHub Issues](https://github.com/Alex870521/AeroViz/issues).
