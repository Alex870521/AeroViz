# AeroViz Data Processing Flow

This document describes the data processing pipeline architecture in AeroViz,
including existing features and planned enhancements.

---

## Pipeline Overview

```
====================================================================================
                            AeroViz Data Pipeline
====================================================================================

    +----------------+
    |   Raw Data     |
    |   Files        |
    | (.txt/.csv)    |
    +-------+--------+
            |
            v
+-----------+------------+
|                        |
|  STAGE 1: _raw_reader  |  [IMPLEMENTED]
|                        |
|  - Parse file format   |
|  - Extract timestamp   |
|  - Convert columns     |
|                        |
+-----------+------------+
            |
            v
    +-------+--------+
    |  Raw DataFrame |
    |  (raw.pkl)     |
    +-------+--------+
            |
            v
+-----------+------------+
|                        |
|  STAGE 2: _QC          |  [IMPLEMENTED]
|                        |
|  - Check raw data      |
|  - Status validation   |
|  - Range checking      |
|  - Add QC_Flag column  |
|  - Store QC summary    |
|                        |
+-----------+------------+
            |
            v
+-----------+------------+
|                        |
|  STAGE 3: _process     |  [IMPLEMENTED]
|                        |
|  - Calc coefficients   |
|  - Derive parameters   |
|    (abs, AAE, SAE...)  |
|  - Validate derived    |
|  - Update QC_Flag      |
|  - Output QC Summary   |
|                        |
+-----------+------------+
            |
            v
    +-------+--------+
    |  QC DataFrame  |
    |  (qc.pkl)      |
    +-------+--------+
            |
            v
    +-------+--------+
    | Final Output   |
    | (output.csv)   |
    +----------------+

====================================================================================
```

---

## Detailed Stage Flow

```
+-----------------------------------------------------------------------------------+
|                                                                                   |
|   RAW FILES                          STAGE 1                    STAGE 2           |
|                                                                                   |
|   +----------+                    +-------------+            +-------------+      |
|   | file1.txt|--+                 |             |            |             |      |
|   +----------+  |                 | _raw_reader |            |    _QC      |      |
|   +----------+  |   +-------+     |             |            |             |      |
|   | file2.txt|--+-->| glob  |---->| - parse     |----------->| - n_sigma   |      |
|   +----------+  |   +-------+     | - timestamp |            | - IQR       |      |
|   +----------+  |                 | - convert   |            | - rolling   |      |
|   | file3.csv|--+                 |             |            | - threshold |      |
|   +----------+                    +-------------+            +------+------+      |
|                                                                     |             |
|                                                                     v             |
|                                                              +------+------+      |
|                                                              | QC Data     |      |
|                                                              | - outliers  |      |
|                                                              |   removed   |      |
|                                                              +-------------+      |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

---

## Planned: QC_Flag System

```
+-----------------------------------------------------------------------------------+
|                                                                                   |
|   STAGE 3: QC_Flag Integration                                                    |
|                                                                                   |
|   +-------------------+         +-------------------+         +----------------+  |
|   |                   |         |                   |         |                |  |
|   |   Raw Data        |         |   QC Process      |         |   Flagged Data |  |
|   |                   |         |                   |         |                |  |
|   |   time    | value |         |   Check each      |         |   time  |value |  |
|   |   --------|-------|  -----> |   data point      |  -----> |   ------|------|  |
|   |   00:00   | 1234  |         |   against rules   |         |   00:00 | 1234 |  |
|   |   01:00   | -999  |         |                   |         |   01:00 | -999 |  |
|   |   02:00   | 99999 |         |   Assign flag     |         |   02:00 |99999 |  |
|   |   03:00   | NaN   |         |   instead of      |         |   03:00 | NaN  |  |
|   |   04:00   | 5678  |         |   removing        |         |   04:00 | 5678 |  |
|   |                   |         |                   |         |                |  |
|   +-------------------+         +-------------------+         +-------+--------+  |
|                                                                       |           |
|                                                                       v           |
|                                                               +-------+--------+  |
|                                                               |   QC_Flag      |  |
|   FLAG DEFINITIONS:                                           |   Column       |  |
|   +------------------+                                        |----------------|  |
|   | 0 = Valid        |                                        |   Valid        |  |
|   | 1 = Below_Detect |                                        |   Below_Detect |  |
|   | 2 = Above_Range  |                                        |   Above_Range  |  |
|   | 3 = Instr_Error  |                                        |   Missing      |  |
|   | 4 = Outlier      |                                        |   Valid        |  |
|   | 5 = Missing      |                                        +----------------+  |
|   | 6 = Suspect      |                                                            |
|   +------------------+                                                            |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

---

## Planned: Instrument-Specific Processing

