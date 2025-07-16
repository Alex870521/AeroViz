# Examples

This page provides practical examples of using AeroViz for common aerosol data analysis tasks.

## Basic Data Processing

### Reading and Processing AE33 Data

```python
from datetime import datetime
from pathlib import Path
from AeroViz import RawDataReader, DataProcess, plot

# Read AE33 aethalometer data
data = RawDataReader(
    instrument='AE33',
    path=Path('/path/to/ae33/data'),
    start=datetime(2024, 1, 1),
    end=datetime(2024, 1, 31)
)

# Apply data processing and quality control
processor = DataProcess(data)
processed_data = processor.process()

# Basic time series plot
plot.time_series(processed_data, 'BC')
```

### Multi-Instrument Data Integration

```python
from AeroViz import RawDataReader, DataProcess, plot

# Read data from multiple instruments
ae33_data = RawDataReader(instrument='AE33', path=ae33_path)
smps_data = RawDataReader(instrument='SMPS', path=smps_path)
neph_data = RawDataReader(instrument='NEPH', path=neph_path)

# Process each dataset
ae33_processed = DataProcess(ae33_data).process()
smps_processed = DataProcess(smps_data).process()
neph_processed = DataProcess(neph_data).process()

# Merge datasets by timestamp
merged_data = DataProcess.merge([ae33_processed, smps_processed, neph_processed])

# Multi-panel visualization
plot.multi_panel(merged_data, ['BC', 'total_conc', 'scattering'])
```

## Advanced Analysis

### Seasonal Variation Analysis

```python
from AeroViz import RawDataReader, DataProcess, plot
import pandas as pd

# Read yearly data
data = RawDataReader(
    instrument='AE33',
    path=data_path,
    start=datetime(2023, 1, 1),
    end=datetime(2023, 12, 31)
)

processed_data = DataProcess(data).process()

# Add seasonal information
processed_data['season'] = processed_data.index.month.map({
    12: 'Winter', 1: 'Winter', 2: 'Winter',
    3: 'Spring', 4: 'Spring', 5: 'Spring',
    6: 'Summer', 7: 'Summer', 8: 'Summer',
    9: 'Autumn', 10: 'Autumn', 11: 'Autumn'
})

# Seasonal box plots
plot.box_plot(processed_data, groupby='season', variable='BC')

# Monthly averages
monthly_avg = processed_data.groupby(pd.Grouper(freq='M')).mean()
plot.time_series(monthly_avg, 'BC', title='Monthly Average BC Concentrations')
```

### Diurnal Pattern Analysis

```python
from AeroViz import RawDataReader, DataProcess, plot

# Read data
data = RawDataReader(instrument='AE33', path=data_path)
processed_data = DataProcess(data).process()

# Calculate diurnal patterns
diurnal_pattern = processed_data.groupby(processed_data.index.hour).agg({
    'BC': ['mean', 'std', 'median']
})

# Plot diurnal variation
plot.diurnal_pattern(processed_data, 'BC')

# Compare weekday vs weekend patterns
processed_data['weekday'] = processed_data.index.weekday < 5
plot.diurnal_comparison(processed_data, 'BC', groupby='weekday')
```

## Quality Control Examples

### Custom Quality Control Parameters

```python
from AeroViz import RawDataReader, DataProcess

# Read data with custom QC parameters
data = RawDataReader(instrument='AE33', path=data_path)

# Custom quality control settings
qc_params = {
    'remove_outliers': True,
    'outlier_threshold': 3.0,  # 3 sigma
    'interpolate_gaps': True,
    'max_gap_minutes': 30,
    'minimum_data_coverage': 0.75
}

processor = DataProcess(data, qc_params=qc_params)
processed_data = processor.process()

# View QC statistics
qc_stats = processor.get_qc_statistics()
print("Data coverage:", qc_stats['coverage'])
print("Outliers removed:", qc_stats['outliers_removed'])
```

### Manual Data Filtering

