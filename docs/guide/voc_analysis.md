# VOC Analysis

Volatile Organic Compounds (VOC) analysis workflow, including OFP and SOAP calculation.

## Data Preparation

```python
from datetime import datetime
from pathlib import Path
from AeroViz import RawDataReader
from AeroViz.dataProcess import DataProcess

# Read VOC data
voc = RawDataReader(
    instrument='VOC',
    path=Path('./data/voc'),
    start=datetime(2024, 1, 1),
    end=datetime(2024, 3, 31),
    mean_freq='1h'
)

# View available species
print(voc.columns.tolist())
# ['Ethane', 'Propane', 'Butane', 'Benzene', 'Toluene', ...]
```

---

## OFP/SOAP Calculation

### Basic Calculation

```python
dp = DataProcess('VOC', Path('./output'))

# Calculate ozone formation potential
result = dp.potential(voc)

# OFP for each species
df_ofp = result['OFP']
print(df_ofp.columns.tolist())
# ['Ethane_OFP', 'Propane_OFP', 'Benzene_OFP', 'Toluene_OFP', ...]

# SOAP for each species
df_soap = result['SOAP']

# Total OFP/SOAP
df_total = result['total']
print(f"Mean total OFP: {df_total['OFP'].mean():.1f} ug O3/m3")
print(f"Mean total SOAP: {df_total['SOAP'].mean():.2f}")
```

---

## Species Contribution Analysis

### Top 10 Contributing Species

```python
# Calculate mean OFP contribution for each species
mean_ofp = df_ofp.mean().sort_values(ascending=False)

# Top 10
top10 = mean_ofp.head(10)
print("Top 10 OFP contributors:")
for species, value in top10.items():
    print(f"  {species}: {value:.1f} ug O3/m3")
```

### Species Contribution Ratio

```python
import matplotlib.pyplot as plt

# Calculate contribution ratio
total_ofp = df_ofp.sum(axis=1)
contribution = df_ofp.div(total_ofp, axis=0) * 100

# Mean contribution ratio
mean_contrib = contribution.mean().sort_values(ascending=False)

# Plot pie chart (Top 8 + Others)
top8 = mean_contrib.head(8)
others = mean_contrib[8:].sum()
plot_data = pd.concat([top8, pd.Series({'Others': others})])

fig, ax = plt.subplots(figsize=(10, 8))
ax.pie(plot_data, labels=plot_data.index, autopct='%1.1f%%')
ax.set_title('OFP Contribution by Species')
plt.show()
```

---

## Analysis by Chemical Category

```python
# Define chemical categories
categories = {
    'Alkanes': ['Ethane', 'Propane', 'Butane', 'Pentane', 'Hexane'],
    'Alkenes': ['Ethene', 'Propene', 'Butene', 'Isoprene'],
    'Aromatics': ['Benzene', 'Toluene', 'Ethylbenzene', 'Xylene'],
    'OVOCs': ['Formaldehyde', 'Acetaldehyde', 'Acetone']
}

# Calculate OFP for each category
category_ofp = {}
for cat, species in categories.items():
    # Find matching columns
    cols = [c for c in df_ofp.columns if any(s in c for s in species)]
    if cols:
        category_ofp[cat] = df_ofp[cols].sum(axis=1)

df_cat_ofp = pd.DataFrame(category_ofp)

# Plot stacked bar chart
fig, ax = plt.subplots(figsize=(12, 6))
df_cat_ofp.resample('D').mean().plot(kind='bar', stacked=True, ax=ax)
ax.set_ylabel('OFP (ug O3/m3)')
ax.set_title('Daily OFP by Chemical Category')
plt.tight_layout()
plt.show()
```

---

## Temporal Variation Analysis

### Diurnal Variation

```python
# Calculate diurnal variation of total OFP
hourly = df_total['OFP'].groupby(df_total.index.hour).agg(['mean', 'std'])

fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(hourly.index, hourly['mean'], 'b-o')
ax.fill_between(hourly.index,
                hourly['mean'] - hourly['std'],
                hourly['mean'] + hourly['std'],
                alpha=0.3)
ax.set_xlabel('Hour')
ax.set_ylabel('OFP (ug O3/m3)')
ax.set_title('Diurnal Variation of Total OFP')
ax.set_xticks(range(0, 24, 3))
plt.show()
```

### Seasonal Variation

```python
# Monthly average
monthly = df_total['OFP'].resample('M').mean()

fig, ax = plt.subplots(figsize=(10, 5))
monthly.plot(kind='bar', ax=ax)
ax.set_ylabel('OFP (ug O3/m3)')
ax.set_title('Monthly Average OFP')
plt.show()
```

---

## OFP vs SOAP Relationship

```python
fig, ax = plt.subplots(figsize=(8, 8))
ax.scatter(df_total['OFP'], df_total['SOAP'], alpha=0.5)
ax.set_xlabel('Total OFP (ug O3/m3)')
ax.set_ylabel('Total SOAP')
ax.set_title('OFP vs SOAP Relationship')

# Correlation
from scipy import stats
r, p = stats.pearsonr(df_total['OFP'].dropna(), df_total['SOAP'].dropna())
ax.text(0.05, 0.95, f'r = {r:.3f}\np < 0.001' if p < 0.001 else f'r = {r:.3f}\np = {p:.3f}',
        transform=ax.transAxes, va='top')
plt.show()
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

# 1. Read VOC data
voc = RawDataReader('VOC', Path('./data/voc'),
                    datetime(2024, 1, 1), datetime(2024, 3, 31))

# 2. Calculate OFP/SOAP
dp = DataProcess('VOC', Path('./output'))
result = dp.potential(voc)

df_ofp = result['OFP']
df_soap = result['SOAP']
df_total = result['total']

# 3. Species contribution analysis
mean_ofp = df_ofp.mean().sort_values(ascending=False)
print("=== Top 5 OFP Contributors ===")
for i, (species, value) in enumerate(mean_ofp.head(5).items(), 1):
    pct = value / df_total['OFP'].mean() * 100
    print(f"{i}. {species}: {value:.1f} ug O3/m3 ({pct:.1f}%)")

# 4. Output results summary
print("\n=== VOC Analysis Summary ===")
print(f"Total OFP: {df_total['OFP'].mean():.1f} +/- {df_total['OFP'].std():.1f} ug O3/m3")
print(f"Total SOAP: {df_total['SOAP'].mean():.2f} +/- {df_total['SOAP'].std():.2f}")

# 5. Plot contribution chart
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# OFP contribution
top10_ofp = mean_ofp.head(10)
axes[0].barh(range(10), top10_ofp.values)
axes[0].set_yticks(range(10))
axes[0].set_yticklabels([s.replace('_OFP', '') for s in top10_ofp.index])
axes[0].set_xlabel('OFP (ug O3/m3)')
axes[0].set_title('Top 10 OFP Contributors')

# Diurnal variation
hourly = df_total['OFP'].groupby(df_total.index.hour).mean()
axes[1].plot(hourly.index, hourly.values, 'b-o')
axes[1].set_xlabel('Hour')
axes[1].set_ylabel('OFP (ug O3/m3)')
axes[1].set_title('Diurnal Pattern')

plt.tight_layout()
plt.savefig('voc_analysis.png', dpi=300)
```

---

## Related Topics

- [Ozone Formation Potential Theory](../theory/ofp.md)
- [VOC API Reference](../api/DataProcess/VOC.md)