```
+-----------------------------------------------------------------------------------+
|                                                                                   |
|   STAGE 4: _process Method (After QC)                                             |
|                                                                                   |
|   +------------------+                                                            |
|   |   QC Data        |                                                            |
|   |   (with flags)   |                                                            |
|   +--------+---------+                                                            |
|            |                                                                      |
|            v                                                                      |
|   +--------+---------+                                                            |
|   |   INSTRUMENT     |                                                            |
|   |   TYPE CHECK     |                                                            |
|   +--------+---------+                                                            |
|            |                                                                      |
|   +--------+------------------+------------------+------------------+             |
|   |                           |                  |                  |             |
|   v                           v                  v                  v             |
|  +-------------+    +-------------+    +-------------+    +-------------+         |
|  | SIZE DISTR  |    | BLACK CARBON|    | SCATTERING  |    |   OTHERS    |         |
|  | SMPS/APS    |    | AE33/BC1054 |    | NEPH/Aurora |    | TEOM/OCEC   |         |
|  +------+------+    +------+------+    +------+------+    +------+------+         |
|         |                  |                  |                  |                |
|         v                  v                  v                  v                |
|  +-------------+    +-------------+    +-------------+    +-------------+         |
|  | CALCULATE:  |    | CALCULATE:  |    | CALCULATE:  |    | CALCULATE:  |         |
|  |             |    |             |    |             |    |             |         |
|  | - total_N   |    | - abs_370   |    | - sca_450   |    | - PM_mass   |         |
|  | - total_S   |    | - abs_520   |    | - sca_550   |    | - OC/EC     |         |
|  | - total_V   |    | - abs_880   |    | - sca_700   |    |             |         |
|  | - GMD_N     |    | - AAE       |    | - SAE       |    |             |         |
|  | - GMD_S     |    | - eBC       |    |             |    |             |         |
|  | - GMD_V     |    |             |    |             |    |             |         |
|  | - GSD       |    |             |    |             |    |             |         |
|  +------+------+    +------+------+    +------+------+    +------+------+         |
|         |                  |                  |                  |                |
|         +------------------+------------------+------------------+                |
|                            |                                                      |
|                            v                                                      |
|                   +--------+--------+                                             |
|                   |  Final Output   |                                             |
|                   |  DataFrame      |                                             |
|                   |                 |                                             |
|                   |  - Raw columns  |                                             |
|                   |  - Derived      |                                             |
|                   |    parameters   |                                             |
|                   |  (no QC_Flag)   |                                             |
|                   +-----------------+                                             |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

---

## Code Structure Flow

```
+-----------------------------------------------------------------------------------+
|                                                                                   |
|   RawDataReader() Call Flow                                                       |
|                                                                                   |
|   User Code                         AbstractReader                                |
|   +-----------------+               +----------------------------------+          |
|   |                 |               |                                  |          |
|   | RawDataReader(  |               |  __init__()                      |          |
|   |   'SMPS',       | ------------> |    - Set paths                   |          |
|   |   path=...,     |               |    - Init logger                 |          |
|   |   start=...,    |               |    - Set QC options              |          |
|   |   end=...,      |               |                                  |          |
|   | )               |               +----------------------------------+          |
|   |                 |                              |                              |
|   +-----------------+                              v                              |
|                                     +----------------------------------+          |
|                                     |                                  |          |
|                                     |  __call__(start, end, freq)      |          |
|                                     |    |                             |          |
|                                     |    +-> _run()                    |          |
|                                     |          |                       |          |
|                                     |          +-> _read_raw_files()   |          |
|                                     |          |     |                 |          |
|                                     |          |     +-> _raw_reader() | <-- Each |          |
|                                     |          |     +-> _QC()         |     file |          |
|                                     |          |                       |          |
|                                     |          +-> _timeIndex_process()|          |
|                                     |          +-> _outlier_process()  |          |
|                                     |          +-> _save_data()        |          |
|                                     |                                  |          |
|                                     |    +-> _generate_report()        |          |
|                                     |    +-> resample(mean_freq)       |          |
|                                     |    +-> return DataFrame          |          |
|                                     |                                  |          |
|                                     +----------------------------------+          |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

---

## Design Philosophy: Single vs Multi-Instrument Processing

