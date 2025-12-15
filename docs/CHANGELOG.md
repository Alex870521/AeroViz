## Unreleased

## v0.1.17 (2025-12-14)

### Feat

- Implement QCFlagBuilder system for unified QC workflow
- Add QCRule dataclass for declarative QC rule definition
- Add pre_process.py for unified absorption/scattering coefficient calculation
- Unified QC_Flag column for all instrument data quality marking
- QC Summary output at end of processing with validation results

### Docs

- Update QC_Flag handling documentation for all instruments
- Clarify QC_Flag only in intermediate files, removed from final output
- Update RawDataReader processing flow documentation
- Simplify Technical Specifications table in instruments index

### Refactor

- Simplify rate calculation and remove deter_key dependency
- Unify QC output format across all instrument readers

## v0.1.16 (2025-02-20)

### BREAKING CHANGE

- Complete overhaul from v0.1.9.0 to v0.1.11

### Feat

- enhance rate calculation to use minimum rates across all determinant keys
- **workflow**: add unpublish.yml

### Fix

- repair TEOM parsing and optical scatter key errors
- improve time handling for instrument data and reporting
- improve aerosol data processing and quality control
- improve aerosol data processing and quality control
- RawDataReader and the ReaderLogger class to better handle different environments and edge cases

### Refactor

- **RawDataReader**: simplify configuration and unify output handling
