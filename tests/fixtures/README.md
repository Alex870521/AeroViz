# Test Fixtures

This directory contains test data files for AeroViz instrument readers.

## Directory Structure

```
fixtures/
└── raw_data/
    ├── AE33/
    │   ├── normal/           # Standard .dat files
    │   └── status_errors/    # Files with error status codes
    ├── APS/
    │   ├── normal/           # Standard APS export
    │   ├── multi_header/     # Files with multiple concatenated headers
    │   ├── transposed/       # Transposed format
    │   └── status_errors/    # Files with non-zero status flags
    ├── SMPS/
    │   ├── normal/           # Standard files
    │   ├── txt_format/       # .txt format files
    │   ├── csv_format/       # .csv format files
    │   └── transposed/       # Transposed format
    ├── TEOM/
    │   ├── normal/           # Standard files
    │   ├── remote_download/  # Remote download format
    │   └── usb_download/     # USB download format
    └── ...
```

## Adding Test Data

### File Requirements

1. **Small size**: Each file should contain only 1-24 hours of data (few KB to ~100 KB)
2. **Representative**: Include typical data patterns for the instrument
3. **No sensitive data**: Remove any location identifiers or sensitive information

### Scenario Directories

Each instrument can have multiple scenario directories:

| Directory | Description |
|-----------|-------------|
| `normal/` | Standard, well-formatted files |
| `multi_header/` | Files with multiple embedded headers |
| `transposed/` | Transposed format files |
| `status_errors/` | Files containing error status codes |
| `duplicate_timestamps/` | Files with duplicate time entries |
| `edge_cases/` | Other edge cases specific to the instrument |

### Naming Convention

- Use descriptive names: `sample_20240101.dat`, `multi_header_example.txt`
- Include format info if multiple formats: `normal_txt.txt`, `normal_csv.csv`

## Running Tests

```bash
# Run all reader tests
pytest tests/test_readers/ -v

# Run tests for a specific instrument
pytest tests/test_readers/test_aps.py -v

# Run only tests that have data available
pytest tests/test_readers/ -v --ignore-glob="**/test_*.py"

# Skip tests without data
pytest tests/test_readers/ -v  # Tests auto-skip if data not available
```

## Instrument-Specific Notes

### APS
- **multi_header/**: Files created by concatenating multiple APS exports
- Status flags are binary strings: `"0000 0000 0000 0000"`

### SMPS
- Supports both `.txt` (tab-separated) and `.csv` formats
- Status is text: `"Normal Scan"` = OK

### TEOM
- Multiple download formats: remote vs USB
- Has Chinese month names in some formats

### AE33/AE43/BC1054/MA350
- Status is numeric with bitwise error codes
- 7 wavelengths for BC measurement

### NEPH/Aurora
- Scattering at multiple wavelengths (B, G, R)
- Status is numeric (0 = OK)
