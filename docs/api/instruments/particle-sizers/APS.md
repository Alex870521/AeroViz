# Aerodynamic Particle Sizer (APS)

The APS is an instrument used for measuring aerodynamic particle size distributions in the micrometer range.

::: AeroViz.rawDataReader.script.APS.Reader

## Data Format

- File format: Tab-delimited text file
- Sampling frequency: 6 minutes (typical)
- File naming pattern: `*.txt`
- Data structure:
    - Header: 6 rows of metadata
    - Time columns: Date and Start Time
    - Size distribution data: Columns 3-54

## Measurement Parameters

The APS provides aerodynamic particle size distribution measurements:

| Parameter | Value | Description |
|-----------|-------|-------------|
| Size range | 542-1981 nm | Aerodynamic diameter range |
| Output | dN/dlogDp | Number concentration per size bin |
| Unit | #/cm³ | Particle number concentration |

## Data Processing

### Data Reading

- Automatically skips 6 rows of header metadata
- Parses date and time into datetime index
- Extracts particle size distribution data (columns 3-54)
- Rounds size bin values to 4 decimal places
- Handles transposed data formats
- Validates datetime values

### Quality Control

The APS reader uses the declarative **QCFlagBuilder** system with the following rules:

```
+-----------------------------------------------------------------------+
|                         QC Thresholds                                 |
+-----------------------------------------------------------------------+
| completeness     >= 50% of the detected frequency's hourly points     |
| MIN_TOTAL_CONC   = 1      #/cm³                                       |
| MAX_TOTAL_CONC   = 700    #/cm³                                       |
| STATUS_OK        = "0000 0000 0000 0000" (16-bit binary, all zeros)   |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
|                            _QC() Pipeline                             |
+-----------------------------------------------------------------------+
|                                                                       |
|  [Pre-process] Calculate dlogDp and total concentration               |
|       |                                                               |
|       v                                                               |
|  +-------------------------+                                          |
|  | Rule: Status Error      |                                          |
|  +-------------------------+                                          |
|  | Status Flags != all     |                                          |
|  | zeros (16-bit binary)   |                                          |
|  +-------------------------+                                          |
|           |                                                           |
|           v                                                           |
|  +-------------------------+                                          |
|  | Rule: Insufficient      |                                          |
|  +-------------------------+                                          |
|  | < 5 measurements        |                                          |
|  | per hour                |                                          |
|  +-------------------------+                                          |
|           |                                                           |
|           v                                                           |
|  +-------------------------+                                          |
|  | Rule: Invalid Number    |                                          |
|  |       Conc              |                                          |
|  +-------------------------+                                          |
|  | Total number conc.      |                                          |
|  | outside range (1-700)   |                                          |
|  +-------------------------+                                          |
|                                                                       |
+-----------------------------------------------------------------------+
```

#### QC Rules Applied

| Rule | Condition | Description |
|------|-----------|-------------|
| **Status Error** | Status Flags ≠ 0 | Non-zero status flags indicate instrument error |
| **Insufficient** | < 5 measurements/hour | Less than 5 measurements per hour |
| **Invalid Number Conc** | Total < 1 OR > 700 #/cm³ | Total number concentration outside valid range |

#### Error Status Codes (from TSI RF command)

| Bit | Binary Value | Description |
|-----|--------------|-------------|
| 0 | 0000 0000 0000 0001 | Laser fault |
| 1 | 0000 0000 0000 0010 | Total Flow out of range |
| 2 | 0000 0000 0000 0100 | Sheath Flow out of range |
| 3 | 0000 0000 0000 1000 | Excessive sample concentration |
| 4 | 0000 0000 0001 0000 | Accumulator clipped (> 65535) |
| 5 | 0000 0000 0010 0000 | Autocal failed |
| 6 | 0000 0000 0100 0000 | Internal temperature < 10°C |
| 7 | 0000 0000 1000 0000 | Internal temperature > 40°C |
| 8 | 0000 0001 0000 0000 | Detector voltage out of range (±10% Vb) |
| 9 | 0000 0010 0000 0000 | Reserved (unused) |

#### Valid Concentration Range

```
    Total Conc (#/cm³)
       ^
   700 +-------------------------------- MAX_TOTAL_CONC
       |   +-----------------------+    (reject if exceeded)
       |   |    VALID RANGE        |
       |   +-----------------------+
     1 +-------------------------------- MIN_TOTAL_CONC
     0 +-------------------------------- (reject if below)
       +----------------------------> Time
```

#### Status Condition Register

The `Status Flags` column is a bitfield: the instrument OR-sums every
active condition and reports the sum, so one value can mean several things at
once. `Reader.STATUS_BITS` carries this table, and it is what turns a raw status
into `df.attrs['status_conditions']` — a named condition instead of a number.

| Bit | Decimal | Condition |
|-----|---------|-----------|
| 8 | `256` | Detector voltage out of range |
| 7 | `128` | Internal temperature > 40°C |
| 6 | `64` | Internal temperature < 10°C |
| 5 | `32` | Autocal failed |
| 4 | `16` | Accumulator clipped |
| 3 | `8` | Excessive sample concentration |
| 2 | `4` | Sheath Flow out of range |
| 1 | `2` | Total Flow out of range |
| 0 | `1` | Laser fault |

The register is written as a space-grouped bit string
(`'0000 0000 0000 0001'` is bit 0, not the number one thousand). Bit 9 is
reserved. Every non-whitelisted bit counts as an error — this table names
the conditions, it does not decide which of them matter.

To stop treating one condition as an error, whitelist its decimal value:

```python
RawDataReader('APS', path, ignored_status_errors=[1])  # ignore Laser fault
```

## Output Data

The processed data contains:

| Column | Unit | Description |
|--------|------|-------------|
| Size bins (542-1981 nm) | dN/dlogDp | Number concentration for each size |

!!! note "QC_Flag Handling"

    - The intermediate file (`_read_aps_qc.pkl/csv`) contains the `QC_Flag` column
    - The final output has invalid data set to NaN and `QC_Flag` column removed

## Notes

- Measures aerodynamic particle diameter directly
- Complementary to SMPS for larger particle sizes
- Size range approximately 0.5-2 μm
- Logarithmic bin spacing in size distribution