```
+-----------------------------------------------------------------------------------+
|                                                                                   |
|   SEPARATION OF CONCERNS                                                          |
|                                                                                   |
|   +----------------------------------+    +----------------------------------+    |
|   |                                  |    |                                  |    |
|   |   RawDataReader + _process()     |    |   DataProcess Module             |    |
|   |   SINGLE INSTRUMENT              |    |   MULTI-INSTRUMENT               |    |
|   |                                  |    |                                  |    |
|   +----------------------------------+    +----------------------------------+    |
|   |                                  |    |                                  |    |
|   |   Input:  One instrument data    |    |   Input:  Multiple DataFrames   |    |
|   |   Output: Complete parameters    |    |   Output: Combined analysis     |    |
|   |                                  |    |                                  |    |
|   |   Examples:                      |    |   Examples:                      |    |
|   |                                  |    |                                  |    |
|   |   SMPS._process()                |    |   SizeDistr.merge()              |    |
|   |   - total_N, total_S, total_V    |    |   - SMPS + APS merge             |    |
|   |   - GMD_N, GMD_S, GMD_V          |    |   - Overlap correction           |    |
|   |   - GSD                          |    |                                  |    |
|   |                                  |    |   Optical.mie_calculation()      |    |
|   |   APS._process()                 |    |   - PSD + Refractive Index       |    |
|   |   - total_N, total_S, total_V    |    |   - Calculate ext, ssa, g        |    |
|   |   - GMD_N, GMD_S, GMD_V          |    |                                  |    |
|   |   - GSD                          |    |   Optical.IMPROVE()              |    |
|   |                                  |    |   - sca + abs + chemistry        |    |
|   |   AE33._process()                |    |   - Reconstruct extinction       |    |
|   |   - abs_370...abs_950            |    |                                  |    |
|   |   - AAE                          |    |   Chemistry.mass_closure()       |    |
|   |   - eBC                          |    |   - Multiple species             |    |
|   |                                  |    |   - Reconstruct PM mass          |    |
|   |   NEPH._process()                |    |                                  |    |
|   |   - sca_450, sca_550, sca_700    |    |   Chemistry.ISOROPIA()           |    |
|   |   - SAE                          |    |   - Ions + meteorology           |    |
|   |                                  |    |   - Thermodynamic equilibrium    |    |
|   +----------------------------------+    +----------------------------------+    |
|                                                                                   |
|   ONE CALL = COMPLETE OUTPUT              COMBINE MULTIPLE READER OUTPUTS         |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

---

## Current Flow (with _process)

```
+-----------------------------------------------------------------------------------+
|                                                                                   |
|   IMPLEMENTED: _QC() + _process() separation                                      |
|                                                                                   |
|   _read_raw_files()                                                               |
|   |                                                                               |
|   +---> for each file:                                                            |
|   |       |                                                                       |
|   |       +---> _raw_reader(file)     # Parse raw data                            |
|   |                                                                               |
|   +---> concat all DataFrames                                                     |
|   |                                                                               |
|   +---> _timeIndex_process()          # Align time index                          |
|   |                                                                               |
|   +---> _QC()                         # Quality control (raw data only)           |
|   |       |                                                                       |
|   |       +---> Status validation     # Check instrument status                   |
|   |       +---> Range checking        # Check raw value ranges                    |
|   |       +---> Completeness check    # Check data completeness                   |
|   |       +---> Add QC_Flag column    # Flag instead of remove                    |
|   |       +---> Store QC summary      # For combined output in _process           |
|   |                                                                               |
|   +---> _process()                    # Calculate derived parameters              |
|   |       |                                                                       |
|   |       +---> if AE33/AE43/BC1054/MA350:  # Absorption instruments              |
|   |       |       _absCoe()           # Calculate abs coefficients                |
|   |       |       calc_AAE()          # Calculate AAE                             |
|   |       |       validate_AAE()      # Check AAE range, update QC_Flag           |
|   |       |                                                                       |
|   |       +---> if NEPH/Aurora:       # Scattering instruments                    |
|   |       |       _scaCoe()           # Calculate sca coefficients                |
|   |       |       calc_SAE()          # Calculate SAE                             |
|   |       |                                                                       |
|   |       +---> if SMPS:              # Size distribution                         |
|   |       |       calc dN, dS, dV     # Number, surface, volume distributions     |
|   |       |       total, GMD, GSD     # For num/surf/vol                          |
|   |       |       mode, ultra/accum   # Mode peak and contributions               |
|   |       |                                                                       |
|   |       +---> if APS:               # Size distribution with cutoffs            |
|   |               calc dN, dS, dV     # Number, surface, volume distributions     |
|   |               total_1um/2.5um/all # Totals at size cutoffs                    |
|   |               GMD, GSD, mode      # For full range                            |
|   |                                                                               |
|   |       +---> Output QC Summary     # Combined summary from _QC + _process      |
|   |                                                                               |
|   +---> return (raw_data, processed_data)                                         |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

---

## User Workflow Comparison

```
+-----------------------------------------------------------------------------------+
|                                                                                   |
|   CURRENT WORKFLOW (Complicated)                                                  |
|                                                                                   |
|   # Step 1: Read raw data                                                         |
|   df_smps = RawDataReader('SMPS', path, ...)   # Only raw columns                 |
|                                                                                   |
|   # Step 2: User must manually calculate derived parameters                       |
|   from AeroViz.dataProcess.SizeDistr import calc_parameters                       |
|   df_smps = calc_parameters(df_smps)           # Extra step needed                |
|                                                                                   |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|   PROPOSED WORKFLOW (Simple)                                                      |
|                                                                                   |
|   # One call = everything                                                         |
|   df_smps = RawDataReader('SMPS', path, ...)                                      |
|                                                                                   |
|   # Output includes:                                                              |
|   # - total_num, total_surf, total_vol                                            |
|   # - GMD_num, GMD_surf, GMD_vol                                                  |
|   # - GSD_num, GSD_surf, GSD_vol                                                  |
|   # - mode_num, mode_surf, mode_vol                                               |
|   # - ultra_num, accum_num (mode contributions)                                   |
|   # (Invalid data already set to NaN, QC_Flag removed)                            |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

---

## File Output Structure

```
{instrument}_outputs/
|
+-- _read_{instrument}_raw.pkl      # Raw data (no QC_Flag)
+-- _read_{instrument}_raw.csv
|
+-- _read_{instrument}_qc.pkl       # QC'd data (with QC_Flag)
+-- _read_{instrument}_qc.csv
|
+-- output_{instrument}.csv         # Final resampled output (no QC_Flag, invalid → NaN)
|
+-- report.json                     # Quality report
|
+-- {instrument}.log                # Processing log
```

---

## Supported Instruments

| Category          | Instrument | Data Type       | Size Range     |
|-------------------|------------|-----------------|----------------|
| Size Distribution | SMPS       | dN/dlogDp       | 11.8-593.5 nm  |
| Size Distribution | APS        | dN/dlogDp       | 0.5-20 um      |
| Size Distribution | GRIMM      | dN/dlogDp       | 0.25-32 um     |
| Black Carbon      | AE33/AE43  | Absorption, BC  | 7 wavelengths  |
| Black Carbon      | BC1054     | Absorption, BC  | 10 wavelengths |
| Black Carbon      | MA350      | Absorption, BC  | 5 wavelengths  |
| Scattering        | NEPH       | Scattering coef | 450/550/700 nm |
| Scattering        | Aurora     | Scattering coef | 450/525/635 nm |
| Mass              | TEOM       | PM mass         | continuous     |
| Mass              | BAM1020    | PM mass         | hourly         |
| Carbon            | OCEC       | OC/EC           | filter-based   |
| Gas               | VOC        | VOC species     | various        |
| Reference         | EPA        | Multiple        | hourly         |

---

## Usage Example

```python
from AeroViz import RawDataReader

