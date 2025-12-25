# Chemical Composition Analysis

Chemical composition analysis workflow, including mass reconstruction, ion balance, hygroscopicity calculation, and gas-particle partitioning ratios.

## Data Preparation

```python
from datetime import datetime
from pathlib import Path
import pandas as pd
from AeroViz import RawDataReader
from AeroViz.dataProcess import DataProcess

# Read ion data
igac = RawDataReader(
    instrument='IGAC',
    path=Path('./data/igac'),
    start=datetime(2024, 1, 1),
    end=datetime(2024, 3, 31)
)

# Read carbon component data
ocec = RawDataReader(
    instrument='OCEC',
    path=Path('./data/ocec'),
    start=datetime(2024, 1, 1),
    end=datetime(2024, 3, 31)
)

# Read elemental data (Xact 625i)
xact = RawDataReader(
    instrument='Xact',
    path=Path('./data/xrf'),
    start=datetime(2024, 1, 1),
    end=datetime(2024, 3, 31)
)

# Merge data
df_chem = pd.concat([igac, ocec, xact], axis=1)
```

---

## Mass Reconstruction

### Basic Reconstruction

```python
dp = DataProcess('Chemistry', Path('./output'))

# Perform mass reconstruction
result = dp.reconstruction_basic(df_chem)

# Main component masses
df_mass = result['mass']
print(df_mass.columns)
# ['AS', 'AN', 'OM', 'EC', 'Soil', 'SS', 'PM25_rc']

# Ammonium status
nh4_status = result['NH4_status']
print(nh4_status.value_counts())
# Balance      45
# Excess       30
# Deficiency   15
```

### Closure Check

```python
# Calculate closure
closure = df_mass['PM25_rc'] / df_chem['PM25'] * 100

print(f"Mean closure: {closure.mean():.1f}%")
print(f"Std closure: {closure.std():.1f}%")

# Closure distribution
import matplotlib.pyplot as plt
plt.hist(closure, bins=20, edgecolor='black')
plt.xlabel('Closure (%)')
plt.ylabel('Frequency')
plt.axvline(100, color='r', linestyle='--', label='100%')
plt.legend()
plt.show()
```

### Component Contributions

```python
# Calculate contribution ratios for each component
components = ['AS', 'AN', 'OM', 'EC', 'Soil', 'SS']
contributions = df_mass[components].div(df_mass['PM25_rc'], axis=0) * 100

print("Average contribution (%):")
print(contributions.mean())
# AS      25.3
# AN      18.2
# OM      35.1
# EC       8.5
# Soil     7.2
# SS       5.7
```

---

## Volume and Refractive Index Calculation

```python
# Calculate volume fraction and refractive index
vol_ri = dp.volume_RI(df_chem)

# Volume fraction
df_volume = vol_ri['volume']
print(df_volume.columns)
# ['AS_volume', 'AN_volume', 'OM_volume', 'EC_volume', 'Soil_volume', 'SS_volume']

# Refractive index
df_RI = vol_ri['RI']
print(f"Mean n: {df_RI['n'].mean():.3f}")
print(f"Mean k: {df_RI['k'].mean():.4f}")
```

---

## Hygroscopicity (kappa) Calculation

```python
# Requires RH data
df_RH = met_data[['RH']]

# Calculate kappa and growth factor
kappa_result = dp.kappa(df_chem, df_RH)

# kappa value
df_kappa = kappa_result['kappa']
print(f"Mean kappa: {df_kappa.mean():.3f}")

# Growth factor
df_gRH = kappa_result['gRH']
print(f"Mean gRH at RH=80%: {df_gRH.mean():.2f}")
```

### kappa vs Composition Relationship

