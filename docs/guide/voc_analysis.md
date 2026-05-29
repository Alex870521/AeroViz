# VOC Analysis

Volatile Organic Compounds (VOC) analysis workflow, including OFP and SOAP calculation.

## Data Preparation

!!! note
    `RawDataReader('VOC', ...)` is deprecated — the VOC reader is a thin CSV
    loader. Read the file directly with pandas and pass the DataFrame to
    `voc_potentials`, which validates species against `support_voc.json`.

```python
import pandas as pd
from AeroViz import voc_potentials

# Read VOC data (datetime index in column 0; '-' / 'N.D.' treated as NA)
voc = pd.read_csv('./data/voc/voc.csv', index_col=0, parse_dates=True,
                  na_values=('-', 'N.D.'))
voc.columns = voc.columns.str.strip()

# View available species
print(voc.columns.tolist())
# ['Ethane', 'Propane', 'Butane', 'Benzene', 'Toluene', ...]
```

---

## OFP/SOAP Calculation

### Basic Calculation

```python
# Calculate VOC reactivity potentials
result = voc_potentials(voc)

# Returns a dict with four DataFrames (each time-indexed):
#   result['Conc'] - mass concentration (ug/m3)
#   result['OFP']  - Ozone Formation Potential (ug O3/m3)
#   result['SOAP'] - Secondary Organic Aerosol Potential
#   result['LOH']  - OH-reactivity (loss rate)
# Each frame's columns are the individual species PLUS per-class totals
# (e.g. 'aromatic_total', 'alkane_total') and a grand 'Total' column.
df_ofp = result['OFP']
df_soap = result['SOAP']

# Grand totals live in the 'Total' column of each frame:
print(f"Mean total OFP: {df_ofp['Total'].mean():.1f} ug O3/m3")
print(f"Mean total SOAP: {df_soap['Total'].mean():.2f}")
```

---

## Species Contribution Analysis

### Top 10 Contributing Species

```python
# Drop the aggregate columns ('Total' and the per-class '*_total' columns)
# so we rank only individual species.
species_cols = [c for c in df_ofp.columns
                if c != 'Total' and not c.endswith('_total')]

# Calculate mean OFP contribution for each species
mean_ofp = df_ofp[species_cols].mean().sort_values(ascending=False)

# Top 10
top10 = mean_ofp.head(10)
print("Top 10 OFP contributors:")
for species, value in top10.items():
    print(f"  {species}: {value:.1f} ug O3/m3")
```

### Species Contribution Ratio

```python
import matplotlib.pyplot as plt

# Calculate contribution ratio (use the 'Total' column as the denominator,
# and only individual species in the numerator)
contribution = df_ofp[species_cols].div(df_ofp['Total'], axis=0) * 100

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
total_ofp = df_ofp['Total']
hourly = total_ofp.groupby(total_ofp.index.hour).agg(['mean', 'std'])

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
monthly = df_ofp['Total'].resample('ME').mean()

fig, ax = plt.subplots(figsize=(10, 5))
monthly.plot(kind='bar', ax=ax)
ax.set_ylabel('OFP (ug O3/m3)')
ax.set_title('Monthly Average OFP')
plt.show()
```

---

## OFP vs SOAP Relationship

```python
total_ofp = result['OFP']['Total']
total_soap = result['SOAP']['Total']

fig, ax = plt.subplots(figsize=(8, 8))
ax.scatter(total_ofp, total_soap, alpha=0.5)
ax.set_xlabel('Total OFP (ug O3/m3)')
ax.set_ylabel('Total SOAP')
ax.set_title('OFP vs SOAP Relationship')

# Correlation
from scipy import stats
mask = total_ofp.notna() & total_soap.notna()
r, p = stats.pearsonr(total_ofp[mask], total_soap[mask])
ax.text(0.05, 0.95, f'r = {r:.3f}\np < 0.001' if p < 0.001 else f'r = {r:.3f}\np = {p:.3f}',
        transform=ax.transAxes, va='top')
plt.show()
```

---

## Complete Analysis Script

```python
import pandas as pd
import matplotlib.pyplot as plt
from AeroViz import voc_potentials

# 1. Read VOC data with pandas (datetime index in column 0)
voc = pd.read_csv('./data/voc/voc.csv', index_col=0, parse_dates=True,
                  na_values=('-', 'N.D.'))
voc.columns = voc.columns.str.strip()

# 2. Calculate OFP/SOAP
result = voc_potentials(voc)

df_ofp = result['OFP']      # columns: species + '*_total' classes + 'Total'
df_soap = result['SOAP']
total_ofp = df_ofp['Total']   # grand total OFP, time-indexed Series
total_soap = df_soap['Total']

# 3. Species contribution analysis (rank individual species only)
species_cols = [c for c in df_ofp.columns
                if c != 'Total' and not c.endswith('_total')]
mean_ofp = df_ofp[species_cols].mean().sort_values(ascending=False)
print("=== Top 5 OFP Contributors ===")
for i, (species, value) in enumerate(mean_ofp.head(5).items(), 1):
    pct = value / total_ofp.mean() * 100
    print(f"{i}. {species}: {value:.1f} ug O3/m3 ({pct:.1f}%)")

# 4. Output results summary
print("\n=== VOC Analysis Summary ===")
print(f"Total OFP: {total_ofp.mean():.1f} +/- {total_ofp.std():.1f} ug O3/m3")
print(f"Total SOAP: {total_soap.mean():.2f} +/- {total_soap.std():.2f}")

# 5. Plot contribution chart
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# OFP contribution
top10_ofp = mean_ofp.head(10)
axes[0].barh(range(10), top10_ofp.values)
axes[0].set_yticks(range(10))
axes[0].set_yticklabels(list(top10_ofp.index))
axes[0].set_xlabel('OFP (ug O3/m3)')
axes[0].set_title('Top 10 OFP Contributors')

# Diurnal variation
hourly = total_ofp.groupby(total_ofp.index.hour).mean()
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
