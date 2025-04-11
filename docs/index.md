# AeroViz Documentation

Welcome to the AeroViz documentation! AeroViz is a comprehensive Python package for processing and visualizing aerosol
data.

## Core Features

AeroViz provides three main APIs for aerosol data processing and visualization:

### 1. RawDataReader

A factory function for reading and processing raw data from various aerosol instruments.

```python
from AeroViz import RawDataReader

# Example usage
data = RawDataReader(
    instrument='AE33',
    path='path/to/data',
    start=datetime(2024, 1, 1),
    end=datetime(2024, 12, 31)
)
```

[Learn more about RawDataReader](guide/RawDataReader.md)

### 2. DataProcess

Tools for advanced data processing and analysis.

```python
from AeroViz import DataProcess

# Example usage
processor = DataProcess(data)
processed_data = processor.process()
```

[Learn more about DataProcess](guide/DataProcess.md)

### 3. Plot

Visualization tools for creating publication-quality plots.

```python
from AeroViz import plot

# Example usage
plot.time_series(data, 'BC')
```

[Learn more about Plot](guide/plot.md)

## Supported Instruments

AeroViz supports a wide range of aerosol instruments through the RawDataReader API:

- [AE33 Aethalometer](instruments/AE33.md)
- [AE43 Aethalometer](instruments/AE43.md)
- [BC1054 Black Carbon Monitor](instruments/BC1054.md)
- [MA350 MicroAeth](instruments/MA350.md)
- [SMPS](instruments/SMPS.md)
- [NEPH](instruments/NEPH.md)
- [And more...](instruments/index.md)

## Quick Start

```python
from datetime import datetime
from pathlib import Path
from AeroViz import RawDataReader, DataProcess, plot

# Read data
data = RawDataReader(
    instrument='AE33',
    path=Path('/path/to/data'),
    start=datetime(2024, 1, 1),
    end=datetime(2024, 12, 31)
)

# Process data
processor = DataProcess(data)
processed_data = processor.process()

# Create visualization
plot.time_series(processed_data, 'BC')
```

## Installation

```bash
pip install AeroViz
```
