# Size Distribution Analysis

A complete size distribution processing workflow, including SMPS-APS merging, distribution conversion, mode statistics, and lung deposition calculation.

## Data Preparation

### Reading SMPS and APS Data

```python
from datetime import datetime
from pathlib import Path
from AeroViz import RawDataReader

# Read SMPS (10-600 nm)
smps = RawDataReader(
    instrument='SMPS',
    path=Path('/path/to/smps'),
    start=datetime(2024, 1, 1),
    end=datetime(2024, 3, 31),
    mean_freq='1h'
)

# Read APS (0.5-20 um)
aps = RawDataReader(
    instrument='APS',
    path=Path('/path/to/aps'),
    start=datetime(2024, 1, 1),
    end=datetime(2024, 3, 31),
    mean_freq='1h'
)
```

---

## SMPS-APS Merging

### Basic Merging

```python
from AeroViz.dataProcess import DataProcess

dp = DataProcess('SizeDistr', Path('./output'))

# v4 merging (recommended, with PM2.5 correction)
result = dp.merge_SMPS_APS_v4(
    df_smps=smps,
    df_aps=aps,
    df_pm25=pm25_data  # Optional, for density correction
)

# Output
merged_pnsd = result['data_dn']       # Merged dN
merged_dndsdv = result['data_dndsdv'] # dN, dS, dV distributions
density = result['density']           # Estimated particle density
```

### Merging Parameter Description

| Parameter | Description |
|-----------|-------------|
| `overlap_range` | SMPS-APS overlap range (default 500-700 nm) |
| `shift_mode` | APS diameter shift mode |
| `density_range` | Density search range (default 1.0-2.5 g/cm3) |

---

## Distribution Conversion and Statistics

### Using SizeDist Class

```python
from AeroViz.dataProcess.SizeDistr import SizeDist

# Create PSD object
psd = SizeDist(merged_pnsd, state='dlogdp', weighting='n')

# Distribution conversion
surface = psd.to_surface()  # Surface area distribution (nm2/cm3)
volume = psd.to_volume()    # Volume distribution (nm3/cm3)

# Basic statistics
props = psd.properties()
print(f"Total N: {props['total_n']:.0f} #/cm3")
print(f"GMD: {props['GMD_n']:.1f} nm")
print(f"GSD: {props['GSD_n']:.2f}")
```

### Mode Statistics

```python
# Calculate mode statistics
stats = psd.mode_statistics()

# Mode distributions
nucleation = stats['number']['Nucleation']   # 10-25 nm
aitken = stats['number']['Aitken']           # 25-100 nm
accumulation = stats['number']['Accumulation']  # 100-1000 nm
coarse = stats['number']['Coarse']           # 1000-2500 nm

# Statistical summary
summary = stats['statistics']
print(summary)
#                 GMD    GSD   total    mode
# Nucleation     18.2   1.45    2500    17.5
# Aitken         52.3   1.62    5200    48.0
# Accumulation  185.0   1.85    1800   160.0
# Coarse        1850    2.10     120  1500.0
```

---

## Extinction Distribution Calculation

### Requires Refractive Index Data

```python
# Calculate refractive index from chemical composition
dp_chem = DataProcess('Chemistry', Path('./output'))
ri_result = dp_chem.volume_RI(df_chem)
df_RI = ri_result['RI']  # n, k columns

# Calculate extinction distribution
ext_dist = psd.to_extinction(
    RI=df_RI,
    method='internal',      # Mixing mode
    result_type='extinction'
)
```

---

## Dry PSD Calculation

### Hygroscopic Correction

```python
# Calculate growth factor
kappa_result = dp_chem.kappa(df_chem, df_RH)
df_gRH = kappa_result[['gRH']]

# Convert to dry PSD
dry_psd = psd.to_dry(df_gRH, uniform=True)
```

---

## Lung Deposition Calculation

### ICRP 66 Model

```python
# Calculate lung deposition
lung = psd.lung_deposition(activity='light')

# Deposition fractions
df_fraction = lung['DF']
print(df_fraction.mean())
#    HA     TB     AL    Total
# 0.025  0.082  0.245    0.352

# Regional dose
dose = lung['dose']
print(f"Alveolar dose: {dose['AL'].mean():.0f} #/cm3")

# Deposited distribution
deposited = lung['deposited']  # Number deposited at each size
```

### Activity Level Comparison

```python
activities = ['sleep', 'sitting', 'light', 'heavy']
results = {}

for act in activities:
    result = psd.lung_deposition(activity=act)
    results[act] = result['total_dose'].mean()

print("Total deposition by activity:")
for act, dose in results.items():
    print(f"  {act}: {dose:.0f} #/cm3")
```

---

## Complete Example Script

```python
from datetime import datetime
from pathlib import Path
from AeroViz import RawDataReader
from AeroViz.dataProcess import DataProcess
from AeroViz.dataProcess.SizeDistr import SizeDist

# 1. Read data
smps = RawDataReader('SMPS', Path('./data/smps'),
                     datetime(2024,1,1), datetime(2024,3,31))
aps = RawDataReader('APS', Path('./data/aps'),
                    datetime(2024,1,1), datetime(2024,3,31))

# 2. Merge SMPS-APS
dp = DataProcess('SizeDistr', Path('./output'))
merged = dp.merge_SMPS_APS_v4(smps, aps)
df_pnsd = merged['data_dn']

# 3. Create SizeDist object
psd = SizeDist(df_pnsd, state='dlogdp', weighting='n')

# 4. Distribution conversion
surface = psd.to_surface()
volume = psd.to_volume()

# 5. Statistical analysis
props = psd.properties()
stats = psd.mode_statistics()

# 6. Lung deposition
lung = psd.lung_deposition(activity='light')

# 7. Output results
print(f"Average total N: {props['total_n'].mean():.0f} #/cm3")
print(f"Average GMD: {props['GMD_n'].mean():.1f} nm")
print(f"Average lung deposition: {lung['total_dose'].mean():.0f} #/cm3")
```

---

## Related Topics

- [Log-normal Distribution Theory](../theory/lognormal.md)
- [ICRP 66 Lung Deposition Model](../theory/icrp.md)
- [SizeDistr API Reference](../api/DataProcess/SizeDistr.md)