```python
# Analyze relationship between kappa and chemical composition
fig, axes = plt.subplots(1, 3, figsize=(12, 4))

# kappa vs SIA ratio
sia_ratio = (df_mass['AS'] + df_mass['AN']) / df_mass['PM25_rc']
axes[0].scatter(sia_ratio, df_kappa, alpha=0.5)
axes[0].set_xlabel('SIA / PM2.5')
axes[0].set_ylabel('kappa')

# kappa vs OM ratio
om_ratio = df_mass['OM'] / df_mass['PM25_rc']
axes[1].scatter(om_ratio, df_kappa, alpha=0.5)
axes[1].set_xlabel('OM / PM2.5')
axes[1].set_ylabel('kappa')

# kappa vs RH
axes[2].scatter(df_RH['RH'], df_kappa, alpha=0.5)
axes[2].set_xlabel('RH (%)')
axes[2].set_ylabel('kappa')

plt.tight_layout()
plt.show()
```

---

## Gas-Particle Partitioning Ratios

```python
# Requires gas data
df_gas = gas_data[['SO2', 'NO2', 'HNO3', 'NH3']]
df_combined = pd.concat([df_chem, df_gas], axis=1)

# Calculate partitioning ratios
partition = dp.partition_ratios(df_combined)

print(partition.columns)
# ['SOR', 'NOR', 'NTR', 'epsilon_ite', 'epsilon_ss']
```

### Partitioning Ratio Description

| Indicator | Formula | Meaning |
|-----------|---------|---------|
| SOR | SO4^2-/(SO4^2-+SO2) | Sulfate conversion degree |
| NOR | NO3-/(NO3-+NO2) | Nitrate conversion degree |
| NTR | NO3-/(NO3-+HNO3) | Nitrate partitioning |
| epsilon_ite | NO3-/(NO3-+Cl-) | Nitrate vs chloride |

```python
# Analyze diurnal variation of SOR and NOR
hourly_sor = partition['SOR'].groupby(partition.index.hour).mean()
hourly_nor = partition['NOR'].groupby(partition.index.hour).mean()

fig, ax = plt.subplots()
ax.plot(hourly_sor.index, hourly_sor.values, 'b-o', label='SOR')
ax.plot(hourly_nor.index, hourly_nor.values, 'r-o', label='NOR')
ax.set_xlabel('Hour')
ax.set_ylabel('Ratio')
ax.legend()
plt.show()
```

---

## OC/EC Ratio Analysis

```python
# OC/EC analysis
ocec_result = dp.ocec_ratio(df_chem[['OC', 'EC']])

# OC/EC ratio
ratio = ocec_result['ratio']
print(f"Mean OC/EC: {ratio.mean():.2f}")

# SOC estimation
soc = ocec_result['SOC']
print(f"Mean SOC: {soc.mean():.2f} ug/m3")
```

---

## Complete Analysis Script

```python
from datetime import datetime
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from AeroViz import RawDataReader
from AeroViz.dataProcess import DataProcess

# 1. Read data
igac = RawDataReader('IGAC', Path('./data'), ...)
ocec = RawDataReader('OCEC', Path('./data'), ...)
df_chem = pd.concat([igac, ocec], axis=1)
df_RH = pd.read_csv('met.csv', index_col='time', parse_dates=True)[['RH']]

# 2. Initialize processor
dp = DataProcess('Chemistry', Path('./output'))

# 3. Mass reconstruction
mass_result = dp.reconstruction_basic(df_chem)
df_mass = mass_result['mass']

# 4. Volume and refractive index
vol_ri = dp.volume_RI(df_chem)
df_RI = vol_ri['RI']

# 5. Hygroscopicity
kappa_result = dp.kappa(df_chem, df_RH)
df_kappa = kappa_result['kappa']
df_gRH = kappa_result['gRH']

# 6. Output results summary
print("=== Chemical Analysis Summary ===")
print(f"PM2.5: {df_chem['PM25'].mean():.1f} +/- {df_chem['PM25'].std():.1f} ug/m3")
print(f"Closure: {(df_mass['PM25_rc']/df_chem['PM25']*100).mean():.1f}%")
print(f"RI: {df_RI['n'].mean():.3f} + {df_RI['k'].mean():.4f}i")
print(f"kappa: {df_kappa.mean():.3f} +/- {df_kappa.std():.3f}")
```

---

## Related Topics

- [Mass Reconstruction Theory](../theory/mass_reconstruction.md)
- [kappa-Kohler Theory](../theory/kappa.md)
- [Chemistry API Reference](../api/DataProcess/Chemistry.md)
