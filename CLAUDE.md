# AeroViz - AI Usage Guide

AeroViz is an aerosol data processing and visualization toolkit for air quality research.

## Quick Start

```python
from AeroViz import RawDataReader

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
| `mean_freq` | str | Averaging frequency ('1h', '30min', '1D'); omit for native resolution (no resampling) |
| `qc` | bool/str | True=apply QC, 'MS'=monthly stats |
| `reset` | bool/str | True=reprocess, 'append'=add new data |
| `size_range` | tuple | (min_nm, max_nm) for SMPS/APS only |
| `fill_missing` | bool | True (default)=pad to requested range; False=clamp to data coverage |
| `raw_freq` | str | Override auto-detected resolution (e.g. '6min'); skips detection |
| `drop_outlier_dates` | bool | Stray timestamps far outside the data bulk (e.g. a year-2000 row in 2023 data) are always detected and warned about. False (default)=keep them (warning tells you how to fix the source); True=drop them automatically before gridding |

## Data Processing

Post-processing is a flat set of **top-level functions**, grouped into four
namespaces — `chemistry`, `optical`, `size`, `voc`. Each call is self-contained:
pass a DataFrame (or a few), get a DataFrame or dict back. No processor object,
no `path_out` — call `.to_csv()` yourself if you want a file.

```python
from AeroViz import reconstruct_mass, mie, improve, merge_psd, psd_stats, voc_potentials

mass = reconstruct_mass(df_chem)              # chemistry
ext  = mie(df_pnsd, df_RI, wavelength=550)    # optical
imp  = improve(df_mass, df_RH, method='revised')
ofp  = voc_potentials(df_voc)                 # voc
```

> **`DataProcess(method=..., path_out=...)` is DEPRECATED** (emits
> `DeprecationWarning`, will be removed). Migrate to the top-level functions:

| Old (deprecated) | New (top-level) |
|------------------|-----------------|
| `DataProcess('Chemistry').ReConstrc_basic(df)` | `reconstruct_mass(df)` |
| `DataProcess('Optical').IMPROVE(df_mass, df_RH, method='revised')` | `improve(df_mass, df_RH, method='revised')` |
| `DataProcess('Optical').Mie(df_psd, df_m)` | `mie(df_psd, df_m)` |
| `DataProcess('SizeDistr').basic(df)` | `psd_stats(df)` |
| `DataProcess('SizeDistr').distributions(df)` | `psd_distributions(df)` |
| `DataProcess('SizeDistr').merge_SMPS_APS_v4(smps, aps, pm25)` | `merge_psd(smps, aps, df_pm25=pm25, version=4)` |
| `DataProcess('VOC').VOC_basic(df)` | `voc_potentials(df)` |

### Size distribution (`SizeDistr` replacement)

The `'SizeDistr'` method maps onto three top-level functions plus the `SizeDist`
class (the engine, NOT deprecated) for the rest:

```python
from AeroViz import psd_stats, psd_distributions, merge_psd
from AeroViz.dataProcess.SizeDistr import SizeDist

stats = psd_stats(df_pnsd)['other']        # was .basic(df)  → total_num/GMD/GSD/mode_*
dists = psd_distributions(df_pnsd)         # was .distributions(df) → number/surface/volume

# Merge SMPS + APS (every version returns {'data', 'density', ...})
merged  = merge_psd(smps, aps, version=4, df_pm25=pm25)   # v4 needs PM2.5
merged3 = merge_psd(smps, aps, version=3)                 # v3 needs no mass ref
pnsd    = merged['data']                                  # recommended merged dN/dlogDp

