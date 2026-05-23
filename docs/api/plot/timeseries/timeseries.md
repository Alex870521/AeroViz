::: AeroViz.plot.timeseries

## Interactive viewer

`timeseries_interactive` renders an interactive Plotly chart for a
`RawDataReader` result — one trace per column, with the legend acting as the
column selector (click an entry to show/hide it). Pan, zoom, hover and a time
range-slider are built in, and the figure can be saved as a standalone HTML
file.

```python
from AeroViz import RawDataReader
from AeroViz.plot import timeseries_interactive

df = RawDataReader('AE33', '/data/AE33')          # native resolution, full coverage
timeseries_interactive(df, columns=['eBC', 'BC1', 'BC6', 'AAE'])  # click legend to toggle
timeseries_interactive(df, save='ae33.html', show=False)          # export to HTML
```

::: AeroViz.plot.timeseries_interactive
