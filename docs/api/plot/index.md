# Plot

`AeroViz.plot` needs the `plot` extra (`pip install "AeroViz[plot]"`). The
matplotlib functions return `(fig, ax)` and accept `ax=` to draw into an
existing axis; `timeseries_interactive` returns a Plotly figure.

| Page | Functions |
|---|---|
| [Basic charts](basic.md) | `scatter`, `linear_regression`, `multiple_linear_regression`, `box`, `bar`, `violin`, `pie`, `donuts`, `radar` |
| [Time series](timeseries.md) | `timeseries`, `timeseries_stacked`, `timeseries_template`, `timeseries_interactive` |
| [Size distribution](distribution.md) | `plot_dist`, `heatmap`, `heatmap_tms`, `three_dimension`, `curve_fitting` |
| [Meteorology](meteorology.md) | `meteorology.wind_rose`, `meteorology.CBPF`, `meteorology.hysplit` |
| [Optical](optical.md) | `optical.Q_plot`, `optical.RI_couple`, `optical.RRI_2D`, `optical.scattering_phase`, `optical.response_surface` |
| [Templates](templates.md) | `diurnal_pattern`, `corr_matrix`, `cross_corr_matrix`, `contour`, `koschmieder`, `ammonium_rich`, `metal_heatmaps` |

Worked usage — which input shape each function wants, the two `box` modes,
multi-panel figures — is in the guide: [Visualization](../../guide/visualization.md);
journal-ready styling is in [Publication figures](../../guide/publication-figures.md).
A picture of what each family produces is on the [home page gallery](../../index.md#gallery).

## Quick reference

```python
from AeroViz import plot

plot.timeseries(data, y='BC')                       # one column, or a list; y2= for a second axis
plot.timeseries(data, y=['BC', 'PM2.5', 'PM10'])
plot.scatter(data, x='BC', y='PM2.5', c='PM10', s='PM1')   # c colours points, s sizes them
plot.box(data, x='WS', y='PM2.5', x_bins=np.arange(0, 11, 2))   # binned; omit x_bins for categorical x
plot.diurnal_pattern(data, y='BC')                  # mean ± spread by hour of day
```

Common parameters: `df` / `data` (time-indexed DataFrame for the time-series
style functions), `ax` (existing axis, optional), `title`; `timeseries` adds
`y2` (secondary axis) and `rolling` (window smoothing); `scatter` adds `c`
(colour column) and `s` (size column).
