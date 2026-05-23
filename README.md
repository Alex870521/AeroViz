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

Pre-built for Linux, macOS, and Windows — no compiler needed.

## Quick Start

```python
from AeroViz import RawDataReader

df = RawDataReader(
    instrument='AE33',
    path='/path/to/data',
    start='2024-01-01',  # optional — omit to read the files' full coverage
    end='2024-12-31',    # optional
    mean_freq='1h',      # optional — '1h' resamples to hourly; omit for native resolution
    qc=True,             # apply quality control
)
print(df[['eBC', 'AAE']].describe())

# Or read everything the files contain, at native resolution:
df_all = RawDataReader('AE33', '/path/to/data')
print(df_all.attrs['coverage_start'], '→', df_all.attrs['coverage_end'])
```

> [!IMPORTANT]
> **Behaviour change:** `mean_freq` no longer defaults to `'1h'` — the default is
> now **no resampling** (native resolution). Pass `mean_freq='1h'` (or `'30min'`,
> `'1D'`) for averaging. `start` / `end` are also optional now.

## Supported Instruments

| Category | Instruments |
|----------|-------------|
| Black carbon / absorption | AE33, AE43, BC1054, MA350 |
| Particle sizers | SMPS, APS, GRIMM |
| Mass concentration | TEOM, BAM1020 |
| Optical | NEPH, Aurora |
| Chemical composition | Xact, OCEC, IGAC, Q-ACSM |

See the [instrument reference](https://alex870521.github.io/AeroViz/api/instruments/)
for output columns and per-instrument notes.

## Usage

`RawDataReader` returns a pandas `DataFrame`. Key options:

- `start` / `end` — optional date range (omit for the files' full coverage)
- `mean_freq` — resample frequency, e.g. `'1h'` (omit for native resolution)
- `qc` — quality control (on by default; flags rows via `QC_Flag` and reports rates)
- `fill_missing` — pad to the requested range (default) or clamp to coverage
- `size_range` — diameter filter for SMPS / APS

Result metadata — coverage, QC rates, native frequency and more — is attached to
`df.attrs`. The [RawDataReader guide](https://alex870521.github.io/AeroViz/guide/rawdatareader/)
has the full parameter list, QC flags, and `df.attrs` reference.

## Data Processing & Visualization

```python
from AeroViz import DataProcess, plot
from AeroViz.plot import timeseries_interactive
```

- **`DataProcess`** — Chemistry (mass reconstruction, κ), Optical (Mie, IMPROVE,
  RI retrieval), SizeDistr (SMPS–APS merge, mode fitting), VOC (OFP, SOAP).
- **`plot`** — publication-ready matplotlib figures (time series, diurnal, wind rose, …).
- **`timeseries_interactive(df)`** — quick interactive Plotly viewer; click the
  legend to toggle columns, or `save='out.html'` for a standalone file.

See the [user guide](https://alex870521.github.io/AeroViz/) for details.

## Documentation

- [Full Documentation](https://alex870521.github.io/AeroViz/)
- [RawDataReader API](https://alex870521.github.io/AeroViz/api/RawDataReader/)
- [Changelog](docs/CHANGELOG.md)

## Contributing

Contributions are welcome! Please see our [GitHub Issues](https://github.com/Alex870521/AeroViz/issues) for bug reports and feature requests.

### Development setup

Building from source — an editable `pip install -e .`, or any platform without
a pre-built wheel — compiles a bundled Fortran extension (ISORROPIA II), so you
need a Fortran compiler (`gfortran`) plus `meson` / `ninja`:

```bash
# macOS:          brew install gcc
# Debian/Ubuntu:  sudo apt-get install gfortran
# Windows:        use the MSYS2 / mingw-w64 toolchain
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
