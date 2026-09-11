# Quality Control

`QualityControl` (`AeroViz/rawDataReader/core/qc.py`) holds the statistical
filters the readers' QC rules are built from, and `QCRule` / `QCFlagBuilder`
turn a list of rules into the `QC_Flag` / `QC_Invalid` columns.

How rules, severities, the verdict and the summary fit together is explained
once, in [RawDataReader Reference §2](../guide/reader-reference.md#2-qc-machinery);
the per-instrument rule lists live on each
[instrument page](instruments/index.md). This page covers calling the filters
directly on your own data.

## Declaring a rule

```python
from AeroViz.rawDataReader.core import QCRule

QCRule(
    name='Invalid BC',
    condition=lambda df: (df['BC6'] <= 0) | (df['BC6'] > 20000),   # True where the row FAILS
    description='BC outside 0-20000 ng/m³',
    # severity='error' is the default: the row is masked to NaN in the output
)

QCRule(
    name='Below MDL',
    condition=lambda df: df['Thermal_OC'] <= 0.3,
    description='At or below the method detection limit',
    severity='warning',   # advisory: recorded and logged, value kept
)
```

`QCFlagBuilder.apply(df)` evaluates every rule as a vectorised mask and writes
`QC_Flag` (every rule that fired, comma-joined, or `"Valid"`) and `QC_Invalid`
(`True` iff an `'error'` rule fired). `get_summary(df)` reports count and
percentage per rule plus the `Valid` and `Usable` totals. Reclassify a rule per
run with `RawDataReader(..., flag_severity={'Insufficient': 'error'})`.

## Filters

```python
from AeroViz.rawDataReader.core.qc import QualityControl
import numpy as np

qc = QualityControl()
```

### Statistical outliers

```python
cleaned = qc.n_sigma(df, std_range=3)                 # N standard deviations
cleaned = qc.iqr(df)                                  # interquartile range
cleaned = qc.iqr(df, log_dist=True)                   # IQR on log-transformed data
cleaned = qc.time_aware_rolling_iqr(df, window_size='24h', iqr_factor=3.0, min_periods=5)
```

### Trend-aware outliers

```python
outlier_mask = qc.bidirectional_trend_std_QC(
    df, window_size='6h', std_factor=3.0, trend_window='30min', trend_factor=2.0)
final_df = df.where(~outlier_mask, np.nan)
```

### Spikes

```python
spike_mask = qc.spike_detection(df['PM_Total'])       # change > 3 × median |Δ|, or a sharp up-down reversal
```

### Instrument status

`filter_error_status` supports four `status_type` modes — `bitwise` (AE33,
AE43, BC1054, MA350, TEOM), `numeric` (Aurora, NEPH), `text` (SMPS) and
`binary_string` (APS). `ignored_values` is the whitelist that `RawDataReader`
exposes as `ignored_status_errors`, interpreted in the active mode; see
[status modes](../guide/reader-reference.md#3-how-a-status-judgement-is-made).

```python
# bitwise: drop one warning bit from the error definition
# (e.g. ignore the TEOM "Dryer A" status bit 0x20000000)
error_mask = qc.filter_error_status(
    df, error_codes=[1 << b for b in range(32)],
    status_column='status', status_type='bitwise',
    ignored_values=[536870912],
)

# bitwise with special codes (AE33-style)
error_mask = qc.filter_error_status(
    df, error_codes=[1, 2, 4, 16, 32], special_codes=[1024, 2048, 4096])

# text: whitelist comma-split tokens (SMPS)
error_mask = qc.filter_error_status(
    df, status_column='Instrument Errors', status_type='text',
    ok_value='', ignored_values=['Low aerosol flow', 'Neutralizer not active'],
)
qc_df = df.where(~error_mask, np.nan)
```

### Completeness

```python
# fraction of the points an hour could hold at the given frequency
completeness_mask = qc.hourly_completeness_QC(df, freq='6min', threshold=0.75)
```

## API

::: AeroViz.rawDataReader.core.qc.QualityControl
    options:
        show_source: false
        show_bases: false
        show_inheritance_diagram: false
        members_order: source
        show_if_no_docstring: false
        filters:
            - "!^_"
        docstring_section_style: table
        heading_level: 3
        show_signature_annotations: true
        separate_signature: true
        group_by_category: true
        show_category_heading: true

## Related

- [AbstractReader](AbstractReader.md) — the base class that calls these filters
- [RawDataReader](RawDataReader/index.md) — the factory with `qc=`, `flag_severity=`, `ignored_status_errors=`
