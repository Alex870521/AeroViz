# API Reference

This section provides the API reference documentation for AeroViz.

## Core Modules

### RawDataReader

Module for reading raw data.

- [RawDataReader Guide](../guide/RawDataReader/index.md)
- [Data Processing Guide](../guide/DataProcess/index.md)
- [Plotting Guide](../guide/plot.md)

## Usage Examples

```python
from AeroViz.rawDataReader import RawDataReader

# Create reader instance
reader = RawDataReader()

# Read data
data = reader.read("path/to/data.txt")
```

## Important Notes

- All time series data use pandas DatetimeIndex
- Data quality control parameters can be set in configuration files
- Support for custom data processing workflows

### DataProcess

Class for advanced data processing and analysis.

```python
from AeroViz import DataProcess

processor = DataProcess(data)
processed_data = processor.process()
```

[View DataProcess Documentation](../guide/DataProcess/index.md)

### plot

Module for creating publication-quality visualizations.

```python
from AeroViz import plot

plot.time_series(data, 'BC')
plot.scatter(data, 'BC', 'PM2.5')
```

[View Plot Documentation](../guide/plot.md)

## Common Parameters

### Time Range Parameters

- `start` (datetime): Start time for data processing
- `end` (datetime): End time for data processing
- `mean_freq` (str): Time frequency for averaging (e.g., '1h', '1D')

### Data Processing Parameters

- `qc` (str): Quality control level ('1MS', '1D', '1W')
- `reset` (bool): Whether to reset previous processing

### Plot Parameters

- `variables` (list): Variables to plot
- `title` (str): Plot title
- `figsize` (tuple): Figure size
- `style` (str): Plot style

## Return Values

### RawDataReader

Returns a pandas DataFrame containing:

- Timestamp index
- Instrument-specific measurements
- Quality control flags
- Metadata

### DataProcess

Returns a processed DataFrame with:

- Cleaned data
- Transformed values
- Statistical summaries
- Quality metrics

### plot

Returns matplotlib figure objects that can be:

- Displayed directly
- Saved to files
- Further customized