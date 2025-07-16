# AeroViz

A modern Python package for aerosol data processing and visualization

<div class="card-container">
    <div class="doc-card">
        <div class="card-icon">
            <i class="fa fa-flag-checkered"></i>
        </div>
        <div class="card-title">Getting started</div>
        <div class="card-desc">
            New to AeroViz? Check out the Beginner's Guide. It contains an introduction to AeroViz's main features and examples to get you started quickly.
        </div>
        <div class="card-action">
            <a href="guide/" class="card-button">To the beginner's guide</a>
        </div>
    </div>
    <div class="doc-card">
        <div class="card-icon">
            <i class="fa fa-book"></i>
        </div>
        <div class="card-title">User guide</div>
        <div class="card-desc">
            The user guide provides in-depth information on key concepts of AeroViz with detailed explanations of data processing and visualization capabilities.
        </div>
        <div class="card-action">
            <a href="guide/" class="card-button">To the user guide</a>
        </div>
    </div>
    <div class="doc-card">
        <div class="card-icon">
            <i class="fa fa-wand-magic-sparkles"></i>
        </div>
        <div class="card-title">API reference</div>
        <div class="card-desc">
            The reference guide contains detailed descriptions of the functions, classes, and methods included in AeroViz. It assumes that you have an understanding of the key concepts.
        </div>
        <div class="card-action">
            <a href="api/" class="card-button">To the reference guide</a>
        </div>
    </div>
    <div class="doc-card">
        <div class="card-icon">
            <img src="assets/icon.svg" alt="AeroViz Icon" width="39" height="39">
        </div>
        <div class="card-title">AeroViz</div>
        <div class="card-desc">
            A platform for real-time monitoring, offering data visualization and analytical insights.
        </div>
        <div class="card-action">
            <a href="https://aeroviz.org/" class="card-button">Visit Website</a>
        </div>
    </div>

</div>

## **Installation**

You can install AeroViz using pip:

```bash
pip install AeroViz
```

For detailed installation instructions, system requirements, and troubleshooting, please see
the [Getting Started Guide](guide/).

## **Quick Start**

Here's a simple example of how to use AeroViz:

```python
from datetime import datetime
from pathlib import Path
from AeroViz import RawDataReader, DataProcess, plot

# Read data from a supported instrument
data = RawDataReader(
    instrument='AE33',
    path=Path('/path/to/folder'),
    start=datetime(2024, 1, 1),
    end=datetime(2024, 12, 31)
)

# Process the data
processor = DataProcess(data)
processed_data = processor.process()

# Create visualization
plot.time_series(processed_data, 'BC')
```

For detailed tutorials and examples, see the [Getting Started Guide](guide/).

## **Key Features**

AeroViz is a comprehensive Python package designed for aerosol data processing and visualization. It provides a unified
interface for handling data from various aerosol instruments, performing quality control, and creating publication-ready
visualizations.

- **Unified Data Interface**: Standardized data structures and built-in quality control across multiple instrument types
- **Advanced Processing**: Customizable processing pipelines with automated corrections and statistical analysis tools
- **Publication-Ready Visualization**: High-resolution plots with extensive customization options

## **Documentation**

- [Installation Guide](guide/index.md#installation) - Setup instructions

[//]: # (- [Tutorials]&#40;guide/tutorials.md&#41; - Step-by-step guides)

- [API Reference](api/index.md) - Detailed function documentation

[//]: # (- [Examples Gallery]&#40;guide/examples.md&#41; - Real-world application examples)

## **Contributing**

AeroViz is an open-source project. Contributions and suggestions are welcome! Visit
our [GitHub repository](https://github.com/alex870521/AeroViz) to get involved.
