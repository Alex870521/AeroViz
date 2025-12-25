# DataProcess Tutorial

DataProcess is the core data processing engine of AeroViz, providing four specialized modules for processing different types of aerosol data.

## Basic Usage

```python
from pathlib import Path
from AeroViz.dataProcess import DataProcess

# Create processor
dp = DataProcess('SizeDistr', Path('./output'))

# Call method
result = dp.basic(df_pnsd)
```

## Module Overview

| Module | Purpose | Main Methods |
|--------|---------|--------------|
| SizeDistr | Size distribution processing | basic, merge_SMPS_APS_v4, distributions |
| Chemistry | Chemical composition analysis | reconstruction_basic, volume_RI, kappa |
| Optical | Optical property calculation | IMPROVE, Mie, retrieve_RI, derived |
| VOC | VOC reactivity assessment | potential |

---

## SizeDistr Module

### Basic Processing

```python
dp = DataProcess('SizeDistr', Path('./output'))

# Basic statistics
result = dp.basic(df_pnsd)
# result['number']   - Number distribution
# result['surface']  - Surface area distribution
# result['volume']   - Volume distribution
# result['other']    - Mode statistics
```

### SMPS-APS Merging

```python
# v4 version (recommended)
result = dp.merge_SMPS_APS_v4(
    df_smps=smps_data,
    df_aps=aps_data,
    df_pm25=pm25_data  # Optional, for density correction
)

# Output
merged = result['data_dn']           # Merged dN
merged_all = result['data_dndsdv']   # dN, dS, dV
density = result['density']          # Estimated density
```

### Using SizeDist Class

```python
from AeroViz.dataProcess.SizeDistr import SizeDist

# Create object
psd = SizeDist(df_pnsd, state='dlogdp', weighting='n')

# Distribution conversion
surface = psd.to_surface()
volume = psd.to_volume()
extinction = psd.to_extinction(df_RI, method='internal')
dry = psd.to_dry(df_gRH)

# Statistics
props = psd.properties()
stats = psd.mode_statistics()

# Lung deposition
lung = psd.lung_deposition(activity='light')
```

---

## Chemistry Module

### Mass Reconstruction

```python
dp = DataProcess('Chemistry', Path('./output'))

# Basic reconstruction
result = dp.reconstruction_basic(df_chem)
# result['mass']        - Reconstructed mass (AS, AN, OM, EC, Soil, SS)
# result['NH4_status']  - Ammonium status

# Full reconstruction
result = dp.reconstruction_full(df_chem)
```

### Volume and Refractive Index

```python
result = dp.volume_RI(df_chem)
# result['volume']  - Volume fraction of each component
# result['RI']      - Refractive index (n, k)
```

### Hygroscopicity

```python
result = dp.kappa(df_chem, df_RH)
# result['kappa']  - kappa value
# result['gRH']    - Growth factor
```

### Gas-Particle Partitioning Ratios

```python
result = dp.partition_ratios(df_combined)
# SOR, NOR, NTR, epsilon_ite, epsilon_ss
```

---

## Optical Module

### IMPROVE Extinction

```python
dp = DataProcess('Optical', Path('./output'))

result = dp.IMPROVE(
    df_mass=df_mass,     # Mass concentration
    df_RH=df_RH,         # Relative humidity
    method='revised'     # 'revised' or 'modified'
)

# Output
result['dry']   # Dry extinction
result['wet']   # Wet extinction
result['ALWC']  # Aerosol liquid water contribution
result['fRH']   # Hygroscopic factor
```

### Mie Calculation

```python
result = dp.Mie(
    df_pnsd=df_pnsd,      # Size distribution
    df_m=df_RI,           # Refractive index
    wave_length=550       # Wavelength (nm)
)

# Output
result['extinction']   # Extinction coefficient
result['scattering']   # Scattering coefficient
result['absorption']   # Absorption coefficient
```

### Refractive Index Retrieval

```python
result = dp.retrieve_RI(
    df_optical=df_optical,  # Measured optical properties
    df_pnsd=df_pnsd,        # Size distribution
    wavelength=550
)

# Output
result['n']  # Real part
result['k']  # Imaginary part
```

### Derived Parameters

```python
result = dp.derived(
    df_sca=neph,
    df_abs=ae33,
    df_ec=ocec,
    df_no2=gas,
    df_temp=met
)

# Output columns
# PG, MAC, Ox, Vis_cal, fRH_IMPR, OCEC_ratio, PM1_PM25
```

---

## VOC Module

### OFP/SOAP Calculation

```python
dp = DataProcess('VOC', Path('./output'))

result = dp.potential(df_voc)

# Output
result['OFP']    # OFP for each species
result['SOAP']   # SOAP for each species
result['total']  # Total OFP/SOAP
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

## Output Management

All outputs are saved to the specified output path:

```python
dp = DataProcess('SizeDistr', Path('./output/size'))

# Outputs saved to ./output/size/
```

---

## Related Topics

- [SizeDistr API](../api/DataProcess/SizeDistr.md)
- [Chemistry API](../api/DataProcess/Chemistry.md)
- [Optical API](../api/DataProcess/Optical.md)
- [VOC API](../api/DataProcess/VOC.md)
- [Example Gallery](../examples/index.md)
