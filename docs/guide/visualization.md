# Visualization Tutorial

AeroViz provides rich visualization tools for aerosol data analysis and publication.

## Basic Usage

```python
from AeroViz import plot

# Scatter plot
plot.scatter(data, x='BC', y='PM25')

# Time series
plot.time_series(data, 'BC')
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
from AeroViz.plot import regression

# Linear regression
regression(data, x='BC', y='PM25', method='linear')

# Polynomial regression
regression(data, x='BC', y='PM25', method='polynomial', degree=2)
```

### Box Plot

```python
from AeroViz.plot import box

# Group by category
box(data, x='season', y='BC')

# By month
data['month'] = data.index.month
box(data, x='month', y='PM25')
```

### Bar Chart

```python
from AeroViz.plot import bar

# Component contributions
components = ['AS', 'AN', 'OM', 'EC', 'Soil', 'SS']
bar(data[components].mean(), ylabel='Mass (ug/m3)')
```

### Violin Plot

```python
from AeroViz.plot import violin

# Distribution comparison
violin(data, x='season', y='BC')
```

### Pie Chart

```python
from AeroViz.plot import pie

# Component proportions
pie(data[components].mean(), labels=components)
```

---

## Time Analysis Charts

### Time Series

```python
# Single variable
plot.time_series(data, 'BC')

# Multiple variables
plot.time_series(data, ['BC', 'PM25', 'PM10'])
```

### Diurnal Variation

```python
# Single variable diurnal pattern
plot.diurnal(data, 'BC')

# Multiple variable comparison
plot.diurnal(data, ['BC', 'PM25'])
```

### Weekly Variation

```python
plot.weekly(data, 'BC')
```

### Monthly Variation

```python
plot.monthly(data, 'BC')
```

---

## Advanced Charts

### Size Distribution

```python
# Time-size contour plot
plot.size_contour(df_pnsd)

# Average distribution
plot.size_distribution(df_pnsd.mean())
```

### Polar Plots

```python
# Wind rose
plot.wind_rose(data, ws='WS', wd='WD')

# Polar pollutant plot
plot.polar(data, pollutant='BC', ws='WS', wd='WD')
```

### Correlation Matrix

```python
# Correlation heatmap
vars = ['BC', 'PM25', 'PM10', 'NO2', 'O3']
plot.correlation_matrix(data[vars])
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
fig, axes = plt.subplots(2, 2, figsize=(12, 10))

scatter(data, 'BC', 'PM25', ax=axes[0,0])
box(data, 'season', 'BC', ax=axes[0,1])
plot.diurnal(data, 'BC', ax=axes[1,0])
plot.monthly(data, 'BC', ax=axes[1,1])

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
