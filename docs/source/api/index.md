# API Reference

## Core APIs

### RawDataReader

Factory function for reading and processing raw data from various aerosol instruments.

```python
from AeroViz import RawDataReader

data = RawDataReader(
    instrument='AE33',
    path='path/to/data',
    start=datetime(2024, 1, 1),
    end=datetime(2024, 12, 31)
)
```

[View RawDataReader Documentation](guide/RawDataReader.md)

### DataProcess

Class for advanced data processing and analysis.

```python
from AeroViz import DataProcess

processor = DataProcess(data)
processed_data = processor.process()
```

[View DataProcess Documentation](guide/DataProcess.md)

### plot

Module for creating publication-quality visualizations.

```python
from AeroViz import plot

plot.time_series(data, 'BC')
plot.scatter(data, 'BC', 'PM2.5')
```

[View Plot Documentation](guide/plot.md)

## Supported Instruments

### AE33 Aethalometer

[View AE33 Documentation](instruments/AE33.md)

### AE43 Aethalometer

[View AE43 Documentation](instruments/AE43.md)

### BC1054 Black Carbon Monitor

[View BC1054 Documentation](instruments/BC1054.md)

### MA350 MicroAeth

[View MA350 Documentation](instruments/MA350.md)

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