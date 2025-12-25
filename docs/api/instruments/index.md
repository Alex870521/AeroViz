# Supported Instruments

AeroViz provides comprehensive support for reading and processing data from a wide range of aerosol measurement
instruments. Each instrument has a dedicated reader that handles its specific data format, file structure, and
measurement characteristics.

!!! info "Instrument Support"

    AeroViz automatically detects instrument types based on file format and content structure. You don't need to specify the
    instrument type manually when using the `RawDataReader` factory function.

## Instrument Categories

### Aethalometers (Black Carbon Measurement)

Instruments for measuring black carbon and light absorption:

- **[AE33](aethalometers/AE33.md)** - Magee Scientific AE33 (7-wavelength aethalometer)
- **[AE43](aethalometers/AE43.md)** - Magee Scientific AE43 (real-time BC measurements)
- **[BC1054](aethalometers/BC1054.md)** - MetOne BC1054 (high-resolution absorption)
- **[MA350](aethalometers/MA350.md)** - AethLabs MA350 (multi-angle absorption photometer)

### Nephelometers (Light Scattering)

Instruments for measuring aerosol light scattering:

- **[Aurora](nephelometers/Aurora.md)** - Ecotech Aurora (3-wavelength nephelometer)
- **[NEPH](nephelometers/NEPH.md)** - TSI Nephelometer (standard scattering measurements)

### Particle Sizers

Instruments for measuring particle size distributions:

- **[SMPS](particle-sizers/SMPS.md)** - Scanning Mobility Particle Sizer (10-600 nm)
- **[APS](particle-sizers/APS.md)** - Aerodynamic Particle Sizer (0.5-20 μm)
- **[GRIMM](particle-sizers/GRIMM.md)** - GRIMM Aerosol Spectrometer (optical sizing)

### Chemical Analysis

Instruments for chemical composition analysis:

- **[IGAC](chemical/IGAC.md)** - Ion chromatography (water-soluble ions)
- **[OCEC](chemical/OCEC.md)** - Organic/Elemental Carbon Analyzer
- **[VOC](chemical/VOC.md)** - Volatile Organic Compounds Monitor
- **[Xact](chemical/Xact.md)** - Xact 625i XRF Analyzer (elemental analysis)

### Mass Concentration

Instruments for PM mass concentration measurement:

- **[TEOM](mass/TEOM.md)** - Tapered Element Oscillating Microbalance
- **[BAM1020](mass/BAM1020.md)** - Beta Attenuation Monitor (PM2.5)

!!! tip "Usage Example"

    ```python
    from AeroViz.rawDataReader import RawDataReader
    
    # Automatic instrument detection
    reader = RawDataReader("instrument_data.txt")
    data = reader.read()
    
    # The reader automatically detects the instrument type
    print(f"Detected instrument: {reader.instrument_type}")
    print(f"Time resolution: {reader.time_resolution}")
    ```

## Technical Specifications

| Instrument | Time Resolution | File Type | QC Rules |
|:-----------|:---------------:|:----------|:---------|
| **AE33** | 1 min | .dat | Status Error, Invalid BC, Invalid AAE, Insufficient |
| **AE43** | 1 min | .dat | Status Error, Invalid BC, Invalid AAE, Insufficient |
| **BC1054** | 1 min | .csv | Status Error, Invalid BC, Invalid AAE, Insufficient |
| **MA350** | 1 min | .csv | Status Error, Invalid BC, Invalid AAE, Insufficient |
| **NEPH** | 5 min | .dat | Status Error, No Data, Invalid Scat Value, Invalid Scat Rel, Insufficient |
| **Aurora** | 1 min | .csv | Status Error, No Data, Invalid Scat Value, Invalid Scat Rel, Insufficient |
| **SMPS** | 6 min | .txt, .csv | Status Error, Invalid Number Conc, DMA Water, Insufficient |
| **APS** | 6 min | .txt | Status Error, Invalid Number Conc, Insufficient |
| **GRIMM** | 6 min | .dat | - |
| **TEOM** | 6 min | .csv | Status Error, High Noise, Non-positive, NV > Total, Invalid Vol Frac, Spike, Insufficient |
| **BAM1020** | 1 h | .csv | Invalid Conc, Spike |
| **OCEC** | 1 h | *LCRes.csv | Invalid Carbon, Below MDL, Spike, Missing OC |
| **IGAC** | 1 h | .csv | Mass Closure, Missing Main, Below MDL, Ion Balance |
| **Xact** | 1 h | .csv | Instrument Error, Upscale Warning, Invalid Value, High Uncertainty |
| **VOC** | 1 h | .csv | - |
| **EPA** | 1 h | .csv | Negative Value |

!!! note "Quality Control System"

    All instruments use the declarative **QCFlagBuilder** system:

    - **Declarative Rules** - Each instrument defines QC rules as `QCRule` dataclass instances
    - **Consistent Processing** - All instruments use `QC_Flag` internally for quality control
    - **Clean Output** - Final output has invalid data set to NaN, `QC_Flag` column removed

### QC Flag Processing

The `QC_Flag` column is used internally during processing:

- `"Valid"` - All QC rules passed
- `"Rule1, Rule2"` - Comma-separated list of failed rule names

**Output Files:**

| File | QC_Flag | Description |
|------|---------|-------------|
| `_read_{inst}_raw.pkl/csv` | ❌ No | Raw data before QC |
| `_read_{inst}_qc.pkl/csv` | ✅ Yes | QC'd data with flag |
| `output_{inst}.csv` | ❌ No | Final output (invalid → NaN) |

## Adding New Instruments

To add support for a new instrument, you need to:

1. Create a new reader class inheriting from `AbstractReader`
2. Implement the required methods for data parsing
3. Add instrument detection logic
4. Include appropriate quality control methods

!!! example "Example Reader Implementation"

    ```python
    from AeroViz.rawDataReader.core.AbstractReader import AbstractReader
    
    class MyInstrumentReader(AbstractReader):
        def __init__(self, file_path, **kwargs):
            super().__init__(file_path, **kwargs)
            
        def read_data(self):
            # Implement your data reading logic
            pass
            
        def apply_qc(self):
            # Implement quality control
            pass
    ```

## Related Documentation

- **[AbstractReader](../AbstractReader.md)** - Base class for all instrument readers
- **[Quality Control](../QualityControl.md)** - Data validation and filtering methods
- **[RawDataReader](../RawDataReader/index.md)** - Factory function for automatic instrument detection