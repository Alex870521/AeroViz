# AbstractReader

The `AbstractReader` class is the foundation of AeroViz's data reading system, providing a standardized interface for
reading and processing aerosol instrument data.

!!! info "Core Architecture"

    AbstractReader serves as the base class for all instrument-specific readers in AeroViz. It defines the common interface
    and provides shared functionality for data processing, quality control, and output formatting.

## Overview

The AbstractReader implements a consistent workflow for all aerosol instruments:

1. **Data Ingestion** - Read raw instrument files
2. **Format Detection** - Automatically identify data structure
3. **Quality Control** - Apply built-in validation and filtering
4. **Standardization** - Convert to unified output format
5. **Metadata Handling** - Preserve instrument and measurement metadata

!!! tip "Usage Pattern"

    While you can use AbstractReader directly, it's typically accessed through the `RawDataReader` factory function which
    automatically selects the appropriate reader based on your instrument type.

## Key Features

- **Flexible Input Handling** - Supports various file formats and structures
- **Built-in Quality Control** - Configurable data validation and filtering
- **Metadata Preservation** - Maintains instrument configuration and measurement context
- **Extensible Design** - Easy to subclass for new instruments
- **Error Handling** - Robust error reporting and recovery

!!! warning "Implementation Note"

    AbstractReader is an abstract base class. For actual data reading, use instrument-specific implementations or the
    `RawDataReader` factory function.

## API Reference

::: AeroViz.rawDataReader.core.AbstractReader
    options:
        show_source: false
        show_bases: true
        show_inheritance_diagram: false
        members_order: alphabetical
        show_if_no_docstring: false
        filters:
            - "!^_"
            - "!^__init__"
        docstring_section_style: table
        heading_level: 3
        show_signature_annotations: true
        separate_signature: true
        group_by_category: true
        show_category_heading: true

## Related Documentation

- **[RawDataReader Factory](RawDataReader/index.md)** - High-level interface for instrument data reading
- **[Quality Control](QualityControl.md)** - Data validation and filtering options
- **[Supported Instruments](instruments/index.md)** - Available instrument implementations

!!! example "Quick Example"

    ````python
    from AeroViz import RawDataReader
    from datetime import datetime
    
    # Using the factory function (recommended)
    data = RawDataReader(
        instrument='AE33',
        path='/path/to/data',
        start=datetime(2024, 1, 1),
        end=datetime(2024, 12, 31)
    )
    
    # Direct usage (advanced - for custom implementations)
    from AeroViz.rawDataReader.core import AbstractReader
    
    
    class MyInstrumentReader(AbstractReader):
        nam = 'MyInstrument'
    
        def _raw_reader(self, file):
            # Custom file reading logic
            pass
    
        def _QC(self, df):
            # Custom QC logic
            return df
    ````
