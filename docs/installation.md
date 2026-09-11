# Installation

```bash
pip install AeroViz
```

Pre-built wheels are published for Linux, macOS and Windows on Python 3.10
through 3.14 — no compiler needed.

## What the base install contains

The base package is deliberately small: only what reading data and the size /
optical / chemistry maths need.

| Dependency | Why |
|---|---|
| pandas ≥ 2.2.2, numpy ≥ 2.0 | frames and arrays |
| scipy ≥ 1.15 | Mie and size-distribution maths |
| numba ≥ 0.61.2 | the QC and pre-processing hot loops (`@jit(nopython=True)` only) |
| rich ~ 13.9, tabulate | reader console output and tables |

`import AeroViz`, `RawDataReader` and every post-processing function work with
just this.

## Plotting: the `plot` extra

Everything under `AeroViz.plot` — matplotlib, seaborn, scikit-learn, windrose,
cartopy, plotly — lives in an optional extra, because those packages account
for most of the install size (plotly alone is ~88 MB; cartopy pulls in pyproj
and shapely).

```bash
pip install "AeroViz[plot]"
```

Without it the package still imports; the first call into `AeroViz.plot`
raises an `ImportError` telling you to install the extra.

## Building from source

An editable install, or any platform without a pre-built wheel, compiles the
bundled Fortran extension (ISORROPIA II), so you need a Fortran compiler plus
`meson` and `ninja`:

```bash
# Fortran toolchain first
#   macOS:          brew install gcc
#   Debian/Ubuntu:  sudo apt-get install gfortran
#   Windows:        MSYS2 / mingw-w64

git clone https://github.com/Alex870521/AeroViz.git
cd AeroViz
pip install -e ".[plot]"          # add ,test,dev for the test suite and linters
```

## Check it works

```python
from importlib.metadata import version
print(version('AeroViz'))

from AeroViz import RawDataReader, psd_stats, reconstruct_mass   # base install
from AeroViz import plot                                          # needs the plot extra
```

## Common problems

- **`ImportError` mentioning matplotlib / plotly / cartopy** — you called into
  `AeroViz.plot` without the extra. `pip install "AeroViz[plot]"`.
- **A Fortran / meson error during `pip install`** — pip fell back to building
  from source (no wheel for your platform or Python). Install the toolchain
  above, or use a Python version that has a wheel.
- **numba refuses to install next to another package** — AeroViz only needs
  numba ≥ 0.61.2, and is tested at that floor, so pin numba to what the other
  package wants as long as it is ≥ 0.61.2.

Next: [Getting Started](guide/index.md) for a first read, or
[RawDataReader Usage](guide/rawdatareader.md) for every parameter.
