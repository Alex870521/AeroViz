# Optical Closure Analysis

Optical closure verifies whether measured optical coefficients are consistent with those calculated from chemical composition/size distribution.

## Overview

Optical closure analysis includes multiple methods:

1. **IMPROVE Closure**: Estimate extinction from chemical composition
2. **Mie Closure**: Calculate extinction from size distribution
3. **Hybrid Closure**: Combine chemical composition and size distribution

---

## Data Preparation

```python
from datetime import datetime
from pathlib import Path
from AeroViz import (
    RawDataReader,
    reconstruct_mass,
    volume_ri,
    improve,
    retrieve_ri,
    optical_basic,
)

# Read optical data
# NOTE: pass dates as start=/end= keywords. RawDataReader's 3rd/4th positional
# args are reset/qc, so positional datetimes would be misinterpreted.
neph = RawDataReader('NEPH', Path('./data/neph'),
                     start=datetime(2024, 1, 1), end=datetime(2024, 3, 31))
ae33 = RawDataReader('AE33', Path('./data/ae33'),
                     start=datetime(2024, 1, 1), end=datetime(2024, 3, 31))

# Read size distribution
smps = RawDataReader('SMPS', Path('./data/smps'),
                     start=datetime(2024, 1, 1), end=datetime(2024, 3, 31))

# Read chemical composition
igac = RawDataReader('IGAC', Path('./data/igac'),
                     start=datetime(2024, 1, 1), end=datetime(2024, 3, 31))
ocec = RawDataReader('OCEC', Path('./data/ocec'),
                     start=datetime(2024, 1, 1), end=datetime(2024, 3, 31))
```

---

## IMPROVE Closure

### Mass Reconstruction

```python
# Merge chemical data
df_chem = pd.concat([igac, ocec], axis=1)

# Mass reconstruction
mass_result = reconstruct_mass(df_chem)
df_mass = mass_result['mass']  # AS, AN, OM, Soil, SS, EC
```

### IMPROVE Extinction Calculation

```python
# Get RH data — df_RH must be a Series, not a single-column DataFrame
df_RH = met_data['RH']

# IMPROVE calculation
improve_result = improve(
    df_mass,
    df_RH,
    method='revised',     # 'revised' | 'modified' | 'localized'
)

# Output. Each frame's columns are: AS, AN, OM, Soil, SS, EC, total
# (lowercase 'total', the per-species sum — no '_ext' suffix).
ext_dry = improve_result['dry']   # Dry extinction
ext_wet = improve_result['wet']   # Wet extinction
alwc = improve_result['ALWC']     # Aerosol liquid water contribution
fRH = improve_result['fRH']       # Hygroscopic factor
```

### Closure Comparison

```python
import matplotlib.pyplot as plt

# Measured extinction (NEPH 'sca_550' + AE33 'abs_550', both lowercase)
ext_measured = neph['sca_550'] + ae33['abs_550']

# Calculated extinction ('total' column = sum over species)
ext_calculated = ext_wet['total']

# Plot comparison
fig, ax = plt.subplots(figsize=(8, 8))
ax.scatter(ext_measured, ext_calculated, alpha=0.5)
ax.plot([0, 500], [0, 500], 'k--', label='1:1 line')
ax.set_xlabel('Measured Extinction (Mm-1)')
ax.set_ylabel('IMPROVE Extinction (Mm-1)')
ax.set_title('IMPROVE Optical Closure')

# Calculate R2
from scipy import stats
slope, intercept, r, p, se = stats.linregress(ext_measured, ext_calculated)
ax.text(0.05, 0.95, f'R2 = {r**2:.3f}\nSlope = {slope:.2f}',
        transform=ax.transAxes, va='top')
plt.show()
```

---

## Mie Closure

### Calculate Refractive Index

```python
# Calculate volume and refractive index from chemical composition
df_RI = volume_ri(mass_result['volume'])   # n_dry, k_dry, n_amb, k_amb, gRH
```

### Mie Extinction Calculation

```python
from AeroViz.dataProcess.SizeDistr import SizeDist

# Create PSD object
psd = SizeDist(df_pnsd, state='dlogdp', weighting='n')

# Calculate extinction
ext_mie = psd.to_extinction(
    RI=df_RI,
    method='internal',
    result_type='extinction'
)

# Can also calculate scattering and absorption separately
sca_mie = psd.to_extinction(df_RI, method='internal', result_type='scattering')
abs_mie = psd.to_extinction(df_RI, method='internal', result_type='absorption')
```

