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
from AeroViz import RawDataReader
from AeroViz.dataProcess import DataProcess

# Read optical data
neph = RawDataReader('NEPH', Path('./data/neph'),
                     datetime(2024,1,1), datetime(2024,3,31))
ae33 = RawDataReader('AE33', Path('./data/ae33'),
                     datetime(2024,1,1), datetime(2024,3,31))

# Read size distribution
smps = RawDataReader('SMPS', Path('./data/smps'),
                     datetime(2024,1,1), datetime(2024,3,31))

# Read chemical composition
igac = RawDataReader('IGAC', Path('./data/igac'),
                     datetime(2024,1,1), datetime(2024,3,31))
ocec = RawDataReader('OCEC', Path('./data/ocec'),
                     datetime(2024,1,1), datetime(2024,3,31))
```

---

## IMPROVE Closure

### Mass Reconstruction

```python
dp_chem = DataProcess('Chemistry', Path('./output'))

# Merge chemical data
df_chem = pd.concat([igac, ocec], axis=1)

# Mass reconstruction
mass_result = dp_chem.reconstruction_basic(df_chem)
df_mass = mass_result['mass']  # AS, AN, OM, Soil, SS, EC
```

### IMPROVE Extinction Calculation

```python
dp_opt = DataProcess('Optical', Path('./output'))

# Get RH data
df_RH = met_data[['RH']]

# IMPROVE calculation
improve_result = dp_opt.IMPROVE(
    df_mass=df_mass,
    df_RH=df_RH,
    method='revised'
)

# Output
ext_dry = improve_result['dry']   # Dry extinction
ext_wet = improve_result['wet']   # Wet extinction
alwc = improve_result['ALWC']     # Aerosol liquid water contribution
fRH = improve_result['fRH']       # Hygroscopic factor
```

### Closure Comparison

```python
import matplotlib.pyplot as plt

# Measured extinction
ext_measured = neph['Sca_550'] + ae33['Abs_880']

# Calculated extinction
ext_calculated = ext_wet['Total_ext']

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
ri_result = dp_chem.volume_RI(df_chem)
df_RI = ri_result['RI']  # n, k columns
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
ri_retrieved = dp_opt.retrieve_RI(
    df_optical=df_optical,  # Sca, Abs columns
    df_pnsd=df_pnsd,
    dlogdp=psd.dlogdp,
    wavelength=550
)

# Output
n_retrieved = ri_retrieved['n']  # Real part
k_retrieved = ri_retrieved['k']  # Imaginary part

print(f"Retrieved RI: {n_retrieved.mean():.3f} + {k_retrieved.mean():.4f}i")
```

---

## Derived Optical Parameters

```python
# Calculate derived parameters
derived = dp_opt.derived(
    df_sca=neph[['Sca_550']],
    df_abs=ae33[['Abs_880']],
    df_ec=ocec[['EC']],
    df_no2=gas[['NO2']],
    df_temp=met[['Temp']]
)

# Output
print(derived.columns)
# ['PG', 'MAC', 'Ox', 'Vis_cal', 'fRH_IMPR', 'OCEC_ratio', 'PM1_PM25']

# Single scattering albedo
SSA = derived['Sca'] / (derived['Sca'] + derived['Abs'])
```

---

## Complete Closure Analysis Script

```python
from datetime import datetime
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from AeroViz import RawDataReader
from AeroViz.dataProcess import DataProcess
from AeroViz.dataProcess.SizeDistr import SizeDist

# 1. Read all data
neph = RawDataReader('NEPH', Path('./data'), ...)
ae33 = RawDataReader('AE33', Path('./data'), ...)
smps = RawDataReader('SMPS', Path('./data'), ...)
df_chem = pd.read_csv('chemistry.csv', parse_dates=['time'], index_col='time')
df_RH = pd.read_csv('met.csv', parse_dates=['time'], index_col='time')[['RH']]

# 2. Initialize processors
dp_chem = DataProcess('Chemistry', Path('./output'))
dp_opt = DataProcess('Optical', Path('./output'))

# 3. Mass reconstruction and refractive index
mass = dp_chem.reconstruction_basic(df_chem)['mass']
ri = dp_chem.volume_RI(df_chem)['RI']

# 4. IMPROVE closure
improve = dp_opt.IMPROVE(mass, df_RH, method='revised')
ext_improve = improve['wet']['Total_ext']

# 5. Mie closure
psd = SizeDist(smps, state='dlogdp', weighting='n')
ext_mie = psd.to_extinction(ri, method='internal').sum(axis=1)

# 6. Measured extinction
ext_measured = neph['Sca_550'] + ae33['Abs_880']

# 7. Compare results
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
