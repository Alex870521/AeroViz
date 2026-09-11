# Visualization Tutorial

AeroViz provides rich visualization tools for aerosol data analysis and publication.

The matplotlib functions return `(fig, ax)`; `timeseries_interactive` returns a
Plotly figure. `scatter`, `box`, `timeseries` and `diurnal_pattern` take a
time-indexed `DataFrame`; `bar`, `violin` and `pie` take pre-aggregated inputs
(described with each function).

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

`box(df, x, y, x_bins=None)` draws `y` grouped by `x`, choosing one of two
modes automatically:

- **Categorical** — `x` is non-numeric (a `'season'` label, say) or `x_bins`
  is omitted: one box per unique value of `x`.
- **Binned** — `x` is numeric and `x_bins` is given: `x` is cut at those edges
  (integer or float, any width, no rounding) and one box is drawn per bin.

```python
import numpy as np
from AeroViz.plot import box

# Categorical: one box per season label
box(data, x='season', y='PM25')

# Binned: PM2.5 by wind-speed bins (0-2, 2-4, ... m/s)
box(data, x='WS', y='PM25', x_bins=np.arange(0, 11, 2))

# Binned with float edges
box(data, x='RH', y='PM25', x_bins=[0, 42.5, 65, 80, 100])
```

> `violin` is the alternative when your data is already *wide* — one column per
> category (see below).

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

### Size-distribution heatmap

```python
# Time × diameter heatmap of a dN/dlogDp matrix (index = time, columns = diameters)
plot.distribution.heatmap_tms(df_pnsd, unit='Number')   # 'Surface' | 'Volume' | 'Extinction'
```

### Extinction contour

```python
# Koschmieder-style fit: extinction as a power law of PM2.5 × gRH,
# drawn as a contour over the PM2.5 / gRH plane.
# df needs the scalar columns 'PM25', 'gRH' and 'Extinction'.
plot.contour(df[['PM25', 'gRH', 'Extinction']])
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

## Styling and saving

Drawing into your own axes, multi-panel layouts, fonts, colour-blind-safe
palettes, journal column widths and `savefig` settings are collected in
[Publication Figures](publication-figures.md).

## Related Topics

- [Plot API Reference](../api/plot/index.md) · [Publication Figures](publication-figures.md)
- [Size Distribution](size_distribution.md) · [Optical Closure](optical_closure.md) · [Chemical Analysis](chemical_analysis.md) · [VOC Analysis](voc_analysis.md)
