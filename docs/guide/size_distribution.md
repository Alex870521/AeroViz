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
from AeroViz import merge_psd

# v4 merging (recommended, with PM2.5 fitness function)
result = merge_psd(
    smps,
    aps,
    df_pm25=pm25_data,   # required for version=4
    version=4,
)

# Output
merged_pnsd = result['data_dn']       # Merged dN
merged_dndsdv = result['data_dndsdv'] # dN, dS, dV distributions
density = result['density']           # Estimated particle density
```

### Merging Parameter Description

| Parameter | Description |
|-----------|-------------|
| `version` | Algorithm version: 1, 2, 3, or 4 (default 4, recommended) |
| `df_pm25` | PM2.5 reference DataFrame (required for `version=4`) |
| `aps_unit` | `'um'` (default) or `'nm'` |
| `smps_overlap_lowbound` | SMPS bin lower bound for overlap region (nm, default 500) |
| `aps_fit_highbound` | APS bin upper bound for power-law fit (nm, default 1000) |
| `shift_mode` | APS diameter shift mode (`version=1` only) |
| `dndsdv_alg` | Apply dN/dS/dV correlation refinement (`version >= 3`) |

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
from AeroViz import reconstruct_mass, volume_ri

# Calculate refractive index from chemical composition
mass_result = reconstruct_mass(df_chem)
df_RI = volume_ri(mass_result['volume'])   # n_dry, k_dry, n_amb, k_amb, gRH

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
from AeroViz import growth_factor

# Calculate growth factor (needs total_dry + ALWC)
df_gRH = growth_factor(mass_result['volume'], df_alwc)

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
from AeroViz import RawDataReader, merge_psd
from AeroViz.dataProcess.SizeDistr import SizeDist

# 1. Read data
smps = RawDataReader('SMPS', Path('./data/smps'),
                     datetime(2024,1,1), datetime(2024,3,31))
aps = RawDataReader('APS', Path('./data/aps'),
                    datetime(2024,1,1), datetime(2024,3,31))
pm25 = RawDataReader('TEOM', Path('./data/teom'),
                     datetime(2024,1,1), datetime(2024,3,31))[['PM_Total']]

# 2. Merge SMPS-APS (v4 requires PM2.5 reference)
merged = merge_psd(smps, aps, df_pm25=pm25, version=4)
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
