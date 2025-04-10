# GRIMM Aerosol Spectrometer

The GRIMM is an optical particle counter that measures particle size distributions across multiple size channels.

## Data Format

- File format: Tab-delimited text file
- Sampling frequency: Variable
- File naming pattern:
    - `A407ST*.txt` (specific format)
    - Other GRIMM formats
- Data structure:
    - Header: 233 rows of metadata
    - European date format (DD/MM/YYYY)
    - Size distribution channels (columns 11-127/128)

## Measurement Parameters

The GRIMM provides:

- Size range: 0.25 to 32 μm
- Resolution: Multiple size channels
- Output: Number concentration for each size bin
- Units: particles/cm³ (after scaling)

## Data Processing

### Data Reading

- Processes tab-delimited files
- Handles European date format
- Extracts size distribution channels
- Applies scaling factor (1/0.035)
- Uses ISO-8859-1 encoding
- Handles different file formats

### Quality Control

- Basic file validation
- Empty file detection
- No additional QC currently implemented
- Future QC possibilities:
    - Value range checks
    - Total concentration consistency
    - Time-based outlier detection

## Output Data

The processed data contains:

- Time index: Data acquisition time
- Size channels: Number concentration for each bin
- All measurements in particles/cm³

## Notes

- High resolution size information
- Wide size range coverage
- Multiple size channels
- Standard scaling factor applied
- European date format support 