# Visualization Tutorial

AeroViz provides rich visualization tools for aerosol data analysis and publication.

All plot functions take a time-indexed `DataFrame` and return `(fig, ax)`.

## Basic Usage

```python
from AeroViz import plot

# Scatter plot (x / y are column names)
plot.scatter(data, x='BC', y='PM25')

# Time series (y is the column, or list of columns, to plot)
plot.timeseries(data, y='BC')
```

---

## Basic Charts

### Scatter Plot

```python
from AeroViz.plot import scatter

# Basic scatter plot
scatter(data, x='BC', y='PM25')

# With regression line
scatter(data, x='BC', y='PM25', regression=True)

# Color mapping
scatter(data, x='BC', y='PM25', c='RH', cmap='viridis')
```

### Regression Analysis

```python
from AeroViz.plot import linear_regression, multiple_linear_regression

# Linear regression (x, y are column names or lists of columns)
linear_regression(data, x='BC', y='PM25')

# Multiple linear regression (several predictors)
multiple_linear_regression(data, x=['BC', 'NO2', 'O3'], y='PM25')
```

### Box Plot

`box` bins a **numeric** x-axis column into intervals (via `x_bins`) and draws one
box per bin — it does not accept a categorical/string x-axis. Provide a numeric
column for `x` and the bin edges in `x_bins`. Note: edges are rounded to integers
internally, so use **integer edges with a width of 2 or more** (e.g.
`np.arange(0, 11, 2)`; width-1 bins collide after rounding).

```python
import numpy as np
from AeroViz.plot import box

# Boxes of PM2.5 grouped by wind-speed bins (0-2, 2-4, ... m/s)
box(data, x='WS', y='PM25', x_bins=np.arange(0, 11, 2))

# Boxes of PM2.5 grouped by 2-month bins
data['month'] = data.index.month
box(data, x='month', y='PM25', x_bins=np.arange(0, 13, 2))
```

> To split by a true category (e.g. season label), use `violin` instead, which
> takes a wide DataFrame with one column per category (see below).

### Bar Chart

`bar(data_set, data_std, labels, unit, ...)` — `data_set` is a DataFrame indexed
by component name, with one column per group; `data_std` is the matching error
DataFrame (or `None`).

```python
import pandas as pd
from AeroViz.plot import bar

# Component contributions
components = ['AS', 'AN', 'OM', 'EC', 'Soil', 'SS']
data_set = pd.DataFrame({'PM2.5': data[components].mean()})  # index = components
bar(data_set, None, components, 'ug/m3')
```

### Violin Plot

`violin(df, unit, ...)` — `df` is wide, with one column per category and each
column holding that category's observations.

```python
from AeroViz.plot import violin

# Distribution comparison across site types (one column each)
violin(data[['Urban', 'Suburban', 'Rural']], 'ng/m3')
```

### Pie Chart

`pie(data_set, labels, unit, style, ...)` — `data_set` is a dict `{group: values}`
(or a DataFrame), `style` is `'pie'` or `'donut'`.

```python
from AeroViz.plot import pie

# Component proportions. The unit string is rendered as a mathtext label, so
# avoid a bare '%' (it fails to render) — use 'percent' or an escaped r'\%'.
pie({'PM2.5': data[components].mean().tolist()}, components, 'percent', 'donut')
```

---

## Time Analysis Charts

### Time Series

```python
# Single variable
plot.timeseries(data, y='BC')

# Multiple variables on the primary axis
plot.timeseries(data, y=['BC', 'PM25', 'PM10'])

# Quick interactive Plotly view (one trace per column; toggle via legend)
plot.timeseries_interactive(data, columns=['BC', 'PM25'])
```

### Diurnal Variation

```python
# Single variable diurnal pattern (mean +/- spread by hour of day)
plot.diurnal_pattern(data, y='BC')

# Multiple variable comparison
plot.diurnal_pattern(data, y=['BC', 'PM25'])
```

---

## Advanced Charts

### Contour

```python
# 2-D contour of a wide DataFrame (e.g. a size-distribution matrix:
# index = time, columns = diameters)
plot.contour(df_pnsd)
```

### Wind Rose

```python
# wind_rose lives in the meteorology submodule; WS / WD are column names
plot.meteorology.wind_rose(data, WS='WS', WD='WD')

# Color by a pollutant value
plot.meteorology.wind_rose(data, WS='WS', WD='WD', val='BC')

# Conditional bivariate probability function (pollutant by wind sector/speed)
plot.meteorology.CBPF(data, WS='WS', WD='WD', val='BC')
```

### Correlation Matrix

```python
# Correlation heatmap
cols = ['BC', 'PM25', 'PM10', 'NO2', 'O3']
plot.corr_matrix(data[cols])
```

---

## Chart Customization

### Basic Settings

```python
import matplotlib.pyplot as plt

# Set style
plt.style.use('seaborn-v0_8-paper')

# Custom chart
fig, ax = plt.subplots(figsize=(10, 6))
scatter(data, x='BC', y='PM25', ax=ax)
ax.set_title('BC vs PM2.5')
ax.set_xlabel('BC (ug/m3)')
ax.set_ylabel('PM2.5 (ug/m3)')
```

### Multi-panel Figures

```python
import numpy as np

fig, axes = plt.subplots(2, 2, figsize=(12, 10))

scatter(data, x='BC', y='PM25', ax=axes[0, 0])
box(data, x='month', y='BC', x_bins=np.arange(0, 13, 2), ax=axes[0, 1])
plot.diurnal_pattern(data, y='BC', ax=axes[1, 0])
plot.timeseries(data, y='BC', ax=axes[1, 1])

plt.tight_layout()
```

### Saving Figures

```python
# High resolution PNG
plt.savefig('figure.png', dpi=300, bbox_inches='tight')

# Vector formats
plt.savefig('figure.pdf', format='pdf', bbox_inches='tight')
plt.savefig('figure.svg', format='svg', bbox_inches='tight')
```

---

## Publication Quality Settings

### Font Settings

```python
import matplotlib.pyplot as plt

plt.rcParams.update({
    'font.family': 'Arial',
    'font.size': 12,
    'axes.labelsize': 14,
    'axes.titlesize': 16,
    'xtick.labelsize': 12,
    'ytick.labelsize': 12,
    'legend.fontsize': 11,
})
```

### Color Settings

```python
# Use colorblind-friendly palette
colors = ['#0077BB', '#EE7733', '#009988', '#CC3311']

# Or use ColorBrewer
from matplotlib.cm import get_cmap
cmap = get_cmap('Set2')
```

### Figure Dimensions

Common journal requirements:

| Journal | Single Column Width | Double Column Width |
|---------|---------------------|---------------------|
| ACP | 8.3 cm | 17.6 cm |
| ES&T | 8.5 cm | 17.8 cm |
| JGR | 8.4 cm | 17.4 cm |

```python
# Single column figure
fig, ax = plt.subplots(figsize=(3.27, 2.5))  # 8.3 cm

# Double column figure
fig, ax = plt.subplots(figsize=(6.93, 4))    # 17.6 cm
```

---

## Related Topics

- [Plot API Reference](../api/plot/index.md)
- [Example Gallery](../examples/index.md)
