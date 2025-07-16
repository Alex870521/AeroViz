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
- **[XRF](chemical/XRF.md)** - X-Ray Fluorescence (elemental analysis)
- **[TEOM](chemical/TEOM.md)** - Tapered Element Oscillating Microbalance (PM mass)
- **[BAM1020](chemical/BAM1020.md)** - Beta Attenuation Monitor (PM2.5 mass)

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

The following table provides detailed technical specifications for all supported instruments:

| Instrument                                             | Time Resolution | File Type   | Display Columns                                       | QAQC method |
|:-------------------------------------------------------|:---------------:|:------------|-------------------------------------------------------|:-----------:|
| NEPH (Nephelometer)                                    |      5min       | .dat        | G                                                     |   default   |
| Aurora (Nephelometer)                                  |      1min       | .csv        | G                                                     |   default   |
| SMPS (Scanning Mobility Particle Sizer)                |      6min       | .txt, .csv  | all                                                   |   default   |
| GRIMM (GRIMM Aerosol Technik)                          |      6min       | .dat        | all                                                   |   default   |
| APS_3321 (Aerodynamic Particle Sizer)                  |      6min       | .txt        | all                                                   |   default   |
| AE33 (Aethalometer Model 33)                           |      1min       | .dat        | BC6                                                   |   default   |
| AE43 (Aethalometer Model 43)                           |      1min       | .dat        | BC6                                                   |   default   |
| BC1054 (Black Carbon Monitor 1054)                     |      1min       | .csv        | BC9                                                   |   default   |
| MA350 (MicroAeth MA350)                                |      1min       | .csv        | BC5                                                   |   default   |
| BAM1020 (Beta Attenuation Mass Monitor)                |       1h        | .csv        | Conc                                                  |   default   |
| TEOM (Continuous Ambient Particulate Monitor)          |      6min       | .csv        | PM_Total, PM_NV                                       |   default   |
| OCEC (Sunset Organic Carbon Elemental Carbon Analyzer) |       1h        | *LCRes.csv  | Thermal_OC, Thermal_EC, Optical_OC, Optical_EC        |   default   |
| IGAC (In-situ Gas and Aerosol Compositions monitor)    |       1h        | .csv        | Na+, NH4+, K+, Mg2+, Ca2+, Cl-, NO2-, NO3-, SO42-     |   default   |
| XRF (X-ray Fluorescence Spectrometer)                  |       1h        | .csv        | Al, Si, P, S, Cl, K, Ca, Ti, V, Cr, Mn, Fe, Ni, Cu... |   default   |
| VOC (Volatile Organic Compounds Monitor)               |       1h        | .csv        | voc                                                   |   default   |
| EPA                                                    |       1h        | .csv        | all                                                   |   default   |
| Minion                                                 |       1h        | .csv, .xlsx | Na+, NH4+, Cl-, NO3-, SO42-, Al, Ti, V, Cr, Mn, Fe    |   default   |

### Notes

1. For VOC, due to the numerous display columns, we've simply noted "voc" in the table. In reality, it includes many
   specific VOC compound names.
2. For instruments marked with "all", it means all available columns or intervals are displayed.
3. The display columns for XRF include a large number of element names, all of which are listed.

### Applying Method

| Processing Step     | Details                 |      NEPH      |     Aurora     |     BC1054      |      AE33       |     TEOM     |     APS      |       SMPS       |            OCEC            |
|:--------------------|:------------------------|:--------------:|:--------------:|:---------------:|:---------------:|:------------:|:------------:|:----------------:|:--------------------------:|
| Instrument Raw Data | Time Resolution         |   5 or 6min    |      1min      |      1min       |      1min       |     6min     |     6min     |       6min       |             1h             |
| QAQC self-check     | Instrument Status       |                |                |                 |                 |              |              |                  |                            |
|                     |                         |                |                |                 |                 |    noise     |              |                  |                            |
|                     | Measurement Range       | 0 < val < 2000 | 0 < val < 2000 | 0 < val < 20000 | 0 < val < 20000 | 0 < val < ?? | 1 < val <700 | 2000 < val < 1e6 |       -5 < val < 100       |
|                     |                         |                |                |                 |                 |              |              |                  |   T_OC > 0.3, O_OC > 0.3   |
|                     |                         |                |                |                 |                 |              |              |                  | T_EC > 0.015, O_EC > 0.015 |
|                     | Data representativeness |      50%       |      50%       |       50%       |       50%       |     50%      |     50%      |       50%        |            None            |
|                     | Data Continuously       |       1h       |       1h       |       1h        |       1h        |      6h      |     None     |       None       |            24h             |
|                     | Specific Check          |      RGB       |      RGB       |                 |                 |              |              |                  |                            |

!!! note "Quality Control Methods"

    All instruments use the "default" QAQC method which includes:
    
    - **Range Validation** - Data outside physical limits are flagged
    - **Continuity Check** - Gaps in data are identified
    - **Status Monitoring** - Instrument status flags are evaluated
    - **Representativeness** - Minimum data coverage requirements

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