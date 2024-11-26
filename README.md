## <div align="center">AeroViz for Aerosol Science Visualization</div>

<div align="center">

![Python](https://img.shields.io/pypi/pyversions/aeroviz?logo=python)
![PyPI](https://img.shields.io/pypi/v/aeroviz?logo=pypi)
![Pytest](https://img.shields.io/github/actions/workflow/status/Alex870521/aeroviz/pytest.yml?logo=pytest&label=pytest)
![GitHub last commit](https://img.shields.io/github/last-commit/Alex870521/aeroviz?logo=github)

</div>

<div align="center">

<a href="https://github.com/Alex870521"><img src="https://github.com/Alex870521/AeroViz/blob/main/assets/media/logo-social-github.png?raw=true" width="3%" alt="Alex870521 GitHub"></a>
<img src="https://github.com/Alex870521/AeroViz/blob/main/assets/media/logo-transparent.png?raw=true" width="3%">
<a href="https://www.linkedin.com/in/Alex870521/"><img src="https://github.com/Alex870521/AeroViz/blob/main/assets/media/logo-social-linkedin.png?raw=true" width="3%" alt="Alex870521 LinkedIn"></a>
<img src="https://github.com/Alex870521/AeroViz/blob/main/assets/media/logo-transparent.png?raw=true" width="3%">
<a href="https://medium.com/@alex870521"><img src="https://github.com/Alex870521/AeroViz/blob/main/assets/media/logo-social-medium.png?raw=true" width="3%" alt="Alex870521 Medium"></a>
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
> and usage, check our [RawDataReader Guide](docs/guide/RawDataReader.md).

### 🔬 Data Processing ▶ DataProcess

Built-in `DataProcess` provides advanced aerosol analysis:
- **Size Distribution**: Mode Fitting, Log-Normal Analysis
- **Optical Properties**: Mie Theory, IMPROVE
- **Chemical**: Mass Closure, Source Apportionment
- **VOC**: OFP, SOAP

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
    instrument='Neph',
    path=Path('/path/to/data'),
    start=datetime(2024, 2, 1),
    end=datetime(2024, 4, 30)
)
```

```pycon
> Concole output
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
For detailed documentation, please refer to the `docs` folder, which includes:

<div align="center">

| Documentation                  | Description              |
|--------------------------------|--------------------------|
| [User Guide](docs/guide)       | Basic usage instructions |
| [Changelog](docs/CHANGELOG.md) | List of changes          |
</div>

## <div align="center">Contact</div>
For bug reports and feature requests please visit [GitHub Issues](https://github.com/Alex870521/DataPlot/issues).
