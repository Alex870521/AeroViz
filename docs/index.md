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
        <div class="card-title">Web Site</div>
        <div class="card-desc">
            AeroViz is a platform for real-time monitoring, offering data visualization and analytical insights.
        </div>
        <div class="card-action">
            <a href="https://aeroviz.org/" class="card-button">Visit Website</a>
        </div>
    </div>

</div>

## Installation

```bash
pip install AeroViz
```

## Overview

AeroViz is a comprehensive Python package designed for aerosol data processing and visualization. It provides a unified
interface for handling data from various aerosol instruments, performing quality control, and creating publication-ready
visualizations.

### Key Features

- **Unified Data Interface**: Standardized data structures and built-in quality control across multiple instrument types
- **Advanced Processing**: Customizable processing pipelines with automated corrections and statistical analysis tools
- **Publication-Ready Visualization**: High-resolution plots with extensive customization options

## Documentation

- [Installation Guide](guide/index.md#installation) - Setup instructions

[//]: # (- [Tutorials]&#40;guide/tutorials.md&#41; - Step-by-step guides)

- [API Reference](api/index.md) - Detailed function documentation

[//]: # (- [Examples Gallery]&#40;guide/examples.md&#41; - Real-world application examples)

## Supported Instruments

AeroViz currently supports the following instruments:

- [AE33 Aethalometer](guide/instruments/AE33.md)
- [AE43 Aethalometer](guide/instruments/AE43.md)
- [BC1054 Multi-wavelength Aethalometer](guide/instruments/BC1054.md)
- [MA350 Micro Aethalometer](guide/instruments/MA350.md)
- [SMPS](guide/instruments/SMPS.md)
- [NEPH](guide/instruments/NEPH.md)
- For more details on specific instrument support, see the [instruments documentation](guide/instruments/index.md).

## Contributing

AeroViz is an open-source project. Contributions and suggestions are welcome! Visit
our [GitHub repository](https://github.com/alex870521/AeroViz) to get involved.
