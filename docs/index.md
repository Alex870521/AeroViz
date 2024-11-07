## <div align="center">AeroViz for Aerosol Science Visualization</div>

<p align="center">

  <img alt="Static Badge" src="https://img.shields.io/badge/python-3.12-blue?logo=python">
  <img alt="Static Badge" src="https://img.shields.io/badge/License-MIT-yellow">
  <img alt="Static Badge" src="https://img.shields.io/badge/github-updating-red?logo=github">
  <img alt="Static Badge" src="https://img.shields.io/badge/testing-green?logo=Pytest&logoColor=blue">

</p>

<div align="center">

<a href="https://github.com/Alex870521"><img src="https://github.com/Alex870521/AeroViz/blob/main/assets/media/logo-social-github.png?raw=true" width="3%" alt="Alex870521 GitHub"></a>
<img src="https://github.com/Alex870521/AeroViz/blob/main/assets/media/logo-transparent.png?raw=true" width="3%">
<a href="https://www.linkedin.com/in/Alex870521/"><img src="https://github.com/Alex870521/AeroViz/blob/main/assets/media/logo-social-linkedin.png?raw=true" width="3%" alt="Alex870521 LinkedIn"></a>
<img src="https://github.com/Alex870521/AeroViz/blob/main/assets/media/logo-transparent.png?raw=true" width="3%">
<a href="https://medium.com/@alex870521"><img src="https://github.com/Alex870521/AeroViz/blob/main/assets/media/logo-social-medium.png?raw=true" width="3%" alt="Alex870521 Medium"></a>

</div>

## <div align="center">Key Features</div>

* Data Reading: Supports reading multiple aerosol data formats.
* Data Visualization: Offers various charts and graphs, including time series plots, distribution plots, and correlation
  matrices.
* Data Processing: Includes multiple data processing tools, such as linear regression and Mie theory calculations.

## <div align="center">Installation</div>

```bash
pip install AeroViz
```

For Windows users: Run `install_windows.bat`

For Linux and Mac users: Run `install_unix.bat`

## <div align="center">Quick Start</div>

```python
from datetime import datetime
from pathlib import Path
from AeroViz import RawDataReader, DataProcess, plot

# Read data from a supported instrument
data = RawDataReader('NEPH', Path('/path/to/data'), start=datetime(2024, 2, 1), end=datetime(2024, 4, 30))

# Create a visualization
plot.timeseries(data, y='scattering_coefficient')
```

For more detailed usage instructions, please refer to our [User Guide]().

## <div align="center"> RawDataReader

RawDataReader supports a wide range of aerosol instruments, including NEPH, SMPS, AE33, and many more. It handles
various file types and time resolutions, making data processing efficient and standardized.

For a detailed list of supported instruments, file types, and data columns, please refer to
our [RawDataReader Usage Guide](docs/guide/RawDataReader) in the `docs` folder.

### Key Features:

- Supports multiple aerosol instruments
- Applies customizable quality control measures
- Offers flexible data filtering and resampling options
- Enables easy data export to CSV format

### Supported Instruments

The AeroViz project currently supports data from the following instruments:

- SMPS (Scanning Mobility Particle Sizer)
- APS (Aerodynamic Particle Sizer)
- GRIMM (GRIMM Aerosol Technik)
- TEOM (Continuous Ambient Particulate Monitor)
- NEPH (Nephelometer)
- Aurora (Nephelometer)
- AE33 (Aethalometer Model 33)
- AE43 (Aethalometer Model 43)
- BC1054 (Black Carbon Monitor 1054)
- MA350 (MicroAeth MA350)
- OCEC (Organic Carbon Elemental Carbon Analyzer)
- IGAC (In-situ Gas and Aerosol Compositions monitor)
- XRF (X-ray Fluorescence Spectrometer)
- VOC (Volatile Organic Compounds Monitor)

> **Note:** We are continuously working to support more instruments. Please check back for updates or contribute to our
> project on GitHub.

## <div align="center">DataProcess</div>

The AeroViz project currently supports the following processing methods:

- **Chemistry**:
- **Optical**
- **SizeDistr**
- **VOC**

## <div align="center">Documentation</div>

For detailed documentation, please refer to the `docs` folder, which includes:

<div align="center">

| Documentation                  | Description              |
|--------------------------------|--------------------------|
| [User Guide](docs/guide)       | Basic usage instructions |
| [Changelog](docs/changelog.md) | List of changes          |

</div>

## <div align="center">Related Source</div>

* #### [PyMieScatt](https://github.com/bsumlin/PyMieScatt.git)
* #### [py-smps](https://github.com/quant-aq/py-smps.git)
* #### [ContainerHandle](https://github.com/yrr-Su/ContainerHandle.git)

## <div align="center">Contact</div>

For bug reports and feature requests please visit [GitHub Issues](https://github.com/Alex870521/DataPlot/issues).

<div align="center">

<a href="https://github.com/Alex870521"><img src="https://github.com/Alex870521/AeroViz/blob/main/assets/media/logo-social-github.png?raw=true" width="3%" alt="Alex870521 GitHub"></a>
<img src="https://github.com/Alex870521/AeroViz/blob/main/assets/media/logo-transparent.png?raw=true" width="3%">
<a href="https://www.linkedin.com/in/Alex870521/"><img src="https://github.com/Alex870521/AeroViz/blob/main/assets/media/logo-social-linkedin.png?raw=true" width="3%" alt="Alex870521 LinkedIn"></a>
<img src="https://github.com/Alex870521/AeroViz/blob/main/assets/media/logo-transparent.png?raw=true" width="3%">
<a href="https://medium.com/@alex870521"><img src="https://github.com/Alex870521/AeroViz/blob/main/assets/media/logo-social-medium.png?raw=true" width="3%" alt="Alex870521 Medium"></a>


</div>