df = RawDataReader(
    instrument='SMPS',
    path='/path/to/data',
    reset=True,  # True: reprocess | False: use cache | 'append': add new
    qc=True,  # True: apply QC | False: skip QC
    start='2024-01-01',
    end='2024-06-30',
    mean_freq='1h',
)
```

---

## QC Methods Available (in qc.py)

| Method                       | Description                              |
|------------------------------|------------------------------------------|
| `n_sigma`                    | N standard deviation filter              |
| `iqr`                        | Interquartile range filter               |
| `time_aware_rolling_iqr`     | Rolling window IQR                       |
| `time_aware_std_QC`          | Rolling window std                       |
| `bidirectional_trend_std_QC` | Trend-aware std QC                       |
| `filter_error_status`        | Status code filter                       |
| `hourly_completeness_QC`     | Data completeness check                  |
| `spike_detection`            | Vectorized spike detection (change rate) |

---

## QC Flag System Architecture

```
+------------------------------------------------------------------+
|                     QC Flag System (New)                         |
+------------------------------------------------------------------+
|                                                                  |
|  +------------------+     +------------------+                   |
|  |     QCRule       |     |  QCFlagBuilder   |                   |
|  +------------------+     +------------------+                   |
|  | - name           |     | - rules[]        |                   |
|  | - condition()    |---->| + add_rule()     |                   |
|  | - description    |     | + add_rules()    |                   |
|  +------------------+     | + apply()        |                   |
|                           | + get_summary()  |                   |
|                           +------------------+                   |
|                                   |                              |
|                                   v                              |
|                         +------------------+                     |
|                         |   DataFrame      |                     |
|                         +------------------+                     |
|                         | + QC_Flag column |                     |
|                         | "Valid" or       |                     |
|                         | "Rule1, Rule2"   |                     |
|                         +------------------+                     |
|                                                                  |
+------------------------------------------------------------------+
|  Instruments Using QCFlagBuilder:                                |
|  AE33, AE43, BC1054, MA350, SMPS, APS, NEPH, Aurora,             |
|  TEOM, BAM1020, OCEC, IGAC, EPA                                  |
|                                                                  |
|  Instruments with _process() method:                             |
|  AE33, AE43, BC1054, MA350, NEPH, Aurora, SMPS, APS              |
+------------------------------------------------------------------+
```

---

## Instrument QC Procedures

### Black Carbon Instruments

#### AE33 / AE43 Aethalometer

```
+-----------------------------------------------------------------------+
|                      _QC() + _process() Pipeline                      |
+-----------------------------------------------------------------------+
|                                                                       |
|  STAGE 1: _QC() - Raw Data Validation                                 |
|  +---------------------+    +---------------------+                   |
|  | Rule: Status Error  |    | Rule: Invalid BC    |                   |
|  +---------------------+    +---------------------+                   |
|  | Status contains:    |    | BC <= 0 OR          |                   |
|  | - 1   (Tape adv.)   |    | BC > 20000 ng/m3    |                   |
|  | - 2   (First meas.) |    +---------------------+                   |
|  | - 3   (Stopped)     |             |                                |
|  | - 4   (Flow error)  |             v                                |
|  | - 16  (LED calib.)  |    +---------------------+                   |
|  | - 32  (Calib. err.) |    | Rule: Insufficient  |                   |
|  | - 384 (Tape error)  |    +---------------------+                   |
|  | - 1024 (Stability)  |    | < 50% hourly data   |                   |
|  | - 2048 (Clean air)  |    +---------------------+                   |
|  | - 4096 (Optical)    |                                              |
|  +---------------------+                                              |
|                                                                       |
|  STAGE 2: _process() - Derived Parameters + Validation                |
|  +---------------------+    +---------------------+                   |
|  | Calculate:          |    | Rule: Invalid AAE   |                   |
|  | - _absCoe()         |--->+---------------------+                   |
|  | - abs_370...abs_950 |    | AAE < -2.0 OR       |                   |
|  | - AAE, eBC          |    | AAE > -0.7          |                   |
|  +---------------------+    +---------------------+                   |
|                                                                       |
+-----------------------------------------------------------------------+
Output: BC1-BC7, abs_370-950, abs_550, AAE, eBC, QC_Flag
```

#### BC1054 Black Carbon Monitor

```
+-----------------------------------------------------------------------+
|                      _QC() + _process() Pipeline                      |
+-----------------------------------------------------------------------+
|                                                                       |
|  STAGE 1: _QC() - Raw Data Validation                                 |
|  [Pre-filter] Remove consecutive duplicate rows                       |
|       |                                                               |
|       v                                                               |
|  +---------------------+    +---------------------+                   |
|  | Rule: Status Error  |    | Rule: Invalid BC    |                   |
|  +---------------------+    +---------------------+                   |
|  | Error codes:        |    | BC <= 0 OR          |                   |
|  | - 1     (Power)     |    | BC > 20000 ng/m3    |                   |
|  | - 2     (Sensor)    |    +---------------------+                   |
|  | - 4     (Tape)      |             |                                |
|  | - 8     (Maint.)    |             v                                |
|  | - 16    (Flow)      |    +---------------------+                   |
|  | - 32    (Auto adv.) |    | Rule: Insufficient  |                   |
|  | - 64    (Detector)  |    +---------------------+                   |
|  | - 256   (Range)     |    | < 50% hourly data   |                   |
|  | - 512   (Nozzle)    |    +---------------------+                   |
|  | - 1024  (SPI link)  |                                              |
|  | - 2048  (Calib.)    |                                              |
|  | - 65536 (Tape move) |                                              |
|  +---------------------+                                              |
|                                                                       |
|  STAGE 2: _process() - Derived Parameters + Validation                |
|  +---------------------+    +---------------------+                   |
|  | Calculate:          |    | Rule: Invalid AAE   |                   |
|  | - _absCoe()         |--->+---------------------+                   |
|  | - abs_370...abs_950 |    | AAE < -2.0 OR       |                   |
|  | - AAE, eBC          |    | AAE > -0.7          |                   |
|  +---------------------+    +---------------------+                   |
|                                                                       |
+-----------------------------------------------------------------------+
Output: BC1-BC10, abs_370-950, abs_550, AAE, eBC, QC_Flag
```

#### MA350 Aethalometer

```
+-----------------------------------------------------------------------+
|                      _QC() + _process() Pipeline                      |
+-----------------------------------------------------------------------+
|                                                                       |
|  STAGE 1: _QC() - Raw Data Validation                                 |
|  +---------------------+    +---------------------+                   |
|  | Rule: Status Error  |    | Rule: Invalid BC    |                   |
|  +---------------------+    +---------------------+                   |
|  | Error codes:        |    | BC <= 0 OR          |                   |
|  | - 1 (Power)         |    | BC > 20000 ng/m3    |                   |
|  | - 2 (Start up)      |    +---------------------+                   |
|  | - 4 (Tape adv.)     |             |                                |
|  | - 16+ (Various)     |             v                                |
|  +---------------------+    +---------------------+                   |
|                             | Rule: Insufficient  |                   |
|                             +---------------------+                   |
|                             | < 50% hourly data   |                   |
|                             +---------------------+                   |
|                                                                       |
|  STAGE 2: _process() - Derived Parameters + Validation                |
|  +---------------------+    +---------------------+                   |
|  | Calculate:          |    | Rule: Invalid AAE   |                   |
|  | - _absCoe()         |--->+---------------------+                   |
|  | - abs_375...abs_880 |    | AAE < -2.0 OR       |                   |
|  | - AAE, eBC          |    | AAE > -0.7          |                   |
|  +---------------------+    +---------------------+                   |
|                                                                       |
+-----------------------------------------------------------------------+
Output: BC1-BC5, abs_375-880, abs_550, AAE, eBC, QC_Flag
```

---

### Size Distribution Instruments

#### SMPS (Scanning Mobility Particle Sizer)

```
+-----------------------------------------------------------------------+
|                         QC Thresholds                                 |
+-----------------------------------------------------------------------+
| MIN_HOURLY_COUNT  = 5        measurements per hour                    |
| MIN_TOTAL_CONC    = 2000     #/cm3                                    |
| MAX_TOTAL_CONC    = 1e7      #/cm3                                    |
| MAX_LARGE_BIN_CONC= 4000     dN/dlogDp (DMA water ingress indicator)  |
| LARGE_BIN_THRESH  = 400      nm                                       |
| STATUS_OK         = "Normal Scan"                                     |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
|                      _QC() + _process() Pipeline                      |
+-----------------------------------------------------------------------+
|                                                                       |
|  STAGE 1: _QC() - Raw Data Validation                                 |
|  +-------------------------+                                          |
|  | Rule: Status Error      |                                          |
|  +-------------------------+                                          |
|  | Status Flag !=          |                                          |
|  | "Normal Scan"           |                                          |
|  +-------------------------+                                          |
|           |                                                           |
|           v                                                           |
|  +-------------------------+    +-------------------------+           |
|  | Rule: Insufficient      |    | Rule: Invalid Number    |           |
|  +-------------------------+    |       Conc              |           |
|  | < 5 measurements        |    +-------------------------+           |
|  | per hour                |    | Total conc. outside     |           |
|  +-------------------------+    | range (2000-1e7 #/cm3)  |           |
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
|  STAGE 2: _process() - Size Distribution Statistics                   |
|  +---------------------------------------------------------------+   |
|  | Calculate from dN/dlogDp:                                      |   |
|  |   - dN (number), dS (surface), dV (volume) distributions       |   |
|  |                                                                 |   |
|  | For each weighting (num, surf, vol):                           |   |
|  |   - total_{weight}: Total concentration                        |   |
|  |   - GMD_{weight}: Geometric Mean Diameter                      |   |
|  |   - GSD_{weight}: Geometric Standard Deviation                 |   |
|  |   - mode_{weight}: Peak diameter                               |   |
|  |                                                                 |   |
|  | Mode contributions (for number):                               |   |
|  |   - ultra_num: fraction < 100 nm                               |   |
|  |   - accum_num: fraction 100-1000 nm                            |   |
|  +---------------------------------------------------------------+   |
|                                                                       |
+-----------------------------------------------------------------------+

         Size Distribution QC Visualization

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

#### APS (Aerodynamic Particle Sizer)

```
+-----------------------------------------------------------------------+
|                         QC Thresholds                                 |
+-----------------------------------------------------------------------+
| MIN_HOURLY_COUNT = 5      measurements per hour                       |
| MIN_TOTAL_CONC   = 1      #/cm3                                       |
| MAX_TOTAL_CONC   = 700    #/cm3                                       |
| STATUS_OK        = "0000 0000 0000 0000" (16-bit binary, all zeros)   |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
|                      Status Flag Bit Definitions                      |
|                        (from TSI RF command)                          |
+-----------------------------------------------------------------------+
| Bit 0 : Laser fault                                                   |
| Bit 1 : Total Flow out of range                                       |
| Bit 2 : Sheath Flow out of range                                      |
| Bit 3 : Excessive sample concentration                                |
| Bit 4 : Accumulator clipped (> 65535)                                 |
| Bit 5 : Autocal failed                                                |
| Bit 6 : Internal temperature < 10°C                                   |
| Bit 7 : Internal temperature > 40°C                                   |
| Bit 8 : Detector voltage out of range (±10% Vb)                       |
| Bit 9 : Reserved (unused)                                             |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
|                      _QC() + _process() Pipeline                      |
+-----------------------------------------------------------------------+
|                                                                       |
|  STAGE 1: _QC() - Raw Data Validation                                 |
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
|  STAGE 2: _process() - Size Distribution Statistics                   |
|  +---------------------------------------------------------------+   |
|  | Calculate from dN/dlogDp:                                      |   |
|  |   - dN (number), dS (surface), dV (volume) distributions       |   |
|  |                                                                 |   |
|  | Totals at size cutoffs (for num, surf, vol):                   |   |
|  |   - total_{weight}_1um: Sum for particles < 1 μm               |   |
|  |   - total_{weight}_2.5um: Sum for particles < 2.5 μm           |   |
|  |   - total_{weight}_all: Sum for all particles                  |   |
|  |                                                                 |   |
|  | Full range statistics:                                          |   |
|  |   - GMD_{weight}: Geometric Mean Diameter                      |   |
|  |   - GSD_{weight}: Geometric Standard Deviation                 |   |
|  |   - mode_{weight}: Peak diameter                               |   |
|  +---------------------------------------------------------------+   |
|                                                                       |
+-----------------------------------------------------------------------+

         APS Valid Concentration Range

    Total Conc (#/cm3)
       ^
   700 +-------------------------------- MAX_TOTAL_CONC
       |   +-----------------------+    (reject if exceeded)
       |   |    VALID RANGE        |
       |   +-----------------------+
     1 +-------------------------------- MIN_TOTAL_CONC
     0 +-------------------------------- (reject if below)
       +----------------------------> Time
```

---

### Scattering Instruments

#### NEPH / Aurora Nephelometer

```
+-----------------------------------------------------------------------+
|                         QC Thresholds                                 |
+-----------------------------------------------------------------------+
| MIN_SCAT_VALUE = 0       Mm^-1                                        |
| MAX_SCAT_VALUE = 2000    Mm^-1                                        |
| STATUS_OK      = 0       (numeric status code)                        |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
|                      _QC() + _process() Pipeline                      |
+-----------------------------------------------------------------------+
|                                                                       |
|  STAGE 1: _QC() - Raw Data Validation                                 |
|  +---------------------------+                                        |
|  | Rule: Status Error        |                                        |
|  +---------------------------+                                        |
|  | Status code != 0          |                                        |
|  | (if column available)     |                                        |
|  +---------------------------+                                        |
|           |                                                           |
|           v                                                           |
|  +---------------------------+    +---------------------------+       |
|  | Rule: No Data             |    | Rule: Invalid Scat Value  |       |
|  +---------------------------+    +---------------------------+       |
|  | All columns are NaN       |    | Value <= 0 OR             |       |
|  +---------------------------+    | Value > 2000 Mm^-1        |       |
|           |                       +---------------------------+       |
|           v                                |                          |
|  +---------------------------+             v                          |
|  | Rule: Invalid Scat Rel    |    +---------------------------+       |
|  +---------------------------+    | Rule: Insufficient        |       |
|  | Blue < Green < Red        |    +---------------------------+       |
|  | (violates physics)        |    | < 50% hourly data         |       |
|  +---------------------------+    +---------------------------+       |
|                                                                       |
|  STAGE 2: _process() - Derived Parameters                             |
|  +---------------------------+                                        |
|  | Calculate:                |                                        |
|  | - _scaCoe()               |                                        |
|  | - sca_550                 |                                        |
|  | - SAE (Scattering Angstrom|                                        |
|  |        Exponent)          |                                        |
|  +---------------------------+                                        |
|                                                                       |
+-----------------------------------------------------------------------+

         Wavelength Dependence Check

    Scattering (Mm^-1)
       ^
       |     Expected: Blue > Green > Red
       |
       |  B *
       |      \
       |       G *
       |           \
       |            R *
       +----+----+----+-----> Wavelength
           450  550  700
```

---

### Mass Concentration Instruments

#### TEOM

```
+-----------------------------------------------------------------------+
|                         QC Thresholds                                 |
+-----------------------------------------------------------------------+
| MAX_NOISE = 0.01                                                      |
| STATUS_OK = 0         (numeric status code)                           |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
|                            _QC() Pipeline                             |
+-----------------------------------------------------------------------+
|                                                                       |
|  [Pre-process]                                                        |
|  - Calculate Volatile_Fraction = (PM_Total - PM_NV) / PM_Total        |
|       |                                                               |
|       v                                                               |
|  +---------------------------+                                        |
|  | Rule: Status Error        |                                        |
|  +---------------------------+                                        |
|  | Status code != 0          |                                        |
|  +---------------------------+                                        |
|           |                                                           |
|           v                                                           |
|  +---------------------------+    +---------------------------+       |
|  | Rule: High Noise          |    | Rule: Non-positive        |       |
|  +---------------------------+    +---------------------------+       |
|  | noise >= 0.01             |    | PM_NV <= 0 OR             |       |
|  +---------------------------+    | PM_Total <= 0             |       |
|           |                       +---------------------------+       |
|           v                                |                          |
|  +---------------------------+             v                          |
|  | Rule: NV > Total          |    +---------------------------+       |
|  +---------------------------+    | Rule: Invalid Vol Frac    |       |
|  | PM_NV > PM_Total          |    +---------------------------+       |
|  | (physically impossible)   |    | Volatile_Fraction < 0 OR  |       |
|  +---------------------------+    | Volatile_Fraction > 1     |       |
|           |                       +---------------------------+       |
|           v                                                           |
|  +---------------------------+    +---------------------------+       |
|  | Rule: Spike               |    | Rule: Insufficient        |       |
|  +---------------------------+    +---------------------------+       |
|  | Sudden value change       |    | < 50% hourly data         |       |
|  | (vectorized detection)    |    |                           |       |
|  +---------------------------+    +---------------------------+       |
|                                                                       |
+-----------------------------------------------------------------------+
Output: PM_NV, PM_Total, Volatile_Fraction, QC_Flag
```

#### BAM1020

```
+-----------------------------------------------------------------------+
|                         QC Thresholds                                 |
+-----------------------------------------------------------------------+
| MIN_CONC = 0       ug/m3                                              |
| MAX_CONC = 500     ug/m3                                              |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
|                            _QC() Pipeline                             |
+-----------------------------------------------------------------------+
|                                                                       |
|  +---------------------------+    +---------------------------+       |
|  | Rule: Invalid Conc        |    | Rule: Spike               |       |
|  +---------------------------+    +---------------------------+       |
|  | Conc <= 0 OR              |    | Sudden value change       |       |
|  | Conc > 500 ug/m3          |    | (vectorized detection)    |       |
|  +---------------------------+    +---------------------------+       |
|                                                                       |
+-----------------------------------------------------------------------+
Output: Conc, QC_Flag
```

---

### Chemical Composition Instruments

#### OCEC (Organic Carbon/Elemental Carbon)

```
+-----------------------------------------------------------------------+
|                         QC Thresholds                                 |
+-----------------------------------------------------------------------+
| MIN_VALUE = -5     ugC/m3                                             |
| MAX_VALUE = 100    ugC/m3                                             |
+-----------------------------------------------------------------------+
|                         Detection Limits (MDL)                        |
+-----------------------------------------------------------------------+
| Thermal_OC  : 0.3   ugC/m3    |   Thermal_EC  : 0.015 ugC/m3          |
| Optical_OC  : 0.3   ugC/m3    |   Optical_EC  : 0.015 ugC/m3          |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
|                            _QC() Pipeline                             |
+-----------------------------------------------------------------------+
|                                                                       |
|  +---------------------------+    +---------------------------+       |
|  | Rule: Invalid Carbon      |    | Rule: Below MDL           |       |
|  +---------------------------+    +---------------------------+       |
|  | Value <= -5 OR            |    | Values below method       |       |
|  | Value > 100 ugC/m3        |    | detection limit           |       |
|  +---------------------------+    +---------------------------+       |
|           |                                |                          |
|           v                                v                          |
|  +---------------------------+    +---------------------------+       |
|  | Rule: Spike               |    | Rule: Missing OC          |       |
|  +---------------------------+    +---------------------------+       |
|  | Sudden value change       |    | Thermal_OC or Optical_OC  |       |
|  | (vectorized detection)    |    | is missing                |       |
|  +---------------------------+    +---------------------------+       |
|                                                                       |
+-----------------------------------------------------------------------+
Output: Thermal_OC, Thermal_EC, Optical_OC, Optical_EC, TC, OC1-4, PC, QC_Flag
```

#### IGAC (Ion Composition)

```
+-----------------------------------------------------------------------+
|                         Detection Limits (MDL)                        |
+-----------------------------------------------------------------------+
| Na+  : 0.06    NH4+ : 0.05    K+   : 0.05    Mg2+ : 0.12    Ca2+: 0.07|
| Cl-  : 0.07    NO2- : 0.05    NO3- : 0.11    SO42-: 0.08    (ug/m3)   |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
|                            _QC() Pipeline                             |
+-----------------------------------------------------------------------+
|                                                                       |
|  +---------------------------+    +---------------------------+       |
|  | Rule: Mass Closure        |    | Rule: Missing Main        |       |
|  +---------------------------+    +---------------------------+       |
|  | Total ions > PM2.5        |    | NH4+, SO42-, or NO3-      |       |
|  +---------------------------+    | is missing                |       |
|           |                       +---------------------------+       |
|           v                                |                          |
|  +---------------------------+             v                          |
|  | Rule: Below MDL           |    +---------------------------+       |
|  +---------------------------+    | Rule: Ion Balance         |       |
|  | Ion concentration below   |    +---------------------------+       |
|  | detection limit           |    | Cation/Anion ratio        |       |
|  +---------------------------+    | outside valid range       |       |
|                                   +---------------------------+       |
|                                                                       |
+-----------------------------------------------------------------------+

            Ion Balance Diagram

    Cation Equivalent
       ^
       |        /
       |       /  Valid Region (C/A ~ 1)
       |      /
       +-----+-------------------------> Anion Equivalent

Output: Ion columns, QC_Flag
```

---

### Other Data Sources

#### EPA (Environmental Data)

```
+-----------------------------------------------------------------------+
|                            _QC() Pipeline                             |
+-----------------------------------------------------------------------+
|                                                                       |
|  +---------------------------+                                        |
|  | Rule: Negative Value      |                                        |
|  +---------------------------+                                        |
|  | Any measurement value < 0 |                                        |
|  +---------------------------+                                        |
|                                                                       |
+-----------------------------------------------------------------------+
Output: All columns, QC_Flag
```

---

## QC Summary Output Format

QC Summary is output at the end of `_process()` (or `_QC()` for instruments without `_process()`).
Each rule is logged on a separate line:

```
AE33 QC Summary:
  Status Error: 24312 (4.9%)
  Invalid BC: 29265 (5.9%)
  Insufficient: 105481 (21.1%)
  Invalid AAE: 25948 (5.2%)
  Valid: 356025 (71.2%)
```

For instruments with `_process()` method (AE33, AE43, BC1054, MA350, NEPH, Aurora, SMPS, APS):
- `_QC()` stores the summary in `self._qc_summary`
- `_process()` adds any additional validation rules (e.g., Invalid AAE) and outputs the combined summary

For instruments without `_process()` method (OCEC, BAM1020, TEOM, EPA, IGAC):
- QC Summary is output directly in `_QC()`

---

## QC Summary Table

| Instrument | QCFlagBuilder | Rules | Key Checks                                                    |
|------------|---------------|-------|---------------------------------------------------------------|
| AE33       | Yes           | 4     | Status, Invalid BC, Invalid AAE, Insufficient                 |
| AE43       | Yes           | 4     | Status, Invalid BC, Invalid AAE, Insufficient                 |
| BC1054     | Yes           | 4     | Status, Invalid BC, Invalid AAE, Insufficient                 |
| MA350      | Yes           | 4     | Status, Invalid BC, Invalid AAE, Insufficient                 |
| SMPS       | Yes           | 4     | Status, Invalid Number Conc, DMA Water, Insufficient          |
| APS        | Yes           | 3     | Status, Invalid Number Conc, Insufficient                     |
| NEPH       | Yes           | 5     | Status, No Data, Invalid Scat, Invalid Rel, Insufficient      |
| Aurora     | Yes           | 5     | Status, No Data, Invalid Scat, Invalid Rel, Insufficient      |
| TEOM       | Yes           | 7     | Status, High Noise, Non-pos, NV>Total, Vol, Spike, Insufficient |
| BAM1020    | Yes           | 2     | Invalid Conc, Spike                                             |
| OCEC       | Yes           | 4     | Invalid Carbon, Below MDL, Spike, Missing OC                    |
| IGAC       | Yes           | 4     | Mass Closure, Missing Main, Below MDL, Ion Balance            |
| EPA        | Yes           | 1     | Negative                                                      |
| VOC        | No            | 0     | None implemented                                              |
| XRF        | No            | 0     | Not implemented                                               |
| GRIMM      | No            | 0     | None implemented                                              |

---

## QC Migration Status

Instruments migrated to new `QCFlagBuilder` system:

- [x] AE33
- [x] AE43
- [x] BC1054
- [x] MA350
- [x] SMPS
- [x] APS
- [x] NEPH
- [x] Aurora
- [x] TEOM
- [x] BAM1020
- [x] OCEC
- [x] IGAC
- [x] EPA

Instruments not yet using QCFlagBuilder:

- [ ] GRIMM (no QC implemented)
- [ ] VOC (no QC implemented)
- [ ] XRF (not implemented)
- [ ] Minion (complex multi-source QC)

---

## Implementation Status

### Phase 1: QC_Flag Implementation [COMPLETED]

1. ~~Define QC_Flag constants in `AbstractReader`~~ ✓
2. ~~Modify `_QC` methods to return DataFrame with flags~~ ✓
3. ~~Update `__call__` to handle flags~~ ✓

### Phase 2: _process Method [COMPLETED]

1. ~~Add `_process` method in `AbstractReader`~~ ✓
2. Implement in each instrument Reader:
   - ~~Absorption instruments (AE33, AE43, BC1054, MA350)~~ ✓
   - ~~Scattering instruments (NEPH, Aurora)~~ ✓
   - ~~Size distribution (SMPS, APS)~~ ✓
3. ~~Update `_run` flow to call `_process` after QC~~ ✓

### Phase 3: Integration [IN PROGRESS]

1. ~~Integrate `pre_process.py` functions into Readers~~ ✓ (for absorption/scattering)
2. ~~Standardize output format~~ ✓
3. Documentation updates ongoing

---

## Project Structure

```
AeroViz/
|
+-- rawDataReader/
|   +-- __init__.py              # RawDataReader factory
|   +-- config/
|   |   +-- supported_instruments.py
|   +-- core/
|   |   +-- __init__.py          # AbstractReader base class
|   |   +-- qc.py                # QualityControl class
|   |   +-- pre_process.py       # Pre-processing functions
|   |   +-- logger.py            # Logging system
|   |   +-- report.py            # Report generation
|   +-- script/
|       +-- SMPS.py              # Instrument Readers
|       +-- APS.py
|       +-- AE33.py
|       +-- ...
|
+-- dataProcess/
|   +-- __init__.py              # DataProcess factory
|   +-- Chemistry/               # Chemical analysis
|   +-- Optical/                 # Optical properties
|   +-- SizeDistr/               # Size distribution merge
|   +-- VOC/                     # VOC processing
|
+-- plot/                        # Plotting modules
```

---

## Design Decisions (Resolved)

- [x] **QC_Flag definitions**: String-based flags (e.g., "Valid", "Status Error", "Invalid BC")
      stored in QC_Flag column. Multiple flags comma-separated.
- [x] **_process method**: Optional (not abstract). Base implementation returns df unchanged.
      Instruments override as needed.
- [x] **Derived parameters**: Merged into same DataFrame with QC_Flag preserved.
- [x] **Integration strategy**: `_process()` calls pre_process.py functions internally.
      DataProcess module remains for multi-instrument operations.

## Open Questions

- [x] ~~Should SMPS/APS calculate size distribution statistics in `_process()`?~~ Yes, implemented.
- [ ] Integration of vectorized spike detection into more instruments?