### Mixing Mode Comparison

```python
methods = ['internal', 'external', 'core_shell']
results = {}

for method in methods:
    ext = psd.to_extinction(df_RI, method=method, result_type='extinction')
    results[method] = ext.sum(axis=1)  # Total extinction

# Compare different mixing modes
fig, ax = plt.subplots()
for method, ext in results.items():
    ax.scatter(ext_measured, ext, alpha=0.5, label=method)
ax.legend()
ax.set_xlabel('Measured')
ax.set_ylabel('Calculated')
plt.show()
```

---

## Refractive Index Retrieval

### Grid Search Method

```python
# Retrieve refractive index from measured optical properties and PSD
ri_retrieved = retrieve_ri(
    df_optical,         # Extinction, Scattering, Absorption columns
    df_pnsd,
    dlogdp=0.014,
    wavelength=550,
)

# Output
n_retrieved = ri_retrieved['re_real']        # Real part
k_retrieved = ri_retrieved['re_imaginary']   # Imaginary part

print(f"Retrieved RI: {n_retrieved.mean():.3f} + {k_retrieved.mean():.4f}i")
```

---

## Basic Optical Parameters

```python
# Compute derived optical properties (extinction, SSA, MEE/MSE/MAE, Ångström, etc.)
# Required columns:
#   df_sca : ['sca_550', 'SAE']         (from NEPH; lowercase)
#   df_abs : ['abs_550', 'AAE', 'eBC']  (from AE33; lowercase)
derived = optical_basic(
    df_sca=neph[['sca_550', 'SAE']],
    df_abs=ae33[['abs_550', 'AAE', 'eBC']],
    df_mass=df_chem[['PM25']],          # optional: enables mass efficiencies
    df_no2=gas[['NO2']],                # optional: subtracts gas absorption
    df_temp=met[['Temp']],              # optional
)

# Returns columns: ['abs', 'sca', 'ext', 'SSA', 'SAE', 'AAE', 'eBC']
# Single scattering albedo is already provided as 'SSA' (= sca / ext):
SSA = derived['SSA']
# (equivalently: derived['sca'] / derived['ext'])
```

---

## Complete Closure Analysis Script

```python
from datetime import datetime
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from AeroViz import (
    RawDataReader,
    reconstruct_mass,
    volume_ri,
    improve,
)
from AeroViz.dataProcess.SizeDistr import SizeDist

# 1. Read all data (pass dates as start=/end= keywords)
neph = RawDataReader('NEPH', Path('./data/neph'),
                     start='2024-01-01', end='2024-03-31', mean_freq='1h')
ae33 = RawDataReader('AE33', Path('./data/ae33'),
                     start='2024-01-01', end='2024-03-31', mean_freq='1h')
smps = RawDataReader('SMPS', Path('./data/smps'),
                     start='2024-01-01', end='2024-03-31', mean_freq='1h')
df_chem = pd.read_csv('chemistry.csv', parse_dates=['time'], index_col='time')
df_RH = pd.read_csv('met.csv', parse_dates=['time'], index_col='time')['RH']  # Series

# 2. Mass reconstruction and refractive index
mass_result = reconstruct_mass(df_chem)
mass = mass_result['mass']
ri   = volume_ri(mass_result['volume'])

# 3. IMPROVE closure ('wet' total extinction is the 'total' column)
improve_result = improve(mass, df_RH, method='revised')
ext_improve = improve_result['wet']['total']

# 4. Mie closure
psd = SizeDist(smps, state='dlogdp', weighting='n')
ext_mie = psd.to_extinction(ri, method='internal').sum(axis=1)

# 5. Measured extinction (lowercase column names)
ext_measured = neph['sca_550'] + ae33['abs_550']

# 6. Compare results
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

axes[0].scatter(ext_measured, ext_improve, alpha=0.5)
axes[0].set_title('IMPROVE Closure')

axes[1].scatter(ext_measured, ext_mie, alpha=0.5)
axes[1].set_title('Mie Closure')

for ax in axes:
    ax.plot([0, 500], [0, 500], 'k--')
    ax.set_xlabel('Measured (Mm-1)')
    ax.set_ylabel('Calculated (Mm-1)')

plt.tight_layout()
plt.savefig('optical_closure.png', dpi=300)
```

---

## Related Topics

- [Mie Scattering Theory](../theory/mie.md)
- [IMPROVE Extinction Equation](../theory/improve.md)
- [Optical API Reference](../api/DataProcess/Optical.md)
