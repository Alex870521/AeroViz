# Scanning Mobility Particle Sizer (SMPS)

The SMPS is an instrument used for measuring particle size distributions in the nanometer range.

::: AeroViz.rawDataReader.script.SMPS.Reader

## Data Format

- File format:
    - `.txt` files (tab-delimited) from AIM 8.x / 9.x / **10.3**
    - `.csv` files (comma-delimited) from AIM **11.x**
- Sampling frequency: 6 minutes (typical)
- File naming pattern: `*.txt` or `*.csv`
- Timestamp formats:
    - mm/dd/yy HH:MM:SS (US format, older versions)
    - mm/dd/yyyy HH:MM:SS (US format, newer versions)
    - dd/mm/yyyy HH:MM:SS (EU format)
- **Default size grid: 11.8–593.5 nm (110 bins) on AIM 10.3; 11.34–615.27 nm
  (112 bins) on AIM 11.x.** A folder mixing both versions cannot be
  outer-joined safely — see "Mixed AIM versions" below.

## Measurement Parameters

The SMPS provides particle size distribution measurements:

| Parameter | Value | Description |
|-----------|-------|-------------|
| Size range | 11.8-593.5 nm | Default particle diameter range |
| Output | dN/dlogDp | Number concentration per size bin |
| Unit | #/cm³ | Particle number concentration |

## Data Processing

### Data Reading

- Automatically detects and skips header rows
- Supports multiple date formats based on AIM version
- Handles transposed data formats
- Extracts and sorts particle size columns numerically
- Validates size range against expected settings

### Quality Control

The SMPS reader uses the declarative **QCFlagBuilder** system with the following rules:

```
+-----------------------------------------------------------------------+
|                         QC Thresholds                                 |
+-----------------------------------------------------------------------+
| MIN_HOURLY_COUNT  = 5        measurements per hour                    |
| MIN_TOTAL_CONC    = 2000     #/cm³                                    |
| MAX_TOTAL_CONC    = 1e7      #/cm³                                    |
| MAX_LARGE_BIN_CONC= 4000     dN/dlogDp (DMA water ingress indicator)  |
| LARGE_BIN_THRESH  = 400      nm                                       |
| STATUS_OK         = "Normal Scan"   (for `Status Flag` column)        |
| SECONDARY status  = empty or "Normal Scan" (`Instrument Errors` col)  |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
|                            _QC() Pipeline                             |
+-----------------------------------------------------------------------+
|                                                                       |
|  [Pre-process] Apply size range filter, calculate total concentration |
|       |                                                               |
|       v                                                               |
|  +-----------------------------------------+                          |
|  | Rule: Status Error  (OR of two columns) |                          |
|  +-----------------------------------------+                          |
|  | `Status Flag` != "Normal Scan", OR      |                          |
|  | `Instrument Errors` non-empty           |                          |
|  | (each empty form '' / 'nan' / 'None'    |                          |
|  | and "Normal Scan" exempted; tokens in   |                          |
|  | `ignored_status_errors` exempted)       |                          |
|  +-----------------------------------------+                          |
|           |                                                           |
|           v                                                           |
|  +-------------------------+    +-------------------------+           |
|  | Rule: Insufficient      |    | Rule: Invalid Number    |           |
|  +-------------------------+    |       Conc              |           |
|  | < 5 measurements        |    +-------------------------+           |
|  | per hour                |    | Total conc. outside     |           |
|  +-------------------------+    | range (2000-1e7 #/cm³)  |           |
|                                 +-------------------------+           |
|           |                              |                            |
|           v                              v                            |
|           |                     +-------------------------+           |
|           |                     | Rule: DMA Water Ingress |           |
|           |                     +-------------------------+           |
|           |                     | Bins > 400nm with       |           |
|           |                     | conc. > 4000 dN/dlogDp  |           |
|           |                     | (indicates water in DMA)|           |
|           |                     +-------------------------+           |
|                                                                       |
+-----------------------------------------------------------------------+
```

#### QC Rules Applied

| Rule | Condition | Description |
|------|-----------|-------------|
| **Status Error** | `Status Flag` ≠ "Normal Scan" **OR** `Instrument Errors` non-empty | Older AIM 10.3 sub-versions use `Status Flag` (e.g. `"Conditioner Temperature Error"`); newer AIM 10.3 + AIM 11.x put hardware warnings in `Instrument Errors` (e.g. `"Low aerosol flow"`). Both columns are checked and OR'd. Empty cells (`''`, `'nan'`, Python-None-stringified `'None'`) and the positive `"Normal Scan"` sentinel (some instruments write it into `Instrument Errors` instead of leaving it empty, e.g. FS) are never errors. Tokens listed in the `ignored_status_errors` kwarg are exempted, with comma-split semantics — `"Low aerosol flow,Neutralizer not active"` passes when both tokens are whitelisted. |
| **Insufficient** | < 5 measurements/hour | Less than 5 measurements per hour |
| **Invalid Number Conc** | Total < 2000 OR > 1e7 #/cm³ | Total number concentration outside valid range |
| **DMA Water Ingress** | Bins >400nm > 4000 dN/dlogDp | Water contamination in DMA column |

