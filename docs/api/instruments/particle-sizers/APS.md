# Aerodynamic Particle Sizer (APS)

The APS is an instrument used for measuring aerodynamic particle size distributions in the micrometer range.

## Data Format

- File format: Tab-delimited text file
- Sampling frequency: Variable
- File naming pattern: `*.txt`
- Data structure:
    - Header: 6 rows of metadata
    - Time columns: Date and Start Time
    - Size distribution data: Columns 3-54

## Measurement Parameters

The APS provides aerodynamic particle size distribution measurements:

- Size range: 542-1981 nm
- Output: Number concentration for each size bin
- Total particle concentration (particles/cm³)

## Data Processing

### Data Reading

- Automatically skips header rows
- Parses date and time into datetime index
- Extracts particle size distribution data
- Rounds size bin values to 4 decimal places
- Validates datetime values

### Quality Control

- Ensures temporal data completeness (minimum 5 measurements/hour)
- Applies total concentration thresholds (1-700 particles/cm³)
- Calculates total concentration with logarithmic bin spacing
- Removes invalid measurements

## Output Data

The processed data contains:

- Time index: Data acquisition time
- Size bins: Number concentration for each particle size
- Total concentration: Integrated particle number concentration

## Notes

- Measures aerodynamic particle diameter directly
- Complementary to SMPS for larger particle sizes
- Size range approximately 0.5-20 μm
- Logarithmic bin spacing in size distribution 