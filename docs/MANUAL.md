# AeroViz User Manual

AeroViz is an aerosol data-processing and visualization toolkit for air-quality
and atmospheric-science research. It provides a single, consistent interface to:

- **Read and quality-control raw instrument data** from 20+ atmospheric
  instruments (black-carbon monitors, size-distribution sizers, mass monitors,
  nephelometers, OC/EC analyzers, XRF, ion chromatographs, VOC, …) through one
  `RawDataReader` factory.
- **Analyze size distributions** — derive number/surface/volume statistics from
  SMPS/APS dN/dlogDp matrices, merge SMPS + APS into a continuous PSD, convert
  weightings, compute mode statistics, hygroscopic drying, lung deposition, and
  per-bin extinction.
- **Reconstruct chemistry and mass** — convert measured ions to reconstructed
  species (AS, AN, OM, Soil, SS, EC), compute volumes, refractive index,
  hygroscopic growth, kappa, gas-particle partitioning, OC/EC splitting, and run
  ISORROPIA II for aerosol thermodynamics.
- **Compute optical properties** — Mie theory (homogeneous, core-shell,
  lognormal, multimodal), bulk extinction/SSA/Ångström exponents, IMPROVE
  extinction reconstruction, nephelometer truncation correction, brown-carbon
  separation, and refractive-index retrieval.
- **Analyze VOCs** — ozone-formation potential (OFP), SOA potential (SOAP), and
  OH-reactivity from VOC concentrations.
- **Visualize** — a large `AeroViz.plot` library covering time series,
  distributions, optical plots, regressions, correlation matrices, and
  meteorology (wind rose, CBPF, HYSPLIT).

It is aimed at researchers and engineers who process field-campaign aerosol data
and need reproducible, QC-aware pipelines from raw files to publication figures.

> **Version covered:** AeroViz `0.3.1`. The API surface below was verified
> against the installed source; signatures and return keys are taken directly
> from the code.

