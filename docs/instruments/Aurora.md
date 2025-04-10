# Aurora Integrating Nephelometer

The Aurora is an integrating nephelometer used for measuring light scattering properties of aerosols at multiple
wavelengths.

## Data Format

- File format: CSV file
- Sampling frequency: 1 minute
- File naming pattern: `*.csv`
- Timestamp column: Date / time local
- Column naming conventions:
    - UV BCc, Blue BCc, Green BCc, Red BCc, IR BCc
    - Biomass BCc, Fossil fuel BCc
    - Delta-C, AAE, BB (%)

## Measurement Parameters

The Aurora provides measurements at multiple wavelengths and source apportionment:

- B, G, R: Total scattering coefficients at blue, green, and red wavelengths (Mm⁻¹)
- BB, BG, BR: Backscattering coefficients at blue, green, and red wavelengths (Mm⁻¹)
- BB mass: Biomass burning BC mass concentration (ng/m³)
- FF mass: Fossil fuel BC mass concentration (ng/m³)
- Delta-C: Difference between UV and IR channels (ng/m³)
- AAE: Absorption Ångström Exponent
- BB: Biomass burning percentage (%)

## Data Processing

### Data Reading

- Parses timestamps from 'Date / time local' column
- Standardizes column names for consistent output
- Converts all measurement values to numeric format
- Handles different column naming conventions
- Maps wavelength-specific BC concentrations to standardized names

### Quality Control

- Removes physically impossible values (negative or > 2000 Mm⁻¹)
- Ensures physical consistency:
    - Backscattering must be less than total scattering
    - Blue > Green > Red (Rayleigh scattering principle)
- Applies time-aware IQR filtering with 1-hour windows
- Ensures data completeness across all channels

## Output Data

The processed data contains the following columns:

- Time index: Data acquisition time
- B, G, R: Total scattering coefficients (Mm⁻¹)
- BB, BG, BR: Backscattering coefficients (Mm⁻¹)
- BB mass: Biomass burning BC (ng/m³)
- FF mass: Fossil fuel BC (ng/m³)
- Delta-C: UV-IR difference (ng/m³)
- AAE: Absorption Ångström Exponent
- BB: Biomass burning percentage (%)

## Notes

- Provides real-time measurement of black carbon concentrations with source apportionment
- Distinguishes between fossil fuel combustion and biomass burning contributions
- Maintains physical consistency between measurements
- Automatically handles different column naming conventions 