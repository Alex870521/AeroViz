# Scanning Mobility Particle Sizer (SMPS)

The SMPS is an instrument used for measuring particle size distributions in the nanometer range.

## Data Format

- File format:
    - .txt files (tab-delimited) from older AIM versions (8.x, 9.x)
    - .csv files (comma-delimited) from newer AIM versions (10.x+)
- Sampling frequency: Variable
- File naming pattern: `*.txt` or `*.csv`
- Timestamp formats:
    - mm/dd/yy HH:MM:SS (US format, older versions)
    - mm/dd/yyyy HH:MM:SS (US format, newer versions)
    - dd/mm/yyyy HH:MM:SS (EU format)

## Measurement Parameters

The SMPS provides particle size distribution measurements:

- Size range: 11.8-593.5 nm (default)
- Output: Number concentration (dN/dlogDp) for each size bin
- Total particle concentration (particles/cm³)

## Data Processing

### Data Reading

- Automatically detects and skips header rows
- Supports multiple date formats based on AIM version
- Handles transposed data formats
- Extracts and sorts particle size columns numerically
- Validates size range against expected settings

### Quality Control

- Filters by specified particle size range
- Ensures temporal data completeness (minimum 6 measurements/hour)
- Applies minimum total concentration threshold (2000 particles/cm³)
- Removes physically implausible high concentrations (>1×10⁶ dN/dlogDp)
- Special filtering for large particles (>400 nm exceeding 4000 dN/dlogDp)

## Output Data

The processed data contains:

- Time index: Data acquisition time
- Size bins: Number concentration for each particle size
- Total concentration: Integrated particle number concentration

## Notes

- Different AIM software versions may produce different file formats
- Size range validation ensures data quality
- Special handling for large particle measurements
- Automatic format detection and parsing 