#### Whitelisting benign status warnings

If an instrument runs in a known-low-aerosol mode and reports `"Low aerosol
flow"` on every scan, every row trips Status Error. Pass
`ignored_status_errors=[...]` to RawDataReader to suppress those tokens:

```python
df = RawDataReader(
    instrument='SMPS', path='/data/TP_SMPS',
    start='2026-01-01', end='2026-05-31',
    ignored_status_errors=['Low aerosol flow', 'Neutralizer not active'],
)
```

Token-level matching: a row passes when EVERY comma-split token is either
the OK sentinel or in the whitelist. `"Low aerosol flow,Sheath flow
error"` still fails because `Sheath flow error` is not whitelisted.

#### Size Distribution QC Visualization

```
    dN/dlogDp
       ^
       |
  4000 +                              ........... MAX_LARGE_BIN_CONC
       |      ___                     :          (DMA water ingress)
       |     /   \                    :
       |    /     \____               :
       +---+------+-------+-------+---+---> Dp (nm)
          11.8   100     400    593.5
                          ^
                    LARGE_BIN_THRESHOLD
```

## Output Data

The processed data contains:

| Column | Unit | Description |
|--------|------|-------------|
| Size bins | dN/dlogDp | Number concentration for each particle size |

!!! note "QC_Flag Handling"

    - The intermediate file (`_read_smps_qc.pkl/csv`) contains the `QC_Flag` column
    - The final output has invalid data set to NaN and `QC_Flag` column removed

## Mixed AIM versions

A single folder is allowed to contain a mix of AIM versions, but the reader
treats each scan grid as its own logical instrument — concatenating
mismatched grids would create NaN-only columns that downstream completeness
checks read as 100% Insufficient.

**Partition by bin grid (auto-applied):** Files are bucketed by their sorted
size-bin tuple. The bucket with the most rows wins; the others are dropped
before concat with a warning naming every skipped file. The picked-by-row-count
rule means a swarm of tiny minority files cannot outvote one large export
just by file count.

To process the dropped bucket explicitly, either move those files to a
separate folder, or pass `size_range=` to force `_raw_reader` to reject
files outside that exact range:

```python
# Process only AIM 11.x scans in a mixed folder:
df = RawDataReader('SMPS', path=mixed_folder, size_range=(11.34, 615.27))
```

**Metadata column aliases:** AIM 11.x renames many metadata columns that
carry the same physical quantity as AIM 10.3. The reader rewrites the
AIM 11.x form to the AIM 10.3 form on every parsed file, so a folder of
either version (or a partitioned-down folder) produces a consistent
schema downstream. The 9 renamed pairs:

| AIM 11.x | → | AIM 10.3 canonical |
|---|---|---|
| `Total Concentration (#/cm³)` | → | `Total Conc. (#/cm)` |
| `Aerosol Temperature (C)` | → | `Sample Temp (C)` |
| `Aerosol Humidity (%)` | → | `Relative Humidity (%)` |
| `Aerosol Density (g/cm³)` | → | `Density (g/cm)` |
| `Impactor D50 (nm)` | → | `D50 (nm)` |
| `Test Name` | → | `Title` |
| `Geo. Std. Dev` | → | `Geo. Std. Dev.` |
| `DMA Column transit time Tf (s)` | → | `tf (s)` |
| `DMA Exit to Optical Detector Td (s)` | → | `td + 0.5 (s)` |

AIM 11.x columns that have no AIM 10.3 equivalent — the 4-way error split
(`Classifier Errors` / `Detector Status` / `Communication Status` /
`Neutralizer Status`), granular DMA timings (`THIGH` / `TLOW` / `TUP` /
`TDOWN`), `Sheath Pressure/Temp/Humidity`, etc. — are intentionally kept
under their AIM 11.x names. Collapsing them onto AIM 10.3's coarser
`Instrument Errors` / `Scan Time` would lose information.

## Notes

- Different AIM software versions may produce different file formats — see
  "Mixed AIM versions" above for how the reader isolates and reconciles them
- Size range validation ensures data quality
- DMA water ingress detection: High concentrations in bins >400nm indicate water contamination in the DMA column
- Automatic format detection and parsing