# Everything else goes through SizeDist directly:
psd  = SizeDist(pnsd, state='dlogdp', weighting='n')
surf = psd.to_surface(); vol = psd.to_volume()
dry  = psd.to_dry(df_gRH)                                 # was .dry_psd(...)
extd = psd.to_extinction(df_RI, method='internal')       # was .extinction_distribution(...)
modes = psd.mode_statistics()                             # per-mode stats
lung  = psd.lung_deposition(activity='light')
```

> Top-level `merge_psd` also supports `density_range=` (QC) and an EXPERIMENTAL
> `version=5` (mass-anchored density, needs `df_pm1=`, emits a warning).

## Interactive timeseries

`AeroViz.plot.timeseries_interactive(df)` gives a quick interactive (Plotly)
look at a reader result: one trace per column, click the legend to toggle
columns. Defaults to numeric, non-size-bin columns (size bins / `QC_Flag`
excluded); `save='x.html'` exports a standalone file; `columns=[...]` picks
specific columns.

```python
from AeroViz.plot import timeseries_interactive
timeseries_interactive(df, columns=['eBC', 'AAE'])   # show=True by default
```

## Output Columns by Instrument

### AE33/AE43
- `BC1`-`BC7`: Black carbon at 7 wavelengths (ng/m³)
- `abs_370`-`abs_950`: Absorption coefficients (Mm⁻¹)
- `AAE`: Absorption Ångström Exponent
- `eBC`: Equivalent black carbon

### SMPS/APS
The reader returns the **size distribution itself** — a `dN/dlogDp` DataFrame
whose columns are particle diameters (SMPS in nm, e.g. `11.8`, `13.6`, ...;
APS in µm). There are no statistics columns in the reader output.

Derive statistics with `psd_stats(df)` (see `AeroViz.size`):
- `psd_stats(df)['other']`: stats frame — `total_num_all`, `GMD_num_all`,
  `GSD_num_all`, `mode_num_all`, plus per-mode `*_{num,surf,vol}_{Nucleation,
  Aitken,Accumulation,Coarse}`
- `psd_stats(df)['number'|'surface'|'volume']`: dN/dS/dV-dlogDp distributions
- `merge_psd(smps, aps, ...)`: merge SMPS+APS into a continuous PSD

Each read also writes, alongside `{prefix}.csv` (= dN/dlogDp): the
`{prefix}_dNdlogDp.csv` / `_dSdlogDp.csv` / `_dVdlogDp.csv` distributions and a
QC-aligned `{prefix}_stats.csv` (same columns as `psd_stats(df)['other']`).
Pass `append_stats=True` to `RawDataReader` to append the stat columns to the
returned frame (default False keeps it a clean PSD matrix for the functions
above).

### TEOM
- `PM_NV`: Non-volatile PM (μg/m³)
- `PM_Total`: Total PM (μg/m³)
- `Volatile_Fraction`: Volatile fraction (0-1)

### Aurora/NEPH
- `sca_550`: Scattering coefficient at 550 nm (Mm⁻¹) — **primary output**
- `SAE`: Scattering Ångström Exponent — **primary output**
- Aurora also keeps the per-wavelength raw channels: `B`, `G`, `R` (0° total
  scattering at blue/green/red) and `BB`, `BG`, `BR` (90° backscatter)
- NEPH keeps the same `B`, `G`, `R`, `BB`, `BG`, `BR` channels plus any
  ancillary columns (RH, pressure, temperatures, status)

Note: column names are lowercase — `sca_550` (not `Sca_550`); AE33 absorption is
`abs_550` / `abs_880` (not `Abs_550` / `Abs_880`).

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

## Reader Metadata (`df.attrs`)

Every `RawDataReader` result carries metadata in `df.attrs`. With the default
`fill_missing=True` the output is padded to the *requested* range, so the frame
can be mostly NaN — use `df.attrs['coverage_*']` to learn what the files
**actually** contained without scanning for non-null rows (or pass
`fill_missing=False` to clamp the grid to that coverage).

```python
df = RawDataReader('AE33', '/data/NZ_AE33', start='2024-01-01', end='2024-12-31')

df.attrs['coverage_start']   # Timestamp — first row with real data
df.attrs['coverage_end']     # Timestamp — last row with real data (None if no data in range)
df.attrs['requested_start']  # what you asked for
df.attrs['n_files']          # how many raw files were read
df.attrs['total_rate']       # overall % valid (QC path only)
```

| Key | When | Meaning |
|-----|------|---------|
| `instrument`, `station`, `source_path`, `n_files` | always | provenance |
| `coverage_start` / `coverage_end` | always | real data span (ignores NaN padding) |
| `requested_start` / `requested_end` | always | the range you passed |
| `raw_freq` | always | native frequency, auto-detected per file (config is fallback) |
| `freq_mixed` | always | True if files had differing resolutions (most-common was used) |
| `fill_missing` | always | whether the grid was padded to the request or clamped to coverage |
| `aeroviz_version`, `processed_at` | always | build / run stamp |
| `mean_freq`, `qc_applied`, `qc_freq` | qc on | output frequency + QC mode |
| `acquisition_rate`, `yield_rate`, `total_rate` | qc on | overall rates (%) |

`attrs` survive `to_pickle`/`read_pickle` and `resample` (pandas >= 2), but are
dropped by `concat` of frames with conflicting attrs — re-stamp if you merge.

**Caching:** with `reset=False` (default) the parsed result is cached as a pkl
under `{instrument}_outputs/`. The cache stores the *canonical* frame — data on
its native grid over the files' own coverage, **not** padded to any range — so
a cache hit still applies the current call's `start`/`end` and `fill_missing`
and re-stamps `df.attrs`. Pre-existing pkls from older versions are detected as
stale and re-parsed automatically.

**Frequency detection:** each file's resolution is auto-detected (regular
`inferred_freq`, else median timestamp delta); `meta['freq']` in the instrument
config is only a last-resort fallback. If files in one batch disagree, the
most-common resolution is used and `freq_mixed` is set with a warning — pass
`raw_freq=` to force one. Off-grid timestamps (e.g. 08:20 on an hourly grid) are
snapped by rounding each row to its nearest grid bin, so a single reading is
never duplicated across two slots.

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
from AeroViz import RawDataReader, psd_stats

# Read SMPS data with size range filter — returns dN/dlogDp (diameters as columns)
smps = RawDataReader(
    instrument='SMPS',
    path='/data/SMPS',
    start='2024-01-01',
    end='2024-06-30',
    size_range=(10, 500)  # nm
)

# Derive statistics from the distribution
stats = psd_stats(smps)['other']
print(stats['total_num_all'].mean())   # total number concentration (#/cm³)
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

1. `start` / `end` are optional — omit to read the files' full coverage (one
   side may be given to bound just that end); `df.attrs['coverage_*']` reports
   what was actually found
2. Use `qc=True` for quality-controlled data
3. Use `reset=True` only when reprocessing is needed
4. Check `QC_Flag` column for data quality
5. Size distribution instruments (SMPS/APS) support `size_range` parameter
