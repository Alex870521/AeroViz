# Getting Started with AeroViz

## Installation

You can install AeroViz using pip:

```bash
pip install AeroViz
```

## Basic Usage

Here's a simple example of how to use AeroViz:

```python
from datetime import datetime
from pathlib import Path
from AeroViz import RawDataReader, DataProcess, plot

# Read data from a supported instrument
data = RawDataReader(
    instrument='AE33',
    path=Path('/path/to/data'),
    start=datetime(2024, 1, 1),
    end=datetime(2024, 12, 31)
)

# Process the data
processor = DataProcess(data)
processed_data = processor.process()

# Create visualization
plot.time_series(processed_data, 'BC')
```

## Next Steps

- Learn more about [RawDataReader](RawDataReader.md)
- Explore [DataProcess](DataProcess.md) functionality
- Check out [Plot](plot.md) capabilities
- Browse supported [instruments](../instruments/instrument_overview.md) 