# Publication Figures

General matplotlib practice for turning an AeroViz plot into a journal figure.
Nothing here is specific to AeroViz — every function returns `(fig, ax)` and
accepts `ax=`, so the usual matplotlib workflow applies.

## Draw into your own axes

```python
import matplotlib.pyplot as plt
from AeroViz.plot import scatter

plt.style.use('seaborn-v0_8-paper')

fig, ax = plt.subplots(figsize=(10, 6))
scatter(data, x='BC', y='PM25', ax=ax)
ax.set_title('BC vs PM2.5')
ax.set_xlabel('BC (ug/m3)')
ax.set_ylabel('PM2.5 (ug/m3)')
```

## Multi-panel figures

```python
import numpy as np
from AeroViz import plot
from AeroViz.plot import scatter, box

fig, axes = plt.subplots(2, 2, figsize=(12, 10))

scatter(data, x='BC', y='PM25', ax=axes[0, 0])
box(data, x='month', y='BC', x_bins=np.arange(0, 13, 2), ax=axes[0, 1])
plot.diurnal_pattern(data, y='BC', ax=axes[1, 0])
plot.timeseries(data, y='BC', ax=axes[1, 1])

plt.tight_layout()
```

## Saving

```python
plt.savefig('figure.png', dpi=300, bbox_inches='tight')     # raster
plt.savefig('figure.pdf', format='pdf', bbox_inches='tight') # vector
plt.savefig('figure.svg', format='svg', bbox_inches='tight')
```

## Fonts

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

## Colours

```python
# colour-blind-safe palette
colors = ['#0077BB', '#EE7733', '#009988', '#CC3311']

# or a ColorBrewer map
from matplotlib.cm import get_cmap
cmap = get_cmap('Set2')
```

## Figure widths

Common journal column widths:

| Journal | Single column | Double column |
|---|---|---|
| ACP | 8.3 cm | 17.6 cm |
| ES&T | 8.5 cm | 17.8 cm |
| JGR | 8.4 cm | 17.4 cm |

```python
fig, ax = plt.subplots(figsize=(3.27, 2.5))  # 8.3 cm single column
fig, ax = plt.subplots(figsize=(6.93, 4))    # 17.6 cm double column
```

## Related

- [Visualization](visualization.md) — the AeroViz plot functions and their inputs
- [Plot API](../api/plot/index.md)
