# Post-Processing Functions Tutorial

AeroViz exposes its post-processing as a flat set of top-level functions, grouped into four namespaces — `chemistry`, `optical`, `size`, and `voc`. Each call is self-contained: it takes a DataFrame (or a few), runs one calculation, and returns a DataFrame or dict.

!!! warning "Legacy API deprecated"
    The old `DataProcess(...)` factory class — e.g. `dp = DataProcess('Chemistry', Path('./output'))` followed by `dp.ReConstrc_basic(df_chem)` — still exists but is deprecated and will be removed in a future release. New code should use the top-level functions described on this page. The functions take exactly the same inputs and return the same results — they just skip the constructor boilerplate and the `path_out` argument. If you want a CSV, call `.to_csv()` on the returned DataFrame yourself. A method-by-method migration table is in the [Post-processing API](../api/DataProcess/index.md#migrating-from-dataprocess).

## Basic Usage

```python
from AeroViz import reconstruct_mass, mie, psd_distributions

# Each call is independent — no need to pre-instantiate a processor
result = reconstruct_mass(df_chem)
ext = mie(df_pnsd, df_RI, wavelength=550)
psd = psd_distributions(df_pnsd)
```

You can also import each function from its namespace:

```python
from AeroViz import chemistry, optical, size, voc

result = chemistry.reconstruct_mass(df_chem)
ext    = optical.mie(df_pnsd, df_RI, wavelength=550)
```

## Function Overview

| Namespace | Functions |
|-----------|-----------|
| `chemistry` | `reconstruct_mass`, `split_oc_ec`, `partition_ratios`, `isoropia`, `volume_ri`, `kappa`, `growth_factor` |
| `optical` | `optical_basic`, `improve`, `mie`, `gas_extinction`, `retrieve_ri`, `brown_carbon`; Mie building blocks `mie_lognormal`, `mie_multimodal`, `mie_core_shell`, `mie_core_shell_sd`, `scattering_function`, `scattering_function_sd`, `phase_matrix`, `nephelometer_truncation_correction`, `iterative_inversion`, `iterative_inversion_sd`, `contour_intersection` (see the [Optical API](../api/DataProcess/Optical.md)) |
| `size` | `psd_stats`, `psd_distributions`, `merge_psd` |
| `voc` | `voc_potentials` |

---

## Size Distribution

### Basic Statistics

```python
from AeroViz import psd_stats

result = psd_stats(df_pnsd)
# result['number']   - Number distribution
# result['surface']  - Surface area distribution
# result['volume']   - Volume distribution
# result['other']    - Mode statistics
```

### Number / Surface / Volume Distributions

```python
from AeroViz import psd_distributions

dists = psd_distributions(df_pnsd)
# dists['number'], dists['surface'], dists['volume']
# dists['properties'] - concatenated GMD/GSD/mode per weighting
```

### SMPS-APS Merging

```python
from AeroViz import merge_psd

# v4 (recommended, requires PM2.5 reference)
result = merge_psd(smps_data, aps_data, df_pm25=pm25_data, version=4)

merged   = result['data']            # recommended merged dN/dlogDp (every version)
density  = result['density']         # estimated effective density (g/cm³)
# v3/v4 variants: result['data_dn'], result['data_dndsdv'], result['data_cor_dn']
```

`version` selects the algorithm: 1 (original power-law), 2 (simplified), 3 (dN/dS/dV refinement), 4 (PM2.5 fitness, default and recommended), 5 (**experimental** — mass-anchored density from PM1 closure; emits a warning). v4 requires `df_pm25`; v5 requires `df_pm1`. `times_range=(start, stop, step)` sets the SMPS-times grid search for v4.

### Using the SizeDist Class

For per-row distribution conversions (extinction, dry PSD, lung deposition), use the `SizeDist` class directly:

```python
from AeroViz.dataProcess.SizeDistr import SizeDist

psd = SizeDist(df_pnsd, state='dlogdp', weighting='n')

# Distribution conversion
surface    = psd.to_surface()
volume     = psd.to_volume()
extinction = psd.to_extinction(df_RI, method='internal')
dry        = psd.to_dry(df_gRH)

# Statistics
props = psd.properties()
stats = psd.mode_statistics()

# Lung deposition (ICRP 66)
lung = psd.lung_deposition(activity='light')
```

---

## Chemistry

### Mass Reconstruction

```python
from AeroViz import reconstruct_mass

result = reconstruct_mass(df_chem, df_ref=df_pm25)
# result['mass']        - Reconstructed mass (AS, AN, OM, Soil, SS, EC, total)
# split_om=True additionally splits OM into POA / SOA by the EC-tracer method
# result['volume']      - Component volumes (*_volume + total_dry)
# result['NH4_status']  - Ammonium status DataFrame ('ratio', 'status'); status is Enough / Deficiency
# result['RI_550']      - Refractive index at 550 nm (RI_dry, RI_wet)
# result['density_rec'] - Reconstructed density
```

### Volume and Refractive Index

```python
from AeroViz import volume_ri

ri = volume_ri(df_volume, df_alwc=df_alwc)
# Columns: n_dry, k_dry, n_amb, k_amb, gRH
```

### Hygroscopicity (kappa)

```python
from AeroViz import kappa, growth_factor

gf  = growth_factor(df_volume, df_alwc)        # gRH = (V_wet / V_dry)^(1/3)
kap = kappa(df_data, diameter=0.5)             # df_data needs gRH, AT, RH
```

### Gas-Particle Partitioning

```python
from AeroViz import partition_ratios

ratios = partition_ratios(df_data)
# SOR, NOR, NOR_2, NTR, epls_SO42-, epls_NO3-, epls_NH4+, epls_Cl-
```

### OC / EC Split

```python
from AeroViz import split_oc_ec

result = split_oc_ec(df_lcres, df_mass=df_pm25)
# result['basic']  - OC/EC + POC/SOC/WSOC/WISOC + status flags
# result['ratio']  - Per-species PM / OC ratios
```

### ISORROPIA II

```python
from pathlib import Path
from AeroViz import isoropia

# path_out is accepted for backward compatibility only and ignored —
# the calculation is a native (f2py) extension with no file I/O
result = isoropia(df_ions, df_met)
# result['input'], result['output'] (pH, ALWC, gas/aerosol partitioning)
```

---

## Optical

### Basic Optical Properties

```python
from AeroViz import optical_basic

basic = optical_basic(df_sca, df_abs, df_mass=df_mass, df_no2=df_no2, df_temp=df_temp)
# Columns: abs, sca, ext, SSA, SAE, AAE, eBC, plus MAE / MSE / MEE when df_mass is given
```

### IMPROVE Extinction

```python
from AeroViz import improve

# df_RH must be a Series (e.g. met['RH']), not a single-column DataFrame.
result = improve(df_mass, df_RH, method='revised')
# method = 'revised' | 'modified' | 'localized'
# result['dry'], result['wet'], result['ALWC'], result['fRH']
# Expected: result['dry'] / result['wet'] have columns
#   AS, AN, OM, Soil, SS, EC, total  (lowercase 'total' = the per-species sum)
result['dry']['total'].mean()    # mean total dry extinction (Mm-1)
```

### Mie Calculation

```python
from AeroViz import mie

# Single-material RI (Series of complex numbers)
ext = mie(df_pnsd, df_RI_complex, wavelength=550)
# Columns: ext, sca, abs (Mm⁻¹)

# Species mixing-table RI (DataFrame with *_volume_ratio columns)
ext = mie(df_pnsd, df_mix_table, wavelength=550, mixing='internal')
# mixing = 'internal' | 'external' | 'both'

# Per-bin distribution instead of totals
dext = mie(df_pnsd, df_RI_complex, wavelength=550, distribution=True)
```

`mie` replaces the legacy `Mie` / `extinction_distribution` / `extinction_full` triplet. Behavior is controlled by the shape of `ri` and the `mixing` / `distribution` keywords.

### Mie building blocks

Synthetic-PSD shortcuts, core-shell particles and angular scattering, for
when you do not have a measured size distribution or need more than bulk
coefficients.

```python
from AeroViz import mie_lognormal, mie_multimodal, mie_core_shell, mie_core_shell_sd

# One-shot optics from a synthetic lognormal (or multi-mode) PSD
mie_lognormal(refractive_index, wavelength=550, *, geo_mean=200, geo_std=2.0,
              total_number=1e6, n_bins=167, dp_range=(1, 2500))   -> {'ext', 'sca', 'abs'}
mie_multimodal(refractive_index, wavelength=550, *, modes,
               n_bins=167, dp_range=(1, 2500))                    -> {'ext', 'sca', 'abs'}
# modes = [(geo_mean, geo_std, total_number), ...]

# Core-shell (Aden-Kerker)
mie_core_shell(m_core, m_shell, d_core, d_total, wavelength)
#   -> single-particle efficiencies Q_ext, Q_sca, Q_abs, g, Q_pr, Q_back, Q_ratio
mie_core_shell_sd(m_core, m_shell, dp_core, dp_total, ndp,
                  wavelength=550, psd_type='dNdlogDp')
#   -> PSD-integrated ext, sca, abs (Mm⁻¹) plus g_eff
```

```python
from AeroViz import (scattering_function, scattering_function_sd, phase_matrix,
                     nephelometer_truncation_correction)

scattering_function(m, wavelength, diameter, angles=None, space='theta')
#   -> {'angles', 'SL', 'SR', 'SU'}   parallel / perpendicular / unpolarised phase function
scattering_function_sd(m, wavelength, dp, ndp, angles=None, space='theta', psd_type='auto')
#   -> same keys, PSD-integrated
phase_matrix(m, wavelength, diameter, mu=None)
#   -> {'mu', 'S11', 'S12', 'S33', 'S34'}   Mueller phase-matrix elements
nephelometer_truncation_correction(sae, wavelength=550, instrument='NEPH')
#   -> Anderson & Ogren (1998) multiplicative factor for an integrating nephelometer
#      (TSI 3563 default; Aurora 3000 also tabulated); sae = scattering Ångström exponent
```

### Inverse problems

Besides `retrieve_ri` (below), two retrievals work from bulk (Bext, Bsca, Babs)
and a PSD description instead of a per-bin matrix:

```python
from AeroViz import iterative_inversion, iterative_inversion_sd, contour_intersection

# Newton-Raphson on measured (Bext, Bsca, Babs)
iterative_inversion(b_ext, b_sca, b_abs, lognormal_params,
                    wavelength=550, n_initial=1.5, k_initial=0.01)
#   lognormal_params = {'geo_mean': ..., 'geo_std': ..., 'total_number': ...}
#   -> {'n', 'k', 'iterations', 'converged', 'residuals'}
iterative_inversion_sd(b_ext, b_sca, b_abs, dp, ndp,
                       wavelength=550, n_initial=1.5, k_initial=0.01)   # measured PSD instead

# Sumlin (2018) contour-intersection retrieval over an (n, k) grid
contour_intersection(b_ext, b_sca, b_abs, lognormal_params, wavelength=550,
                     n_range=(1.3, 2.0), k_range=(0, 0.5), grid=51)
```

### Gas Extinction

```python
from AeroViz import gas_extinction

g = gas_extinction(df_no2, df_temp)
# Columns: ScatteringByGas, AbsorptionByGas, ExtinctionByGas
```

### Refractive Index Retrieval

```python
from AeroViz import retrieve_ri

ri = retrieve_ri(df_optical, df_pnsd, dlogdp=0.014, wavelength=550)
# Columns: re_real, re_imaginary
```

### Brown Carbon Separation

```python
from AeroViz import brown_carbon

bc_brc = brown_carbon(df_abs, ref_wavelength=880, aae_bc=1.0)
# Splits multi-wavelength absorption into BC vs BrC components
```

---

## VOC

```python
from AeroViz import voc_potentials

result = voc_potentials(df_voc)
# result['Conc']  - mass concentration per species (ug/m3)
# result['OFP']   - Ozone Formation Potential per species (ug O3/m3)
# result['SOAP']  - SOAP per species
# result['LOH']   - OH-reactivity per species
# Each frame also has per-class '*_total' columns and a grand 'Total' column,
# so the grand total OFP is result['OFP']['Total'].
```

---

## Input Format Requirements

### Size Distribution

```python
# Columns are particle diameters (nm)
df_pnsd.columns = [11.8, 13.6, 15.7, ..., 523.3]

# Index is time
df_pnsd.index = DatetimeIndex
```

### Chemical Composition

```python
# Required columns
columns = [
    'SO42-', 'NO3-', 'NH4+',      # Ions
    'OC', 'EC',                    # Carbon
    'Na+', 'Cl-',                  # Sea salt
    'Al', 'Fe', 'Ti',              # Crustal elements
    'PM25'                         # Mass
]
```

### VOC

```python
# Columns are species names
df_voc.columns = ['Benzene', 'Toluene', 'Ethylbenzene', ...]

# Units: ppb or ug/m3
```

---

## Output Handling

The new functions return DataFrames or dicts of DataFrames; they do **not** write files. If you want CSVs, call `.to_csv()` yourself:

```python
result = reconstruct_mass(df_chem)
result['mass'].to_csv('./output/mass.csv')
```

(`isoropia` still *accepts* a `path_out` argument for backward compatibility but ignores it: ISORROPIA II runs as a native f2py extension on every platform, with no temp files. The argument will be removed in a future release.)

---

## Related Topics

- [SizeDistr API](../api/DataProcess/SizeDistr.md)
- [Chemistry API](../api/DataProcess/Chemistry.md)
- [Optical API](../api/DataProcess/Optical.md)
- [VOC API](../api/DataProcess/VOC.md)
- [Size Distribution](size_distribution.md) · [Optical Closure](optical_closure.md) · [Chemical Analysis](chemical_analysis.md) · [VOC Analysis](voc_analysis.md)
