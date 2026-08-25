# TEOM (Tapered Element Oscillating Microbalance)

The TEOM is used for continuous monitoring of PM2.5 mass concentrations using microbalance technology.

::: AeroViz.rawDataReader.script.TEOM.Reader

## Data Format

- File format: CSV file
- Sampling frequency: 6 minutes
- File naming pattern: `*.csv`
- Supported formats:
    - Remote Download Format (single timestamp column — `Time Stamp`, or the
      SNMP-named `time_stamp` some 1405 auto-exports use)
    - USB Download/Auto Export Format (separate `Date` + `Time` columns)

### Remote Download Format

| Column | Mapping | Description |
|--------|---------|-------------|
| Time Stamp | time | Timestamp (`DD - MM - YYYY HH:MM:SS`; the month may be a number or a localized name, e.g. `六月` / `Aug`) |
| System status | status | Instrument status |
| PM-2.5 base MC | PM_NV | Non-volatile PM2.5 |
| PM-2.5 MC | PM_Total | Total PM2.5 |
| PM-2.5 TEOM noise | noise | Measurement noise |

### USB/Auto Export Format

| Column | Mapping | Description |
|--------|---------|-------------|
| Date, Time | time | Timestamp |
| tmoStatusCondition_0 | status | Instrument status |
| tmoTEOMABaseMC_0 | PM_NV | Non-volatile PM2.5 |
| tmoTEOMAMC_0 | PM_Total | Total PM2.5 |
| tmoTEOMANoise_0 | noise | Measurement noise |

## Measurement Parameters

| Parameter | Unit | Description |
|-----------|------|-------------|
| PM_Total | μg/m³ | Total PM2.5 mass concentration |
| PM_NV | μg/m³ | Non-volatile PM2.5 concentration |
| noise | - | TEOM measurement noise |

## Data Processing

### Data Reading

- Unifies column names across different data formats
- Handles various time formats. The TEOM host writes the month in the operating
  system's language, so the same instrument emits `07 - 六月 - 2025 12:00:00`
  on a Chinese UI and `10 - Aug - 2026 00:00:01` after the machine is switched
  to English. Both names — plus a plain number — are mapped to `06`/`08` before
  parsing, so a directory may freely mix them
- Converts all measurement values to numeric format
- Removes duplicate timestamps and invalid indices

### Quality Control

The TEOM reader uses the declarative **QCFlagBuilder** system with the following rules:

```
+-----------------------------------------------------------------------+
|                         QC Thresholds                                 |
+-----------------------------------------------------------------------+
| MAX_NOISE          = 0.01                                             |
| MIN_VOL_FRAC       = 0.01      PM_NV / PM_Total minimum               |
| MAX_VOL_FRAC       = 0.9       PM_NV / PM_Total maximum               |
| STATUS_OK          = 0         (status is a 32-bit bitfield)          |
| ERROR_STATES       = bits 0-31 (any set warning bit = error)          |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
|                            _QC() Pipeline                             |
+-----------------------------------------------------------------------+
|                                                                       |
|  [Pre-process] Calculate volatile fraction (PM_NV / PM_Total)         |
|       |                                                               |
|       v                                                               |
|  +-------------------------+                                          |
|  | Rule: Status Error      |                                          |
|  +-------------------------+                                          |
|  | Any warning bit set     |                                          |
|  +-------------------------+                                          |
|           |                                                           |
|           v                                                           |
|  +-------------------------+    +-------------------------+           |
|  | Rule: High Noise        |    | Rule: Non-positive      |           |
|  +-------------------------+    +-------------------------+           |
|  | noise > 0.01            |    | PM_Total <= 0 OR        |           |
|  +-------------------------+    | PM_NV <= 0              |           |
|           |                     +-------------------------+           |
|           v                              |                            |
|  +-------------------------+             v                            |
|  | Rule: NV > Total        |    +-------------------------+           |
|  +-------------------------+    | Rule: Invalid Vol Frac  |           |
|  | PM_NV > PM_Total        |    +-------------------------+           |
|  | (physically impossible) |    | Ratio > 0.9 OR < 0.01   |           |
|  +-------------------------+    +-------------------------+           |
|           |                              |                            |
|           v                              v                            |
|  +-------------------------+    +-------------------------+           |
|  | Rule: Spike             |    | Rule: Insufficient      |           |
|  +-------------------------+    +-------------------------+           |
|  | Sudden value change     |    | < 50% hourly data       |           |
|  | (vectorized detection)  |    | completeness            |           |
|  +-------------------------+    +-------------------------+           |
|                                                                       |
+-----------------------------------------------------------------------+
```

#### QC Rules Applied

