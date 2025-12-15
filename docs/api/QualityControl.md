# Quality Control

The `QualityControl` class provides comprehensive data quality assessment and outlier detection methods for aerosol
instrument data.

## Overview

Quality control is essential for ensuring data reliability in aerosol measurements. The QualityControl class offers
various statistical methods to identify and handle outliers, invalid measurements, and data quality issues.

## Key Features

- **QCFlagBuilder System** - Declarative rule-based quality control
- **Multiple Outlier Detection Methods** - N-sigma, IQR, time-aware rolling methods
- **Flexible Thresholds** - Configurable parameters for different data types
- **Time-Aware Processing** - Considers temporal patterns in data
- **Status Code Filtering** - Handles instrument-specific error codes
- **Data Completeness Checks** - Validates temporal coverage requirements

## QCFlagBuilder System

All instruments use the declarative **QCFlagBuilder** system for quality control. This system provides:

- **Declarative Rules** - Define QC rules as simple dataclass instances
- **Consistent Processing** - All instruments use `QC_Flag` internally for quality control
- **Transparent Results** - Failed rules are clearly listed in the flag
- **Clean Output** - Final output has invalid data set to NaN, `QC_Flag` column removed

### QCRule Dataclass

```python
from dataclasses import dataclass
from typing import Callable
import pandas as pd

@dataclass
class QCRule:
    name: str                           # Rule identifier (e.g., "Invalid BC")
    condition: Callable[[pd.DataFrame], pd.Series]  # Returns True where data fails
    description: str                    # Human-readable description
```

### QCFlagBuilder Class

```python
class QCFlagBuilder:
    def __init__(self, rules: list[QCRule]):
        self.rules = rules

    def build(self, df: pd.DataFrame) -> pd.Series:
        """Build QC flag column from rules."""
        flags = pd.Series("Valid", index=df.index)

        for rule in self.rules:
            mask = rule.condition(df)
            for idx in df.index[mask]:
                current = flags.loc[idx]
                if current == "Valid":
                    flags.loc[idx] = rule.name
                else:
                    flags.loc[idx] = f"{current}, {rule.name}"

        return flags
```

### Usage Example

```python
from AeroViz.rawDataReader.core.qc import QCRule, QCFlagBuilder

# Define QC rules
rules = [
    QCRule(
        name="Invalid Range",
        condition=lambda df: (df['value'] < 0) | (df['value'] > 1000),
        description="Value outside valid range (0-1000)"
    ),
    QCRule(
        name="Missing Data",
        condition=lambda df: df['value'].isna(),
        description="Value is missing"
    ),
]

# Build flags
builder = QCFlagBuilder(rules)
df['QC_Flag'] = builder.build(df)

# Results:
# - "Valid" if all rules pass
# - "Invalid Range" if only range check fails
# - "Invalid Range, Missing Data" if both fail
```

### Instrument QC Rules Summary

| Instrument | QC Rules |
|------------|----------|
| **AE33/AE43** | Status Error, Invalid BC, Invalid AAE, Insufficient |
| **BC1054** | Status Error, Invalid BC, Invalid AAE, Insufficient |
| **MA350** | Status Error, Invalid BC, Invalid AAE, Insufficient |
| **SMPS** | Status Error, Insufficient, Low Total, High Bin, High Large Bin |
| **APS** | Status Error, Insufficient, Low Total, High Total |
| **NEPH/Aurora** | No Data, Invalid Scat Value, Invalid Scat Rel, Insufficient |
| **TEOM** | High Noise, Negative/Zero, NV > Total, Invalid Vol Frac, Std Outlier, Insufficient |
| **BAM1020** | Invalid Range, IQR Outlier |
| **OCEC** | Invalid Range, Below MDL, IQR Outlier, Missing OC |
| **IGAC** | Mass Closure, Missing Main, Below MDL, Ion Balance |
| **EPA** | Negative Value |

## Methods

### Statistical Outlier Detection

#### N-Sigma Method

```python
from AeroViz.rawDataReader.core.qc import QualityControl

qc = QualityControl()
cleaned_data = qc.n_sigma(df, std_range=3)
```

#### Interquartile Range (IQR) Method

```python
# Basic IQR
cleaned_data = qc.iqr(df)

# With log transformation
cleaned_data = qc.iqr(df, log_dist=True)
```

#### Time-Aware Rolling IQR

```python
# Rolling IQR with time awareness
cleaned_data = qc.time_aware_rolling_iqr(
    df,
    window_size='24h',
    iqr_factor=3.0,
    min_periods=5
)
```

### Advanced Quality Control

#### Bidirectional Trend Analysis

```python
# Detect outliers while considering data trends
outlier_mask = qc.bidirectional_trend_std_QC(
    df,
    window_size='6h',
    std_factor=3.0,
    trend_window='30min',
    trend_factor=2.0
)
```

#### Status Code Filtering

```python
# Filter based on instrument status codes
error_mask = qc.filter_error_status(
    df,
    error_codes=[1, 2, 4, 16],
    special_codes=[384, 1024]
)
```

#### Completeness Validation

```python
# Check hourly data completeness
completeness_mask = qc.hourly_completeness_QC(
    df,
    freq='6min',
    threshold=0.75  # Require 75% data availability
)
```

## Usage Examples

### Basic Outlier Removal

```python
from AeroViz.rawDataReader.core.qc import QualityControl
import pandas as pd

# Load your data
df = pd.read_csv('instrument_data.csv', index_col=0, parse_dates=True)

# Initialize QC
qc = QualityControl()

# Apply basic outlier detection
cleaned_df = qc.n_sigma(df, std_range=3)
```

### Advanced Time-Aware Processing

```python
# For time series with trends
cleaned_df = qc.time_aware_rolling_iqr(
    df,
    window_size='12h',
    iqr_factor=2.5,
    min_periods=10
)

# With bidirectional trend consideration
outlier_mask = qc.bidirectional_trend_std_QC(
    df,
    window_size='6h',
    std_factor=3.0,
    trend_window='1h'
)

# Apply the mask
final_df = df.where(~outlier_mask, np.nan)
```

### Instrument-Specific QC

```python
# For instruments with status codes (e.g., AE33)
error_mask = qc.filter_error_status(
    df,
    error_codes=[1, 2, 4, 16, 32],  # Common error codes
    special_codes=[384, 1024, 2048]  # Specific error conditions
)

# Remove error data
qc_df = df.where(~error_mask, np.nan)
```

## API Reference

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

## Related Documentation

- **[AbstractReader](AbstractReader.md)** - Base class that uses QualityControl methods
- **[RawDataReader](RawDataReader/index.md)** - Factory function with built-in QC options
- **[Instrument Documentation](instruments/index.md)** - Instrument-specific QC procedures