---

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Concepts / Architecture](#core-concepts--architecture)
- [Reading Raw Data (`RawDataReader`)](#reading-raw-data-rawdatareader)
  - [Signature and parameters](#signature-and-parameters)
  - [Supported instruments](#supported-instruments)
  - [What each read writes to disk](#what-each-read-writes-to-disk)
  - [Reader metadata (`df.attrs`)](#reader-metadata-dfattrs)
  - [The SMPS/APS dN/dlogDp contract](#the-smpsaps-dndlogdp-contract)
- [Quality Control](#quality-control)
- [Size Distribution](#size-distribution)
  - [`psd_stats`](#psd_stats)
  - [`psd_distributions`](#psd_distributions)
  - [`merge_psd` (SMPS + APS)](#merge_psd-smps--aps)
  - [The `SizeDist` class](#the-sizedist-class)
- [Chemical Analysis](#chemical-analysis)
- [Optical Properties](#optical-properties)
- [VOC Analysis](#voc-analysis)
- [Visualization (`AeroViz.plot`)](#visualization-aerovizplot)
- [Utilities / DataBase / DataClassifier](#utilities--database--dataclassifier)
- [Troubleshooting / FAQ](#troubleshooting--faq)
- [Further Reading](#further-reading)

---

## Installation

AeroViz is published on PyPI as **`AeroViz`**.

```bash
pip install AeroViz
```

- **Python:** requires Python **>= 3.10** (wheels are built for 3.10–3.14).
- AeroViz ships pre-built binary wheels (the ISORROPIA II Fortran extension is
  compiled cross-platform via `meson-python` + `cibuildwheel`), so no Fortran
  toolchain is needed for a normal install.

**Core dependencies** (installed automatically): `pandas >= 2.2`,
`numpy >= 2.0`, `matplotlib`, `scipy`, `seaborn`, `scikit-learn`, `windrose`,
`cartopy`, `tabulate`, `rich`, `numba`, `plotly`.

**Optional extras:**

```bash
pip install "AeroViz[test]"   # pytest + coverage
pip install "AeroViz[dev]"    # black, isort, flake8, mypy, build, twine, commitizen
pip install "AeroViz[docs]"   # mkdocs + material + mkdocstrings
```

To build from source you need a C and Fortran compiler (gfortran) plus
`meson-python`; see `CONTRIBUTING.md`.

---

## Quick Start

> **Start here:** new users should (1) `pip install AeroViz`, (2) read a dataset
> with `RawDataReader` (below), then (3) pass the resulting DataFrame to a
> processing function (`reconstruct_mass`, `improve`, `merge_psd`, …) or a plot.
> No data of your own? Run the bundled examples in demo mode:
> `python examples/01_basic_reading.py --demo` and
> `python examples/04_size_distribution.py --demo`.

A minimal end-to-end example: read a black-carbon dataset with QC and inspect
the result.

```python
from AeroViz import RawDataReader

# Read AE33 aethalometer data, hourly-averaged, with automatic QC
df = RawDataReader(
    instrument='AE33',          # instrument name (see supported list)
    path='/data/NZ_AE33',       # directory containing the raw files
    start='2024-01-01',         # ISO date (optional)
    end='2024-06-30',           # ISO date (optional)
    mean_freq='1h',             # output frequency; omit for native resolution
    qc=True,                    # apply quality control
)

print(df[['eBC', 'AAE']].describe())
# Expected output: a time-indexed DataFrame with columns BC1-BC7,
# abs_370-abs_950, AAE, eBC, QC_Flag — here .describe() prints count/mean/std/...
# for the eBC and AAE columns.

# Reader metadata is on df.attrs
print(df.attrs['coverage_start'], '→', df.attrs['coverage_end'])
print('valid %:', df.attrs.get('total_rate'))
```

A size-distribution example using the current API:

```python
from AeroViz import RawDataReader, psd_stats

# SMPS reader returns the dN/dlogDp matrix (diameters are the columns)
smps = RawDataReader('SMPS', '/data/NZ_SMPS',
                     start='2024-01-01', end='2024-06-30',
                     mean_freq='1h', size_range=(10, 500))   # nm

stats = psd_stats(smps)            # derive statistics
total_num = stats['other']['total_num_all']     # #/cm³ per timestamp
print(total_num.mean())
```

---

## Core Concepts / Architecture

AeroViz exposes a **flat functional API** plus a few sub-namespaces. All entry
points resolve to the same implementations; pick the import style you prefer:

```python
from AeroViz import RawDataReader, reconstruct_mass, mie, psd_stats   # flat
from AeroViz import chemistry, optical, size, voc                     # namespaces
from AeroViz.optical import improve, mie                              # explicit
```

The main building blocks:

| Layer | What it is | Examples |
|-------|------------|----------|
| **`RawDataReader`** | Factory that reads + QCs raw instrument files into a tidy time-indexed `DataFrame`. | `RawDataReader('SMPS', path, ...)` |
| **Top-level functions** | Direct, return-a-result analysis functions (no on-disk boilerplate). | `reconstruct_mass`, `merge_psd`, `improve`, `mie`, `voc_potentials` |
| **Sub-namespaces** | The same functions grouped by domain. | `AeroViz.chemistry`, `AeroViz.optical`, `AeroViz.size`, `AeroViz.voc` |
| **Classes** | Stateful helpers for richer workflows. | `SizeDist`, `DataBase`, `DataClassifier` |
| **`AeroViz.plot`** | Plotting library. | `plot.timeseries`, `plot.distribution.heatmap`, `plot.meteorology.wind_rose` |
| **`DataProcess`** | **Deprecated** legacy factory; prefer the top-level functions. | — |

**Data conventions:**

- DataFrames are **time-indexed** (a `DatetimeIndex`), with one column per
  measured quantity (or per diameter bin for size distributions).
- Size-distribution frames are **`dN/dlogDp`** matrices whose *column labels are
  the particle diameters* (SMPS in nm, APS in µm).
- Concentrations are in instrument-native physical units (e.g. µg/m³, #/cm³,
  Mm⁻¹); the relevant unit is noted per function.

**Output-folder convention:** by default, reading writes processed artifacts to
`{path}/{instrument}_outputs/` (a pkl cache, intermediate CSVs, a log, and a
`report.json`). A typical campaign directory looks like:

```
/data/
├── NZ_AE33/             # convention: Station_Instrument
│   ├── *.dat            # raw files
│   └── ae33_outputs/    # processed outputs
├── NZ_SMPS/
└── NZ_TEOM/
```

---

## Reading Raw Data (`RawDataReader`)

`RawDataReader` is a factory: it picks the right reader for the instrument,
parses the matching raw files, optionally applies QC, resamples, fills the time
grid, caches the result, and returns a `DataFrame`.

### Signature and parameters

```python
RawDataReader(
    instrument: str,
    path: Path | str,
    reset: bool | str = False,
    qc: bool | str = True,
    start: datetime | str = None,
    end: datetime | str = None,
    mean_freq: str | None = None,
    size_range: tuple[float, float] | None = None,
    fill_missing: bool = True,
    output_dir: Path | str | None = None,
    output_prefix: str | None = None,
    save_pkl: bool = True,
    save_intermediate_csv: bool = True,
    save_report: bool = True,
    quiet: bool = False,
    log_level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR'] = 'INFO',
    **kwargs,
) -> pandas.DataFrame
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `instrument` | str | — | Instrument key (see [Supported instruments](#supported-instruments)). |
| `path` | str / Path | — | Directory containing the raw data files. Must exist. |
| `reset` | bool / str | `False` | `False`=use cached processed data if available; `True`=force full reprocess from raw; `'append'`=add new data to existing. |
| `qc` | bool / str | `True` | `True`=apply QC and compute overall rates; `False`=raw data only; a frequency string computes rate stats at intervals (`'W'`, `'MS'`, `'QS'`, `'YS'`, e.g. `'2MS'`). |
| `start` | datetime / str | `None` | Start of the range. ISO string (`'YYYY-MM-DD'` or with time) or `datetime`. Omit to start at the first file timestamp. |
| `end` | datetime / str | `None` | End of the range. A bare midnight date is treated as end-of-day. Omit to end at the last timestamp. |
| `mean_freq` | str | `None` | Resample frequency (`'1h'`, `'30min'`, `'1D'`). **Omit for native resolution (no resampling).** |
| `size_range` | tuple | `None` | `(min, max)` in nm; **only valid for SMPS / APS / GRIMM**. SMPS range 1–1000 nm; APS range 500–20000 nm. |
| `fill_missing` | bool | `True` | `True`=reindex/pad to the full requested `[start, end]` (can yield a mostly-NaN frame); `False`=clamp the grid to actual data coverage. |
| `output_dir` | Path / str | `None` | Output directory. Default `path/{instrument}_outputs/`. |
| `output_prefix` | str | `None` | Output filename prefix. Default `output_{instrument}`. |
| `save_pkl` | bool | `True` | Whether to write the pkl cache. (Existing pkls are still read when `reset=False`.) |
| `save_intermediate_csv` | bool | `True` | Whether to write intermediate `_read_*` CSVs. |
| `save_report` | bool | `True` | Whether to write `report.json`. |
| `quiet` | bool | `False` | Suppress console output (log file still written). |
| `log_level` | str | `'INFO'` | Log-file verbosity. |

**Selected `**kwargs`** (instrument-specific, passed through):

| Kwarg | Applies to | Meaning |
|-------|-----------|---------|
| `append_stats` | SMPS / APS | `False` (default) returns the clean dN/dlogDp matrix; `True` appends derived statistics columns to the returned frame. See [the dN/dlogDp contract](#the-smpsaps-dndlogdp-contract). |
| `raw_freq` | all | Override the auto-detected native resolution (e.g. `'6min'`); skips per-file frequency detection. |
| `drop_outlier_dates` | all | `False` (default) keeps stray off-bulk timestamps (with a warning); `True` drops them automatically before gridding. |

**Caching:** with `reset=False` the parsed result is cached as a pkl under
`{instrument}_outputs/`. The cache stores the *canonical* frame (native grid over
the files' own coverage, **not** padded to any range), so a cache hit still
applies the current call's `start`/`end`/`fill_missing` and re-stamps
`df.attrs`. Pre-existing pkls from older versions are detected as stale and
re-parsed automatically.

### Supported instruments

The instrument key must be one of the following (grouped by measurement type).
The file-glob pattern and native frequency come from the instrument config.

**Black-carbon / absorption monitors**

| Key | Description | Native freq |
|-----|-------------|-------------|
| `AE33` | Aethalometer, 7-wavelength BC (370–950 nm) | 1 min |
| `AE43` | Aethalometer, 7-wavelength BC | 1 min |
| `BC1054` | 10-wavelength black-carbon monitor | 1 min |
| `MA350` | MicroAeth portable BC monitor | 1 min |

**Size distribution**

| Key | Description | Native freq |
|-----|-------------|-------------|
| `SMPS` | Scanning Mobility Particle Sizer (nm) | 6 min |
| `APS` | Aerodynamic Particle Sizer (µm) | 6 min |
| `GRIMM` | Optical particle counter | 6 min |

**Mass concentration**

| Key | Description | Native freq |
|-----|-------------|-------------|
| `TEOM` | Tapered Element Oscillating Microbalance | 6 min |
| `BAM1020` | Beta Attenuation Monitor | 1 h |

**Optical (scattering)**

| Key | Description | Native freq |
|-----|-------------|-------------|
| `NEPH` | TSI integrating nephelometer | 5 min |
| `Aurora` | Aurora 3000 nephelometer (RGB) | 1 min |

**Chemical composition**

| Key | Description | Native freq |
|-----|-------------|-------------|
| `OCEC` | Sunset OC/EC analyzer (LCRes files) | 1 h |
| `IGAC` | Ion chromatograph — water-soluble ions/gases | 1 h |
| `Xact` | XRF heavy metals (with built-in MDLs) | 1 h |
| `Q-ACSM` | Aerosol Chemical Speciation Monitor | 30 min |
| `VOC` | Volatile organic compounds | 1 h |

**Other / aggregated sources**

| Key | Description | Native freq |
|-----|-------------|-------------|
| `EPA` | Taiwan EPA air-quality data | 1 h |
| `Minion` | Minion sensor | 1 h |

> Note: `IGAC`, `Minion`, `EPA`, `VOC`, and `BAM1020` are typically read from
> pre-aggregated / second-hand data — pass `mean_freq=None` to keep their native
> resolution.

You can always confirm the current list at runtime:

```python
from AeroViz.rawDataReader.config.supported_instruments import meta
print(list(meta.keys()))
```

### What each read writes to disk

Inside `{instrument}_outputs/` (unless suppressed):

- `{prefix}.pkl` — cached canonical frame (`save_pkl=True`).
- Intermediate `_read_*_qc.csv` / `_read_*_raw.csv` (`save_intermediate_csv=True`).
- `report.json` (`save_report=True`).
- A log file (always, even with `quiet=True`).

For **SMPS / APS**, each read additionally writes, alongside
`{prefix}.csv` (= dN/dlogDp):

- `{prefix}_dNdlogDp.csv`, `{prefix}_dSdlogDp.csv`, `{prefix}_dVdlogDp.csv`
  (number / surface / volume distributions), and
- `{prefix}_stats.csv` (QC-aligned summary statistics; same columns as
  `psd_stats(df)['other']`).

### Reader metadata (`df.attrs`)

Every result carries provenance and coverage metadata in `df.attrs`. Because
`fill_missing=True` can pad the frame with NaNs, use `coverage_*` to learn what
the files actually contained.

| Key | When | Meaning |
|-----|------|---------|
| `instrument`, `station`, `source_path`, `n_files` | always | provenance |
| `coverage_start` / `coverage_end` | always | real data span (ignores NaN padding; `None` if no data in range) |
| `requested_start` / `requested_end` | always | the range you passed |
| `raw_freq` | always | native frequency (auto-detected per file) |
| `freq_mixed` | always | `True` if files had differing resolutions |
| `fill_missing` | always | whether the grid was padded or clamped |
| `aeroviz_version`, `processed_at` | always | build / run stamp |
| `mean_freq`, `qc_applied`, `qc_freq` | qc on | output frequency + QC mode |
| `acquisition_rate`, `yield_rate`, `total_rate` | qc on | overall rates (%) |

`attrs` survive `to_pickle`/`read_pickle` and `resample` (pandas >= 2) but are
dropped by `concat` of frames with conflicting attrs — re-stamp if you merge.

### The SMPS/APS dN/dlogDp contract

This is the most important current-API detail for size-distribution work:

- **`RawDataReader('SMPS' | 'APS', ...)` returns the size-distribution matrix
  itself** — a `dN/dlogDp` `DataFrame` whose **columns are particle diameters**
  (SMPS as float nm such as `11.8`, `13.6`, …; APS in µm). **There are no
  summary-statistics columns in the reader output.**
- **Derive statistics** with the top-level [`psd_stats(df)`](#psd_stats), which
  returns a dict; the summary frame is under the `'other'` key.
- Pass **`append_stats=True`** to `RawDataReader` to append the statistics
  columns to the returned frame. *Caveat:* this mixes string-typed columns into
  the frame, so the result can no longer be passed straight to `psd_stats` /
  `merge_psd` / `SizeDist`. Default `False` keeps it a clean numeric PSD matrix.

```python
smps = RawDataReader('SMPS', '/data/NZ_SMPS', start='2024-01-01', end='2024-06-30')
# smps is dN/dlogDp; columns are diameters in nm
print(smps.columns[:5].tolist())     # e.g. [11.8, 12.2, 12.6, ...]

stats = psd_stats(smps)
stats['other']['total_num_all']      # total number concentration (#/cm³)
```

---

## Quality Control

QC is applied when `qc=True` (the default) or with a frequency string. The
quality-control engine (`AeroViz.rawDataReader.core.qc`) builds a per-row
`QC_Flag` column and computes overall rates that are stored in `df.attrs`.

- **`qc=True`** — apply all instrument-appropriate QC rules and compute overall
  acquisition / yield / total rates.
- **`qc=False`** — return raw, un-QC'd data (no rate calculation).
- **`qc='W' | 'MS' | 'QS' | 'YS'`** (optionally prefixed with a number, e.g.
  `'2MS'`) — apply QC and report rate statistics at that interval.

The `QC_Flag` column indicates per-row data quality. Typical values:

| Flag | Meaning |
|------|---------|
| `Valid` | Passed all QC checks |
| `Insufficient` | Not enough data points in the period |
| `Status Error` | Instrument status error |
| `Invalid BC` / `Invalid Number Conc` | Out-of-range values |
| `Spike` | Sudden value change detected |

Overall rates (`acquisition_rate`, `yield_rate`, `total_rate`, all in %) are
written to `df.attrs` whenever QC is enabled.

```python
df = RawDataReader('AE33', '/data/NZ_AE33', qc=True, mean_freq='1h')
valid = df[df['QC_Flag'] == 'Valid']
print(df.attrs['total_rate'], '% valid overall')
```

---

## Size Distribution

The size-distribution API lives in `AeroViz.size` (re-exported at the top
level) and the `SizeDist` class in
`AeroViz.dataProcess.SizeDistr`.

### `psd_stats`

```python
psd_stats(df, hybrid_bin_start_loc=None, unit='nm',
          bin_range=(11.8, 19810), input_type='dlogdp') -> dict
```

Computes number / surface / volume distributions and mode statistics from a PSD
matrix (column labels must be diameters convertible to `float`).

| Parameter | Default | Description |
|-----------|---------|-------------|
| `df` | — | PSD matrix (dN/dlogDp by default). |
| `hybrid_bin_start_loc` | `None` | Column index where bin spacing changes (for merged SMPS+APS hybrid grids). `None`=single mean `dlogdp`. |
| `unit` | `'nm'` | Diameter unit (`'nm'` or `'um'`). |
| `bin_range` | `(11.8, 19810)` | Inclusive `(min, max)` diameter range to keep (in `unit`). |
| `input_type` | `'dlogdp'` | `'dlogdp'`/`'norm'`=already normalized; otherwise raw counts (divided by `dlogdp`). |

**Returns** a dict with keys `'number'`, `'surface'`, `'volume'` (distribution
DataFrames keyed by diameter) and **`'other'`** (the statistics summary frame).
The `'other'` frame includes columns such as `total_num_all`, `GMD_num_all`,
`GSD_num_all`, `mode_num_all`, plus per-mode columns
(`total_{num,surf,vol}_{Nucleation,Aitken,Accumulation,Coarse}`, etc.).

```python
stats = psd_stats(smps)
stats['other']['total_num_all'].mean()
stats['other']['total_num_Accumulation'].mean()
```

### `psd_distributions`

```python
psd_distributions(df_pnsd) -> dict
```

Convenience wrapper computing the three weighted distributions and their
properties from a number size distribution (dN/dlogDp; diameter columns in nm).

**Returns** `{'number', 'surface', 'volume', 'properties'}` — the first three
are DataFrames keyed by diameter; `'properties'` concatenates per-distribution
properties (GMD, GSD, mode, …).

### `merge_psd` (SMPS + APS)

Merge SMPS and APS distributions into a single continuous PSD.

```python
merge_psd(
    df_smps, df_aps, *,
    version: int = 4,
    df_pm25=None,
    df_pm1=None,
    aps_unit: str = 'um',
    smps_overlap_lowbound: float = 500,
    aps_fit_highbound: float = 1000,
    shift_mode: str = 'mobility',
    dndsdv_alg: bool = True,
    density_range: tuple = (0.6, 2.6),
    times_range: tuple = (0.8, 1.25, 0.05),
) -> dict
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `df_smps`, `df_aps` | — | SMPS (nm) and APS (µm by default) dN/dlogDp matrices. |
| `version` | `4` | Algorithm version `{1, 2, 3, 4, 5}` (see below). |
| `df_pm25` | `None` | PM2.5 reference for the fitness function. **Required for `version=4`.** |
| `df_pm1` | `None` | PM1 mass reference (µg/m³; prefer a volatile-corrected PM1). **Required for `version=5`.** |
| `aps_unit` | `'um'` | Unit of the APS diameter columns (`'um'` or `'nm'`). |
| `smps_overlap_lowbound` | `500` | SMPS bin lower bound for the overlap region (nm). |
| `aps_fit_highbound` | `1000` | APS bin upper bound for the power-law fit region (nm). |
| `shift_mode` | `'mobility'` | `'mobility'` or `'aerodynamic'`. **Only used by `version=1`.** |
| `dndsdv_alg` | `True` | Apply dN/dS/dV correlation refinement. **Only used by `version >= 3`.** |
| `density_range` | `(0.6, 2.6)` | Effective-density QC range (g/cm³); timestamps whose estimated density (shift²) falls outside are set to NaN. Applied in **every** version. Widen (e.g. `(0.3, 2.6)`) for looser QC. |
| `times_range` | `(0.8, 1.25, 0.05)` | `(start, stop, step)` SMPS-times grid search. **Only used by `version=4`.** |

**Unified output (every version):** the returned dict always contains:

- **`'data'`** — the recommended merged dN/dlogDp (diameters in nm as columns).
- **`'density'`** — the estimated effective density (g/cm³).

**Version behaviour and version-specific extra keys:**

| Version | What `'data'` is | Extra keys | Notes |
|---------|------------------|-----------|-------|
| 1 | single power-law merge | — | base method with `shift_mode`. |
| 2 | mobility merge | `'data_aero'` (aerodynamic-diameter merge) | APS iterative correction + dual output. |
| 3 | APS-corrected dN/dS/dV merge (`cor_dndsdv`) | `'data_dn'`, `'data_dndsdv'`, `'data_cor_dn'`; `'density'` has one column per variant | multiprocessing + dN/dS/dV correlation. |
| 4 *(default, recommended)* | same as v3 | v3 keys **plus** `'times'` (chosen SMPS-times multiplier per algorithm) | adds PM2.5 fitness + SMPS-times correction. **Needs `df_pm25`.** |
| 5 *(EXPERIMENTAL)* | mass-anchored merge | `'density_hourly'`, `'density_unc'` | mass-anchored density via PM1 closure (daily). **Emits a `UserWarning`; needs `df_pm1`. API/behaviour not stable.** |

```python
from AeroViz import RawDataReader, merge_psd

smps = RawDataReader('SMPS', '/data/SMPS', mean_freq='1h', size_range=(11.8, 593.5))
aps  = RawDataReader('APS',  '/data/APS',  mean_freq='1h')

# Recommended: v4 needs a PM2.5 reference
result = merge_psd(smps, aps, df_pm25=df_pm25, version=4)
merged  = result['data']        # continuous dN/dlogDp, columns in nm
density = result['density']      # g/cm³

# No PM2.5 available? use v3
result3 = merge_psd(smps, aps, version=3, density_range=(0.6, 2.6))
```

> **`ValueError`** is raised if `version` is not in `{1,2,3,4,5}`, if
> `version=4` is called without `df_pm25`, or if `version=5` is called without
> `df_pm1`.

### The `SizeDist` class

For richer, stateful workflows, build a `SizeDist` object directly:

```python
from AeroViz.dataProcess.SizeDistr import SizeDist

SizeDist(
    data: DataFrame,
    state: Literal['dN', 'ddp', 'dlogdp'] = 'dlogdp',
    weighting: Literal['n', 's', 'v', 'ext_in', 'ext_ex'] = 'n',
)
```

Attributes: `data`, `dp` (diameters), `dlogdp`, `index`, `state`, `weighting`.

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `to_surface()` | DataFrame | Surface-area distribution (dS/dlogDp). |
| `to_volume()` | DataFrame | Volume distribution (dV/dlogDp). |
| `properties()` | DataFrame | GMD, GSD, mode, mode contributions, totals (e.g. `total_n`, `GMD_n`, `GSD_n`). |
| `mode_statistics(unit='nm')` | dict | Per-mode number/surface/volume distributions + GMD/GSD/total/mode. Summary frame is under `'statistics'`. |
| `to_extinction(RI, method='internal', result_type='extinction')` | DataFrame | Per-bin extinction/scattering/absorption (Mm⁻¹) via Mie theory. `method` ∈ {`'internal'`, `'external'`, `'core_shell'`, `'sensitivity'`}. `RI` needs `n` and `k` columns. |
| `to_dry(df_gRH, uniform=True)` | DataFrame | Convert ambient (wet) PSD to dry PSD using a growth factor (`df_gRH` has a `gRH` column). |
| `lung_deposition(activity='light')` | dict | ICRP 66 deposition; `activity` ∈ {`'sleep'`, `'sitting'`, `'light'`, `'heavy'`}. Returns `'DF'` (HA/TB/AL/Total fractions) and `'total_dose'`. |

```python
psd = SizeDist(df_pnsd, state='dlogdp', weighting='n')

props = psd.properties()
print(props['total_n'].mean(), props['GMD_n'].mean(), props['GSD_n'].mean())

dep = psd.lung_deposition(activity='light')
dep['DF'].mean()      # HA, TB, AL, Total deposition fractions
```

> Note on `mode_statistics`: the per-mode summary frame is under the
> `'statistics'` key when called on a `SizeDist` instance; the top-level
> `psd_stats` wrapper renames that key to `'other'`.

---

## Chemical Analysis

All chemistry functions are in `AeroViz.chemistry` and re-exported at the top
level. They return DataFrames / dicts directly (no on-disk side effects).

### `reconstruct_mass`

```python
reconstruct_mass(*df_chem, df_ref=None, df_water=None, df_density=None,
                 nam_lst=None, split_om=False, oa_oc_ratio=1.8) -> dict
```

Reconstructs aerosol mass and volume from chemical composition: converts ionic
species to reconstructed species (AS, AN, OM, Soil, SS, EC) given the ammonium
neutralization status, and computes volumes, density, and refractive index.
Multiple input DataFrames are concatenated along columns and renamed to
`nam_lst` (default
`['NH4+', 'SO42-', 'NO3-', 'Fe', 'Na+', 'OC', 'EC']`). With `split_om=True` it
also splits OM into POA/SOA via the EC-tracer method (`oa_oc_ratio`).

**Returns** a dict with keys: `mass`, `volume`, `vol_cal`, `eq`, `NH4_status`,
`density_mat`, `density_rec`, `RI_550`, `RI_450`.

```python
result = reconstruct_mass(df_chem, df_ref=df_pm25)
df_mass = result['mass']              # AS, AN, OM, Soil, SS, EC, total
df_mass['total']                      # reconstructed PM mass (sum of species)
result['NH4_status']['status']        # ammonium status: Enough / Deficiency
```

### `volume_ri`

```python
volume_ri(df_volume, df_alwc=None) -> DataFrame
```

Volume-average refractive index (dry & ambient) and gRH at 550 nm using the
volume-mixing rule. `df_volume` needs `total_dry` plus at least one species
volume column (`AS_volume`, `AN_volume`, `OM_volume`, `Soil_volume`,
`SS_volume`, `EC_volume`). **Returns** columns `n_dry`, `k_dry`, `n_amb`,
`k_amb`, `gRH` (ambient values are NaN unless `df_alwc` is supplied).

### `growth_factor`

```python
growth_factor(df_volume, df_alwc) -> DataFrame
```

Hygroscopic growth factor `gRH = (V_wet / V_dry)^(1/3)`. `df_volume` needs
`total_dry`; `df_alwc` needs `ALWC`. **Returns** a single `gRH` column.

### `kappa`

```python
kappa(df_data, diameter=0.5) -> DataFrame
```

Hygroscopicity parameter kappa. `df_data` needs `gRH`, `AT` (°C), `RH` (%);
`diameter` is the dry diameter in µm. **Returns** a single `kappa_chem` column.

### `partition_ratios`

```python
partition_ratios(df_data) -> DataFrame
```

Gas-particle partitioning ratios. Requires a `temp` (°C) column plus at least
one species pair (e.g. `SO42-`+`SO2` → SOR, `NO3-`+`NO2` → NOR, `NH4+`+`NH3` →
NTR, `Cl-`+`HCl`). **Returns** columns including `SOR`, `NOR`, `NOR_2`, `NTR`,
`epls_SO42-`, `epls_NO3-`, `epls_NH4+`, `epls_Cl-`.

### `split_oc_ec`

```python
split_oc_ec(df_lcres, df_mass=None, ocec_ratio=None, ocec_ratio_month=1,
            hr_lim=200, least_square_range=(0.1, 2.5, 0.1),
            WISOC_OC_range=(0.2, 0.7, 0.01)) -> dict
```

Splits OC into primary (POC) and secondary (SOC) using the EC-tracer / MRS
method, for both Thermal and Optical analyses, plus WSOC/WISOC and status flags.
`df_lcres` (OC/EC level results) must include `OC1`–`OC4`, `PC`, `Thermal_OC`,
`Thermal_EC`, `Optical_OC`, `Optical_EC`, `Sample_Volume`. **Returns** a dict
with `basic` (OC/EC data + status flags) and `ratio` (per-species PM/OC ratios).

### `isoropia`

```python
isoropia(*df_chem, path_out=None, nam_lst=None) -> dict
```

Runs **ISORROPIA II** (native cross-platform f2py extension; works on macOS,
Linux, Windows) to compute aerosol pH, ALWC, and gas-particle partitioning.
Inputs are concatenated and renamed to `nam_lst` (default
`['Na+', 'SO42-', 'NH4+', 'NO3-', 'Cl-', 'Ca2+', 'K+', 'Mg2+', 'NH3', 'HNO3',
'HCl', 'RH', 'temp']`). `path_out` is retained for backward compatibility but
no longer used. **Returns** `{'input', 'output'}` where `output` has pH, ALWC,
and gas/aerosol-phase NH3/HNO3/HCl/NH4+/NO3-/Cl-.

```python
from AeroViz import reconstruct_mass, isoropia, volume_ri, kappa

rec = reconstruct_mass(df_chem, df_ref=df_pm25)
iso = isoropia(df_ions, df_meteo)
ri  = volume_ri(rec['volume'], df_alwc=df_alwc)
```

---

## Optical Properties

Optical functions live in `AeroViz.optical` (re-exported at top level).

### Bulk extinction

#### `optical_basic`

```python
optical_basic(df_sca, df_abs, df_mass=None, df_no2=None, df_temp=None) -> DataFrame
```

Computes basic optical properties (extinction, SSA, mass efficiencies MEE/MSE/MAE,
Ångström exponents) from measured scattering and absorption (Mm⁻¹). Optional
`df_mass` (µg/m³) enables mass efficiencies; `df_no2` (ppb) + `df_temp` (°C)
subtract gas absorption.

**Required columns:** `df_sca` needs `['sca_550', 'SAE']` (NEPH output);
`df_abs` needs `['abs_550', 'AAE', 'eBC']` (AE33 output). All column names are
lowercase. **Returns** a DataFrame with `['abs', 'sca', 'ext', 'SSA', 'SAE',
'AAE', 'eBC']` (SSA = sca / ext).

#### `improve` (IMPROVE extinction reconstruction)

```python
improve(df_mass, df_RH=None, method='revised', df_nh4_status=None,
        df_ext=None, oa_oc_ratio=1.8, upper_bounds=None) -> dict
```

Reconstructs extinction from species mass using the IMPROVE equation.
`method` ∈ {`'revised'`, `'modified'`, `'localized'`}. `'revised'`/`'modified'`
need AS, AN, OM, Soil, SS, EC; `'localized'` needs AS, AN, POC, SOC, Soil, SS,
EC **and** `df_ext` (with `Scattering`/`Absorption` columns) to fit POA/SOA mass
scattering efficiencies via MLR. **Returns** a dict with `dry`, `wet`, `ALWC`,
`fRH` (and for `'localized'`: `coefficients`, `regression`).

> **`df_RH` must be a `Series`** (e.g. `met['RH']`), not a single-column
> DataFrame — passing `met[['RH']]` raises `ValueError`.

The `dry` and `wet` frames have one column per species **plus** a `total`
column (the per-species sum): `AS, AN, OM, Soil, SS, EC, total` (lowercase
`total`, no `_ext` suffix). The total dry/wet extinction is the `total`
column — do **not** `.sum(axis=1)` (that double-counts the `total` column):

```python
ext = improve(rec['mass'], df_RH=met['RH'], method='revised')
ext['dry']['total']     # total dry extinction (Mm⁻¹)
ext['wet']['total']     # total wet (ambient) extinction (Mm⁻¹)
```

#### `gas_extinction`

```python
gas_extinction(df_no2, df_temp) -> DataFrame
```

Gas contribution to extinction (Rayleigh + NO2 absorption). `df_no2` in ppb,
`df_temp` in °C. **Returns** `ScatteringByGas`, `AbsorptionByGas`,
`ExtinctionByGas` (Mm⁻¹).

#### `brown_carbon`

```python
brown_carbon(df_abs, wavelengths=None, ref_wavelength=880, aae_bc=1.0) -> DataFrame
```

Separates BC and BrC absorption via the AAE approach. `df_abs` has multi-λ
absorption columns named like `abs_370`, `abs_470`, …, `abs_880`. Default
`wavelengths=[370, 470, 520, 590, 660]`. **Returns** BC/BrC absorption, BrC
fraction per wavelength, and `AAE_BrC`.

### Mie theory

#### `mie`

```python
mie(df_psd, ri, wavelength=550, mixing=None, distribution=False)
```

Mie optics from a PSD (`df_psd`: rows=time, columns=diameters in nm). `ri` is
either a **Series of complex** RI (single material) or a **DataFrame with
`*_volume_ratio` columns** (species mixing table). For a mixing table, `mixing`
∈ {`'internal'`, `'external'`, `'both'`}. With `distribution=False` returns a
DataFrame of total ext/sca/abs (Mm⁻¹) per row; with `distribution=True` returns
a dict of per-bin distributions `{'ext', 'sca', 'abs'}` (each a DataFrame keyed
by diameter). `mixing='both'` returns `{'internal', 'external'}`.

#### `mie_lognormal` / `mie_multimodal`

```python
mie_lognormal(refractive_index, wavelength=550, *, geo_mean=200, geo_std=2.0,
              total_number=1e6, n_bins=167, dp_range=(1, 2500)) -> dict
mie_multimodal(refractive_index, wavelength=550, *, modes,
               n_bins=167, dp_range=(1, 2500)) -> dict
```

One-shot Mie optics from a synthetic lognormal (or multi-mode) PSD. For
`mie_multimodal`, `modes` is a sequence of `(geo_mean, geo_std, total_number)`
tuples. Both **return** `{'ext', 'sca', 'abs'}` (Mm⁻¹).

#### Core-shell Mie (Aden-Kerker)

```python
mie_core_shell(m_core, m_shell, d_core, d_total, wavelength) -> dict
mie_core_shell_sd(m_core, m_shell, dp_core, dp_total, ndp,
                  wavelength=550, psd_type='dNdlogDp') -> dict
```

`mie_core_shell` returns single-particle efficiencies `Q_ext`, `Q_sca`,
`Q_abs`, `g`, `Q_pr`, `Q_back`, `Q_ratio`. `mie_core_shell_sd` is
PSD-integrated and returns `ext`, `sca`, `abs` (Mm⁻¹) plus `g_eff`.

### Angular scattering

```python
scattering_function(m, wavelength, diameter, angles=None, space='theta') -> dict
scattering_function_sd(m, wavelength, dp, ndp, angles=None, space='theta',
                       psd_type='auto') -> dict
phase_matrix(m, wavelength, diameter, mu=None) -> dict
nephelometer_truncation_correction(sae, wavelength=550, instrument='NEPH')
```

- `scattering_function` / `scattering_function_sd` return the Mie phase function
  (`angles`, `SL`, `SR`, `SU`); the `_sd` variant is PSD-integrated.
- `phase_matrix` returns the Mueller phase-matrix elements (`mu`, `S11`, `S12`,
  `S33`, `S34`).
- `nephelometer_truncation_correction` returns the Anderson & Ogren (1998)
  multiplicative correction factor for an integrating nephelometer (TSI 3563
  default; Aurora 3000 also tabulated). `sae` is the scattering Ångström
  exponent.

### Refractive-index retrieval (inverse problems)

```python
retrieve_ri(df_optical, df_pnsd, dlogdp=0.014, wavelength=550) -> DataFrame
iterative_inversion(b_ext, b_sca, b_abs, lognormal_params,
                    wavelength=550, n_initial=1.5, k_initial=0.01) -> dict
iterative_inversion_sd(b_ext, b_sca, b_abs, dp, ndp,
                       wavelength=550, n_initial=1.5, k_initial=0.01) -> dict
contour_intersection(b_ext, b_sca, b_abs, lognormal_params, wavelength=550,
                     n_range=(1.3, 2.0), k_range=(0, 0.5), grid=51) -> dict
```

- `retrieve_ri` retrieves the complex RI from co-located optical
  (`Extinction`/`Scattering`/`Absorption`) and PSD data; **returns** columns
  `re_real`, `re_imaginary`.
- `iterative_inversion` / `iterative_inversion_sd` use Newton-Raphson on
  measured (Bext, Bsca, Babs); `lognormal_params` is a dict with `geo_mean`,
  `geo_std`, `total_number`. **Returns** `n`, `k`, `iterations`, `converged`,
  `residuals`.
- `contour_intersection` is the Sumlin (2018) contour-intersection retrieval.

```python
from AeroViz import improve, mie, reconstruct_mass

rec = reconstruct_mass(df_chem)
ext = improve(rec['mass'], df_RH=df_rh, method='revised')   # df_rh is a Series
ext['dry']['total']           # total dry extinction (Mm⁻¹)
```

---

## VOC Analysis

```python
from AeroViz import voc_potentials

voc_potentials(df_voc) -> dict
```

Computes VOC reactivity potentials and concentration summaries. For each species
in `df_voc` (concentrations in **ppb**), it uses the bundled `support_voc.json`
parameter table (MW, MIR, SOAP, KOH) to compute:

- Mass concentrations (µg/m³)
- **Ozone Formation Potential (OFP)** (µg O₃/m³ via MIR × ppb)
- **Secondary Organic Aerosol Potential (SOAP)**
- **OH-reactivity** (KOH × concentration)

Species are aggregated into chemistry classes (alkane, alkene, aromatic, alkyne,
OVOC, ClVOC). Column names in `df_voc` must match the supported species; an
unrecognized column raises `KeyError`.

**Returns** a dict of four time-indexed DataFrames:

| Key | Quantity | Unit |
|-----|----------|------|
| `'Conc'` | Mass concentration | µg/m³ |
| `'OFP'` | Ozone Formation Potential | µg O₃/m³ |
| `'SOAP'` | Secondary Organic Aerosol Potential | — |
| `'LOH'` | OH-reactivity (loss rate) | s⁻¹ |

Each frame's columns are the individual species, **plus** per-class totals named
`<class>_total` (e.g. `aromatic_total`, `alkane_total`), **plus** a grand
`Total` column. So the grand total OFP is `result['OFP']['Total']` (a Series):

```python
result = voc_potentials(df_voc)
result['OFP']['Total'].mean()          # mean total OFP (µg O₃/m³)
# Rank individual species (exclude the aggregate columns):
ofp = result['OFP']
species = [c for c in ofp.columns if c != 'Total' and not c.endswith('_total')]
ofp[species].mean().sort_values(ascending=False).head(10)
```

```python
import pandas as pd
# The VOC reader is deprecated — read the CSV directly and pass to voc_potentials.
voc = pd.read_csv('/data/VOC/voc.csv', index_col=0, parse_dates=True,
                  na_values=('-', 'N.D.'))
voc.columns = voc.columns.str.strip()
result = voc_potentials(voc)
```

---

## Visualization (`AeroViz.plot`)

`AeroViz.plot` is a large matplotlib-based library. Most functions take a
`DataFrame` and return a `(fig, ax)` tuple, accept an optional `ax=` to compose
into subplots, and pass extra `**kwargs` through. There is also a Plotly-based
interactive viewer.

**Time series**

| Function | Purpose |
|----------|---------|
| `timeseries(df, y, y2=None, yi=None, ...)` | Multi-series time-series plot (primary/secondary axes, rolling smoothing, scatter/bar/line/arrow styles). |
| `timeseries_stacked(df, y, yi, label, plot_type='both', ...)` | Stacked time series (absolute / percentage / both). |
| `timeseries_interactive(df, columns=None, *, save=None, show=True, title=None)` | Interactive Plotly viewer; one trace per column, legend toggling, `save='x.html'` exports standalone. |

```python
from AeroViz.plot import timeseries, timeseries_interactive
fig, ax = timeseries(df, y='eBC', y2='AAE')
timeseries_interactive(df, columns=['eBC', 'AAE'])    # interactive HTML
```

**Distributions** (`AeroViz.plot.distribution`)

| Function | Purpose |
|----------|---------|
| `heatmap(data, unit, ...)` | PSD heatmap (`unit` ∈ Number/Surface/Volume/Extinction). |
| `heatmap_tms(data, unit, ...)` | Time-series PSD heatmap. |
| `three_dimension(data, unit, ...)` | 3-D distribution plot. |
| `plot_dist(data, ...)` | Average distribution curve (with std / enhancement / error options). |
| `curve_fitting(dp, dist, ...)` | Fit and overlay lognormal modes. |

**Optical** (`AeroViz.plot.optical`)

`Q_plot`, `RI_couple`, `RRI_2D`, `response_surface`, `scattering_phase` — Mie
efficiency curves, refractive-index couplings, 2-D real-RI response surfaces, and
single-particle scattering phase functions.

**Regression / correlation**

| Function | Purpose |
|----------|---------|
| `scatter(df, x, y, ...)` | Scatter (optional regression line / 1:1 diagonal / color/size mapping). |
| `linear_regression(df, x, y, ...)` | Simple linear regression. |
| `multiple_linear_regression(df, x, y, ...)` | Multiple linear regression. |
| `corr_matrix(data, ...)` / `cross_corr_matrix(data1, data2, ...)` | Correlation heatmaps. |

**Categorical / composition**

`bar`, `box`, `violin`, `pie`, `donuts`, `radar`, `diurnal_pattern`,
`metal_heatmap` / `metal_heatmaps`, `koschmieder` (visibility vs extinction),
`ammonium_rich`.

**Meteorology** (`AeroViz.plot.meteorology`)

| Function | Purpose |
|----------|---------|
| `wind_rose(df, WS, WD, val=None, typ='scatter', ...)` | Wind rose (bar or scatter). |
| `CBPF(df, WS, WD, val=None, ...)` | Conditional bivariate probability function (pollution-rose-style). |
| `hysplit(file=..., savefig=None)` | Plot HYSPLIT back-trajectories. |

**Helpers:** `set_figure`, `combine_legends`, `auto_label_pct`, `Color`,
`Unit`.

---

## Utilities / DataBase / DataClassifier

### `DataBase`

```python
from AeroViz import DataBase

DataBase(file_path=None, load_data=False, load_PSD=False)
```

A helper class for loading bundled / project datasets (and PSD data). Construct
it pointing at a file and toggle `load_data` / `load_PSD` to pull the
corresponding tables.

### `DataClassifier`

```python
from AeroViz import DataClassifier

DataClassifier(df, by, df_support=None, cut_bins=None, qcut=None,
               labels=None) -> tuple[DataFrame, DataFrame]
```

Groups a DataFrame and returns summary statistics. `by` can be a built-in
grouping (`'Hour'`, `'State'`, `'Season'`, `'Season_state'`) or a column name;
use `cut_bins`/`qcut`/`labels` for custom binning. If `by` is not a column,
provide `df_support` to supply the grouping variable. **Returns** a tuple of
two DataFrames (e.g. group means and standard deviations), commonly fed straight
into `AeroViz.plot.bar` / `box` / `violin`.

```python
mean_df, std_df = DataClassifier(df, by='Season')
```

### Legacy: `DataProcess`

```python
DataProcess(method, path_out, excel=False, csv=True)   # DEPRECATED
```

The old method-based factory (`method` ∈ `'Chemistry'`, `'Optical'`,
`'SizeDistr'`, `'VOC'`) is **deprecated** and will be removed. Use the top-level
functions instead. Migration cheatsheet:

| Old | New |
|-----|-----|
| `DataProcess('Chemistry', ...).ReConstrc_basic(df, ...)` | `reconstruct_mass(df, ...)` |
| `DataProcess('Optical', ...).IMPROVE(df_mass, df_RH, method='revised')` | `improve(df_mass, df_RH, method='revised')` |
| `DataProcess('Optical', ...).Mie(df_psd, df_m)` | `mie(df_psd, df_m)` |
| `DataProcess('SizeDistr', ...).merge_SMPS_APS_v4(df_smps, df_aps, df_pm25)` | `merge_psd(df_smps, df_aps, df_pm25=df_pm25, version=4)` |
| `DataProcess('VOC', ...).VOC_basic(df_voc)` | `voc_potentials(df_voc)` |

---

## Troubleshooting / FAQ

**My SMPS/APS DataFrame no longer has `total_num` (or other statistic) columns.**
That is intentional. `RawDataReader('SMPS' | 'APS', ...)` now returns the raw
**dN/dlogDp matrix** (diameters as columns). Derive statistics with
`psd_stats(df)['other']`, or pass `append_stats=True` to the reader to append
them. The per-read `{prefix}_stats.csv` sidecar also has them.

**`append_stats=True` broke `psd_stats` / `merge_psd`.** When you append stats,
the frame gains string-typed columns and is no longer a pure numeric PSD matrix.
Keep `append_stats=False` (default) for anything you'll feed to `psd_stats`,
`merge_psd`, or `SizeDist`, and read the stats from the dedicated functions or
the `_stats.csv` sidecar.

**`merge_psd(..., version=4)` raises `ValueError` about `df_pm25`.** Version 4
uses a PM2.5 fitness function, so it **requires** `df_pm25`. Either pass a PM2.5
reference DataFrame, or use `version=3` to skip the fitness step.

**`merge_psd(..., version=5)` prints a UserWarning.** Version 5 is
**EXPERIMENTAL** (mass-anchored density via PM1 closure) and emits a
`UserWarning`; it also **requires `df_pm1`**. Prefer `version=4` for production
work.

**My merged density column is mostly NaN.** Each timestamp's estimated effective
density (shift²) is QC'd against `density_range` (default `(0.6, 2.6)` g/cm³);
out-of-range timestamps are set to NaN. Widen the range, e.g.
`density_range=(0.3, 2.6)`, for looser QC.

**My reader frame is huge and mostly NaN.** With `fill_missing=True` (default)
the grid is padded to the full requested `[start, end]`. Use
`df.attrs['coverage_start'/'coverage_end']` to see what the files actually
contained, or pass `fill_missing=False` to clamp the grid to real coverage.

**`size_range` raised an error.** `size_range` is only valid for `SMPS`, `APS`,
`GRIMM`. SMPS values must be within 1–1000 nm; APS within 500–20000 nm.

**`KeyError: 'Instrument name ... is not valid'.** The instrument key is not
recognized. Check the exact spelling against the
[supported list](#supported-instruments) (note the hyphen in `Q-ACSM`).

**Metadata (`df.attrs`) disappeared after `concat`.** pandas drops `attrs` when
concatenating frames with conflicting attrs. `attrs` survive pickling and
`resample` (pandas >= 2) but you must re-stamp after a merge.

---

## Further Reading

- **Guides:** `docs/guide/` — `rawdatareader.md`, `size_distribution.md`,
  `chemical_analysis.md`, `optical_closure.md`, `voc_analysis.md`,
  `visualization.md`, `dataprocess.md`, `rawdatareader-internals.md`.
- **Theory:** `docs/theory/` — `mie.md`, `improve.md`, `mass_reconstruction.md`,
  `kappa.md`, `lognormal.md`, `icrp.md`, `ofp.md`.
- **API reference:** `docs/api/` and the published docs at
  <https://alex870521.github.io/AeroViz/>.
- **Runnable examples:** `examples/01_basic_reading.py` …
  `examples/07_plotting.py`.
- **SMPS–APS merge details:** `AeroViz/dataProcess/SizeDistr/merge/README.md`.
- **Project / repo:** <https://github.com/Alex870521/AeroViz>.
</content>
</invoke>
