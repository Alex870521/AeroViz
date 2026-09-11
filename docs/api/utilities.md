# Utilities

Two helpers under `AeroViz.tools`, exported at package level.

## `DataBase`

```python
from AeroViz import DataBase

df = DataBase(file_path)                 # any CSV: index column 0, parsed as dates
df = DataBase(load_data=True)            # bundled Tunghai chemistry / optical dataset
psd = DataBase(load_PSD=True)            # bundled PNSD dataset
```

`DataBase(file_path=None, load_data=False, load_PSD=False)` is a loader, not a
class you keep around — calling it **returns a DataFrame**. With `file_path` it
reads that CSV (`na_values=('E', 'F', '-', '_', '#', '*')`, `index_col=0`,
`parse_dates=True`). Without a path, exactly one of `load_data` / `load_PSD`
must be `True`; it then loads the bundled local dataset (`Tunghai` or `PNSD`).

## `DataClassifier`

```python
from AeroViz import DataClassifier

mean_df, std_df = DataClassifier(df, by='Season')
mean_df, std_df = DataClassifier(df, by='WS', cut_bins=[0, 2, 4, 6, 10])
mean_df, std_df = DataClassifier(df, by='PM25', qcut=4, labels=['Q1', 'Q2', 'Q3', 'Q4'])
```

`DataClassifier(df, by, df_support=None, cut_bins=None, qcut=None, labels=None)`
groups a DataFrame and returns **two DataFrames** — group means and group
standard deviations — shaped for `AeroViz.plot.bar` / `box` / `violin`.

- `by` is a built-in grouping (`'Hour'`, `'State'`, `'Season'`,
  `'Season_state'`) or any column name.
- If `by` is not a column of `df`, pass `df_support` (a frame carrying the
  time-indexed variables the built-in groupings are derived from).
- `cut_bins` bins a numeric `by` column at fixed edges; `qcut` splits it into
  quantiles; `labels` names the bins.

## API

::: AeroViz.tools.DataBase

::: AeroViz.tools.DataClassifier