```python
from AeroViz import RawDataReader, DataProcess
import numpy as np

data = RawDataReader(instrument='SMPS', path=data_path)
processed_data = DataProcess(data).process()

# Apply custom filters
# Remove negative values
processed_data = processed_data[processed_data >= 0]

# Remove values during instrument maintenance
maintenance_periods = [
    (datetime(2024, 2, 15), datetime(2024, 2, 16)),
    (datetime(2024, 5, 10), datetime(2024, 5, 11))
]

for start, end in maintenance_periods:
    processed_data = processed_data[~((processed_data.index >= start) &
                                      (processed_data.index <= end))]

# Apply rolling median filter for noise reduction
processed_data['BC_filtered'] = processed_data['BC'].rolling(
    window=5, center=True
).median()
```

## Visualization Examples

### Publication-Ready Figures

```python
from AeroViz import plot
import matplotlib.pyplot as plt

# Set publication style
plt.style.use('seaborn-v0_8-paper')

# Create multi-panel figure
fig, axes = plt.subplots(2, 2, figsize=(12, 8))

# Time series
plot.time_series(processed_data, 'BC', ax=axes[0,0], 
                title='Black Carbon Time Series')

# Diurnal pattern
plot.diurnal_pattern(processed_data, 'BC', ax=axes[0,1],
                    title='Diurnal Variation')

# Histogram
plot.histogram(processed_data, 'BC', ax=axes[1,0],
              title='BC Distribution')

# Correlation plot
plot.scatter(processed_data, 'BC', 'PM2.5', ax=axes[1,1],
            title='BC vs PM2.5 Correlation')

plt.tight_layout()
plt.savefig('publication_figure.png', dpi=300, bbox_inches='tight')
```

### Interactive Plots

```python
from AeroViz import plot

# Create interactive time series plot
plot.interactive_timeseries(processed_data, ['BC1', 'BC2', 'BC3'],
                           title='Multi-wavelength BC Analysis')

# Interactive correlation matrix
plot.interactive_correlation(processed_data, 
                           variables=['BC', 'PM2.5', 'PM10', 'NO2'])

# Interactive size distribution
plot.interactive_size_distribution(smps_data,
                                  title='Particle Size Distribution')
```

## Export and Reporting

### Data Export Examples

```python
from AeroViz import DataProcess
import pandas as pd

# Export processed data
processed_data.to_csv('processed_aerosol_data.csv')

# Export with metadata
metadata = {
    'instrument': 'AE33',
    'location': 'Urban Background',
    'processing_date': datetime.now(),
    'qc_applied': True
}

# Save as Excel with multiple sheets
with pd.ExcelWriter('aerosol_analysis.xlsx') as writer:
    processed_data.to_excel(writer, sheet_name='Data')
    pd.DataFrame([metadata]).to_excel(writer, sheet_name='Metadata')
    qc_stats.to_excel(writer, sheet_name='QC_Statistics')
```

### Automated Reporting

```python
from AeroViz import RawDataReader, DataProcess, plot, report

# Process data
data = RawDataReader(instrument='AE33', path=data_path)
processed_data = DataProcess(data).process()

# Generate automated report
report_config = {
    'include_timeseries': True,
    'include_statistics': True,
    'include_diurnal': True,
    'include_correlation': True
}

report.generate_summary_report(
    processed_data,
    output_path='aerosol_summary_report.html',
    config=report_config
)
```

## Troubleshooting Common Issues

### Handling Missing Data

```python
# Check for missing data
print("Missing data percentage:", 
      processed_data.isnull().sum() / len(processed_data) * 100)

# Different interpolation methods
processed_data['BC_linear'] = processed_data['BC'].interpolate(method='linear')
processed_data['BC_spline'] = processed_data['BC'].interpolate(method='spline', order=2)

# Forward/backward fill for short gaps
processed_data['BC_filled'] = processed_data['BC'].fillna(method='ffill', limit=3)
```

### Timezone Handling

```python
import pytz

# Convert timezone
processed_data.index = processed_data.index.tz_localize('UTC')
processed_data.index = processed_data.index.tz_convert('Asia/Taipei')

# Handle daylight saving time
local_tz = pytz.timezone('US/Eastern')
processed_data.index = processed_data.index.tz_convert(local_tz)
```

For more examples and detailed tutorials, visit
our [GitHub repository](https://github.com/alex870521/AeroViz/tree/main/examples).