# Organic Carbon/Elemental Carbon Analyzer (OC/EC)

The OC/EC analyzer measures carbonaceous aerosol components using thermal and optical methods.

## Data Format

- File format: CSV file
- Sampling frequency: Variable
- File naming pattern: `*.csv`
- Data structure:
    - Header: 3 rows of metadata
    - Time column: Start Date/Time
    - Carbon fraction measurements
    - Sample volume information

## Measurement Parameters

The OC/EC analyzer provides measurements of:

- Thermal analysis:
    - Organic Carbon (Thermal_OC)
    - Elemental Carbon (Thermal_EC)
- Optical analysis:
    - Organic Carbon (Optical_OC)
    - Elemental Carbon (Optical_EC)
- Carbon fractions:
    - OC1-4: Different temperature stages
    - PC: Pyrolyzed carbon
    - TC: Total carbon

## Data Processing

### Data Reading

- Processes CSV files with varying header structures
- Handles 12/24 hour time formats
- Standardizes column names
- Rounds timestamps to nearest hour
- Converts raw measurements to concentration units

### Quality Control

- Removes physically implausible values (<-5 or >100 μgC/m³)
- Applies minimum detection limits:
    - Thermal_OC: 0.3 μgC/m³
    - Optical_OC: 0.3 μgC/m³
    - Thermal_EC: 0.015 μgC/m³
    - Optical_EC: 0.015 μgC/m³
- Uses time-aware IQR filtering
- Requires valid OC measurements

## Output Data

The processed data contains:

- Time index: Data acquisition time
- Carbon measurements:
    - Thermal and optical OC/EC
    - Total carbon (TC)
    - Carbon fractions (OC1-4, PC)
- Sample volume: Air volume sampled

## Notes

- Provides critical information about combustion sources
- Helps identify secondary organic aerosol formation
- Combines thermal and optical analysis methods
- Standardizes output across different instrument formats 