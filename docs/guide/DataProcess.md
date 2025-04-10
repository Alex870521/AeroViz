# DataProcess Documentation

## Overview

DataProcess is a class for advanced data processing and analysis of aerosol data. It provides methods for data cleaning,
transformation, and statistical analysis.

## Basic Usage

```python
from AeroViz import DataProcess

# Initialize with data from RawDataReader
processor = DataProcess(data)

# Process the data
processed_data = processor.process()
```

## Methods

### process()

Process the input data with default settings.

```python
processed_data = processor.process()
```

### clean_data()

Clean the data by removing outliers and filling missing values.

```python
cleaned_data = processor.clean_data()
```

### transform()

Transform the data (e.g., log transformation).

```python
transformed_data = processor.transform()
```

### analyze()

Perform statistical analysis on the data.

```python
analysis_results = processor.analyze()
```

## Parameters

- `data` (DataFrame): Input data from RawDataReader
- `methods` (list): List of processing methods to apply
- `params` (dict): Parameters for each processing method

## Returns

- DataFrame: Processed data with applied transformations and cleaning

## Examples

### Basic Processing

```python
from AeroViz import DataProcess

processor = DataProcess(data)
processed_data = processor.process()
```

### Custom Processing

```python
processor = DataProcess(
    data,
    methods=['clean', 'transform', 'analyze'],
    params={
        'clean': {'threshold': 3},
        'transform': {'method': 'log'},
        'analyze': {'window': '1D'}
    }
)
processed_data = processor.process()
```

## Notes

- The DataProcess class is designed to work seamlessly with data from RawDataReader
- All processing methods are configurable through parameters
- Results can be saved to various formats (CSV, Excel, etc.)
