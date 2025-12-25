# API Reference

Complete technical reference documentation for AeroViz, a comprehensive Python package for aerosol data processing,
analysis, and visualization.

!!! info "About AeroViz API"

    AeroViz provides a unified interface for working with aerosol measurement data from multiple instrument types. The API is designed for scientific research applications with emphasis on data quality, reproducibility, and ease of use.

## Core Components

### Data Input and Processing

**[RawDataReader](RawDataReader/index.md)**
Primary interface for reading and standardizing aerosol instrument data with automatic format detection.

- [AbstractReader](AbstractReader.md) - Base class architecture and extension points
- [Quality Control](QualityControl.md) - Data validation, filtering, and quality assurance
- [Supported Instruments](instruments/index.md) - Complete instrument compatibility matrix

### Measurement Instrument Support

AeroViz provides native support for the following categories of aerosol instruments:

**Black Carbon and Light Absorption**

- [AE33](instruments/aethalometers/AE33.md) - Magee Scientific AE33 7-wavelength aethalometer
- [AE43](instruments/aethalometers/AE43.md) - Magee Scientific AE43 real-time measurements
- [BC1054](instruments/aethalometers/BC1054.md) - MetOne BC1054 high-resolution absorption
- [MA350](instruments/aethalometers/MA350.md) - AethLabs MA350 multi-angle photometer

**Light Scattering Measurements**

- [Aurora](instruments/nephelometers/Aurora.md) - Ecotech Aurora 3-wavelength nephelometer
- [NEPH](instruments/nephelometers/NEPH.md) - TSI nephelometer standard processing

**Particle Size Distribution**

- [SMPS](instruments/particle-sizers/SMPS.md) - Scanning Mobility Particle Sizer (10-600 nm)
- [APS](instruments/particle-sizers/APS.md) - Aerodynamic Particle Sizer (0.5-20 μm)
- [GRIMM](instruments/particle-sizers/GRIMM.md) - GRIMM Aerosol Spectrometer optical sizing

**Chemical Composition Analysis**

- [IGAC](instruments/chemical/IGAC.md) - Ion chromatography for water-soluble species
- [OCEC](instruments/chemical/OCEC.md) - Organic and elemental carbon analysis
- [VOC](instruments/chemical/VOC.md) - Volatile organic compounds monitoring
- [Xact](instruments/chemical/Xact.md) - Xact 625i XRF elemental analyzer
- [TEOM](instruments/chemical/TEOM.md) - Tapered Element Oscillating Microbalance

### Data Processing and Analysis

**[DataProcess](DataProcess/index.md)**
Advanced data processing engine for aerosol science with specialized modules:

- [SizeDistr](DataProcess/SizeDistr.md) - Particle size distribution processing and analysis
- [Chemistry](DataProcess/Chemistry.md) - Chemical composition and mass reconstruction
- [Optical](DataProcess/Optical.md) - Optical properties and extinction calculations
- [VOC](DataProcess/VOC.md) - Volatile organic compounds analysis

## Visualization and Plotting

**[Plot API](plot/index.md)**  
Professional-grade plotting interface optimized for scientific publications with publication-ready defaults.

### Available Plot Types

- **[Scatter Plots](plot/basic/scatter.md)** - Correlation analysis with statistical regression
- **[Regression Analysis](plot/basic/regression.md)** - Statistical relationship modeling and fitting
- **[Box Plots](plot/basic/box.md)** - Statistical distribution summaries and outlier detection
- **[Bar Charts](plot/basic/bar.md)** - Categorical data visualization and comparison
- **[Violin Plots](plot/basic/violin.md)** - Distribution shape analysis and comparison
- **[Pie Charts](plot/basic/pie.md)** - Proportional data representation

## Getting Started

### New Users

Begin with the [RawDataReader](RawDataReader/index.md) for data input, understand [Quality Control](QualityControl.md)
procedures, then explore [basic plotting](plot/basic/scatter.md) capabilities.

### Advanced Users

Leverage [DataProcess](DataProcess/index.md) for complex workflows,
consult [instrument-specific documentation](instruments/index.md) for detailed configurations, and utilize
advanced [plotting features](plot/index.md) for publication-quality figures.

### Developers

Review the [AbstractReader](AbstractReader.md) architecture for understanding the framework design, examine existing
instrument implementations as templates, and study plotting modules for extending visualization capabilities.

## Documentation Standards

!!! note "API Documentation Convention"

    All AeroViz API documentation follows NumPy docstring standards and includes:

    - **Parameters** - Complete parameter descriptions with data types
    - **Returns** - Detailed return value specifications and formats  
    - **Examples** - Working code examples with expected outputs
    - **Notes** - Implementation details, limitations, and best practices
    - **References** - Scientific literature and technical specifications

## Related Resources

- **[User Guide](../guide/index.md)** - Step-by-step tutorials and workflow examples
- **[Examples](../guide/index.md)** - Real-world usage scenarios and case studies
- **[Installation Guide](../guide/index.md)** - Setup instructions and system requirements