| Rule | Condition | Description |
|------|-----------|-------------|
| **Status Error** | Any non-whitelisted warning bit set | `status` is a 32-bit bitfield (TEOM manual Table A-1); tested bitwise so individual conditions (e.g. `536870912` = Dryer A) can be whitelisted via `ignored_status_errors` |
| **High Noise** | noise ≥ 0.01 | Measurement noise exceeds threshold |
| **Non-positive** | PM_Total ≤ 0 OR PM_NV ≤ 0 | Non-positive concentration values |
| **NV > Total** | PM_NV > PM_Total | Non-volatile exceeds total (physically impossible) |
| **Invalid Vol Frac** | Ratio < 0 OR > 1 | Volatile fraction outside valid range (0-1) |
| **Spike** | Sudden value change | Unreasonable sudden change detected |
| **Insufficient** | < 50% hourly data | Less than 50% hourly data completeness |

#### Status Condition Register

`status` (`System status` / `tmoStatusCondition_0`) is a **32-bit bitfield**, not
a flat code: the instrument OR-sums every active warning and reports the decimal
sum. A status of `24` is therefore two conditions at once (`8 | 16`), not a
condition numbered 24.

The reader carries this table as `Reader.STATUS_BITS`, which is what decodes the
register into `df.attrs['status_conditions']` — so a status of `8` is reported as
*Ambient RH & Temp sensor* rather than left for the reader of a log to look up.
"A"/"B" denote the FDMS dual-channel sides. Source: TEOM 1405 / 1405-F manual,
Appendix A, Table A-1.

| Bit | Decimal | Condition |
|-----|---------|-----------|
| 30 | `1073741824` | %RH High Side A (>=98%) |
| 29 | `536870912` | Dryer A (>2) |
| 28 | `268435456` | Cooler A (>0.5C deviation) |
| 27 | `134217728` | Exchange Filter A (>90) |
| 26 | `67108864` | Flow A (>10% deviation) |
| 25 | `33554432` | Heaters Side A (>2% deviation) |
| 24 | `16777216` | Mass Transducer A (<10Hz) |
| 22 | `4194304` | %RH High Side B (>=98%) |
| 21 | `2097152` | Dryer B (>2) |
| 20 | `1048576` | Cooler B (>0.5C deviation) |
| 19 | `524288` | Exchange Filter B (>90) |
| 18 | `262144` | Flow B (>10% deviation) |
| 17 | `131072` | Heaters Side B (>2% deviation) |
| 16 | `65536` | Mass Transducer B (<10Hz) |
| 14 | `16384` | User I/O |
| 13 | `8192` | FDMS Device |
| 12 | `4096` | Head 1 |
| 11 | `2048` | Head 0 |
| 10 | `1024` | MFC 1 |
| 9 | `512` | MFC 0 |
| 8 | `256` | System Bus |
| 7 | `128` | Vacuum Pressure (<0.1 atm) |
| 6 | `64` | Case/Cap Heater (>2% deviation) |
| 5 | `32` | FDMS Valve |
| 4 | `16` | Bypass Flow (>10% deviation) |
| 3 | `8` | Ambient RH & Temp sensor |
| 2 | `4` | Database (log failure) |
| 1 | `2` | Enclosure Temp (>60C) |
| 0 | `1` | Power Failure |

Bits 15, 23 and 31 are not assigned in Table A-1. Any of them being set still
counts as a `Status Error` — `ERROR_STATES` covers all 32 bits — it simply has no
name to report.

To stop treating one condition as an error, whitelist its decimal value; bitwise
testing means it stays whitelisted no matter what else is co-set:

```python
RawDataReader('TEOM', path, ignored_status_errors=[536870912])  # ignore Dryer A
```

## Output Data

The processed data contains the following columns:

| Column | Unit | Description |
|--------|------|-------------|
| PM_Total | μg/m³ | Total PM2.5 mass concentration |
| PM_NV | μg/m³ | Non-volatile PM2.5 concentration |

!!! note "QC_Flag Handling"

    - The intermediate file (`_read_teom_qc.pkl/csv`) contains the `QC_Flag` column
    - The final output has invalid data set to NaN and `QC_Flag` column removed

## Usage Example

```python
from datetime import datetime
from pathlib import Path

from AeroViz import RawDataReader

# Set data path and time range
data_path = Path('/path/to/your/data/folder')
start_time = datetime(2024, 2, 1)
end_time = datetime(2024, 3, 31, 23, 59, 59)

# Read and process TEOM data
teom_data = RawDataReader(
    instrument='TEOM',
    path=data_path,
    reset=True,
    qc='1MS',
    start=start_time,
    end=end_time,
    mean_freq='1h',
)

# Show processed data
print("\nProcessed TEOM data:")
print(teom_data.head())
```