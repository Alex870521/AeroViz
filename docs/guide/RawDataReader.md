# RawDataReader Usage Guide

This guide demonstrates various usage scenarios for the `RawDataReader` function from the AeroViz package. Each scenario
shows different configurations and explains the expected outputs.

## Installation

Before using `RawDataReader`, ensure you have the AeroViz package installed:

```bash
pip install AeroViz
```

## Basic Usage

Here are several scenarios showcasing different ways to use `RawDataReader`:

```python
from pathlib import Path
from datetime import datetime
from AeroViz.rawDataReader import RawDataReader

# Common parameters
data_path = Path('/path/to/your/data')
start_time = datetime(2024, 1, 1)
end_time = datetime(2024, 12, 31, 23, 59, 59)
```

### Scenario 1: Basic Usage with NEPH Instrument

```python
neph_data = RawDataReader(
    instrument_name='NEPH',
    path=data_path / 'NEPH',
    start=start_time,
    end=end_time,
    mean_freq='1h'
)
```

**Expected Output:**

- Hourly averaged NEPH data for the entire year.
- Will include scattering coefficients and other NEPH-related metrics.

### Scenario 2: AE33 with Quality Control and Rate Calculation

```python
ae33_data = RawDataReader(
    instrument_name='AE33',
    path=data_path / 'AE33',
    reset=True,
    qc=True,
    qc_freq='1M',
    rate=True,
    start=start_time,
    end=end_time,
    mean_freq='1h',
    csv_out=True
)
```

**Expected Output:**

- Hourly AE33 data with quality control applied monthly.
- Includes black carbon concentrations and absorption coefficients.
- Will generate a CSV file with the processed data.

### Scenario 3: SMPS with Specific Time Range

```python
smps_data = RawDataReader(
    instrument_name='SMPS',
    path=data_path / 'SMPS',
    start=datetime(2024, 6, 1),
    end=datetime(2024, 8, 31, 23, 59, 59),
    mean_freq='30min',
    csv_out=False
)
```

**Expected Output:**

- SMPS data for the summer months (June to August).
- 30-minute averaged data points.
- Includes particle size distribution information.
- No CSV file will be generated.

### Scenario 4: Minion with Appending New Data

```python
minion_data = RawDataReader(
    instrument_name='Minion',
    path=data_path / 'Minion',
    reset=False,
    append_data=True,
    start=start_time,
    end=end_time,
    mean_freq='1d'
)
```

**Expected Output:**

- Daily averaged Minion data for the entire year.
- New data will be appended to the existing dataset.

## Console Output

For each scenario, you may see console output similar to this:

```
Reading [Instrument] RAW DATA from [Start Date] to [End Date]
Reading [Instrument] files ━━━━━━━━━━━━━━━━━━ 100% [Time]
    Acquisition rate : [Percentage]%
    Yield rate       : [Percentage]%
```

## Data Sample

To view a sample of the processed data, you can use:

```python
print(data.head())
```

This will display the first few rows of the processed data, including timestamps and instrument-specific measurements.

## Parameter Explanation

- `instrument_name`: Name of the instrument (e.g., 'NEPH', 'AE33', 'SMPS', 'Minion')
- `path`: Directory path where raw data files are stored
- `reset`: If True, reprocess data from scratch
- `qc`: If True, apply quality control
- `qc_freq`: Frequency of quality control ('1M' for monthly, '1W' for weekly, etc.)
- `rate`: If True, calculate rates from the data
- `append_data`: If True, append new data to existing dataset
- `start` and `end`: Date range for data processing
- `mean_freq`: Frequency for data averaging ('1h' for hourly, '30min' for half-hourly, etc.)
- `csv_out`: If True, output processed data as CSV

# Supported Instruments: Default Time Resolutions and File Types
### The AeroViz project currently supports data from the following instruments:

|                       Instrument                       | Time Resolution | File Type   | Display Columns                                       | QAQC method |
|:------------------------------------------------------:|:---------------:|:------------|-------------------------------------------------------|:-----------:|
|                  NEPH (Nephelometer)                   |      5min       | .dat        | G                                                     |   default   |
|                 Aurora (Nephelometer)                  |      1min       | .csv        | G                                                     |   default   |
|        SMPS (Scanning Mobility Particle Sizer)         |      6min       | .txt, .csv  | all                                                   |   default   |
|             GRIMM (GRIMM Aerosol Technik)              |      6min       | .dat        | all                                                   |   default   |
|         APS_3321 (Aerodynamic Particle Sizer)          |      6min       | .txt        | all                                                   |   default   |
|              AE33 (Aethalometer Model 33)              |      1min       | .dat        | BC6                                                   |   default   |
|              AE43 (Aethalometer Model 43)              |      1min       | .dat        | BC6                                                   |   default   |
|           BC1054 (Black Carbon Monitor 1054)           |      1min       | .csv        | BC9                                                   |   default   |
|                MA350 (MicroAeth MA350)                 |      1min       | .csv        | BC5                                                   |   default   |
|     TEOM (Continuous Ambient Particulate Monitor)      |      6min       | .csv        | PM_Total, PM_NV                                       |   default   |
| OCEC (Sunset Organic Carbon Elemental Carbon Analyzer) |       1h        | *LCRes.csv  | Thermal_OC, Thermal_EC, Optical_OC, Optical_EC        |   default   |
|  IGAC (In-situ Gas and Aerosol Compositions monitor)   |       1h        | .csv        | Na+, NH4+, K+, Mg2+, Ca2+, Cl-, NO2-, NO3-, SO42-     |   default   |
|         XRF (X-ray Fluorescence Spectrometer)          |       1h        | .csv        | Al, Si, P, S, Cl, K, Ca, Ti, V, Cr, Mn, Fe, Ni, Cu... |   default   |
|        VOC (Volatile Organic Compounds Monitor)        |       1h        | .csv        | voc                                                   |   default   |
|                          EPA                           |       1h        | .csv        | all                                                   |   default   |
|                         Minion                         |       1h        | .csv, .xlsx | Na+, NH4+, Cl-, NO3-, SO42-, Al, Ti, V, Cr, Mn, Fe    |   default   |

```{note}
Notes:
1. For VOC, due to the numerous display columns, we've simply noted "voc" in the table. In reality, it includes many specific VOC compound names.
2. For instruments marked with "all", it means all available columns or intervals are displayed.
3. The display columns for XRF include a large number of element names, all of which are listed.
4. The file types for AE33 and AE43 actually have more specific patterns, but are simplified to ".dat" in this table.
```
