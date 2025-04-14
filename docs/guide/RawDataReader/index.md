# RawDataReader Documentation

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Basic Usage](#basic-usage)
- [Examples](#examples)
- [Output Files](#output-files)
- [Supported Instruments](#supported-instruments)
- [API Reference](../../api/RawDataReader.md)

## Overview

RawDataReader is a factory function that instantiates the appropriate reader module for a given instrument and returns
the processed data over a specified time range.

## Installation

```python
from pathlib import Path
from datetime import datetime
from AeroViz import RawDataReader
```

## Basic Usage

Here are several scenarios showcasing different ways to use `RawDataReader`:

```python
data = RawDataReader(
    instrument='AE33',
    path=Path('/path/to/data'),
    start=datetime(2024, 2, 1),
    end=datetime(2024, 8, 31),
    mean_freq='1h'
)
```

## Examples

### Scenario 1: Basic Usage with NEPH Instrument

```python
neph_data = RawDataReader(
    instrument='NEPH',
    path=Path('/path/to/your/data/folder'),
    reset=True,
    start=datetime(2024, 2, 1),
    end=datetime(2024, 4, 30),
    mean_freq='1h'
)
```

**Console Output:**

```pycon
╔════════════════════════════════════════════════════════════════════════════════╗
║     Reading NEPH RAW DATA from 2024-02-01 00:00:00 to 2024-04-30 23:59:59      ║
╚════════════════════════════════════════════════════════════════════════════════╝
▶ Reading NEPH files ━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 file_name.dat
		▶ Scatter Coe. (550 nm)
			├─ Sample Rate    :   100.0%
			├─ Valid  Rate    :   100.0%
			└─ Total  Rate    :   100.0%
```

**Expected Output:**

- Hourly averaged NEPH data for the entire year.
- Will include scattering coefficients and other NEPH-related metrics.

### Scenario 2: AE33 with Quality Control and Rate Calculation

```python
ae33_data = RawDataReader(
    instrument='AE33',
    path=Path('/path/to/your/data/folder'),
    reset=True,
    qc='1MS',  # print qc each month
    start=datetime(2024, 1, 1),
    end=datetime(2024, 8, 31),
    mean_freq='1h',
)
```

**Console Output:**

```pycon
╔════════════════════════════════════════════════════════════════════════════════╗
║     Reading AE33 RAW DATA from 2024-02-01 00:00:00 to 2024-05-31 23:59:59      ║
╚════════════════════════════════════════════════════════════════════════════════╝
▶ Reading AE33 files ━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 AE33_AE33-S07-00599_20240225.dat
	 AE33_AE33-S07-00599_20240704.dat may not be a whole daily data. Make sure the file is correct.  # some warming or 
	 AE33_AE33-S07-00599_20240711.dat may not be a whole daily data. Make sure the file is correct.  # error print
	▶ Processing: 2024-02-01 to 2024-02-29
		▶ BC Mass Conc. (880 nm)
			├─ Sample Rate    :   26.3%
			├─ Valid  Rate    :   99.5%
			└─ Total  Rate    :   26.1%
	▶ Processing: 2024-03-01 to 2024-03-31
		▶ BC Mass Conc. (880 nm)
			├─ Sample Rate    :  100.0%
			├─ Valid  Rate    :  100.0%
			└─ Total  Rate    :  100.0%
	▶ Processing: 2024-04-01 to 2024-04-30
		▶ BC Mass Conc. (880 nm)
			├─ Sample Rate    :  100.0%
			├─ Valid  Rate    :  100.0%
			└─ Total  Rate    :  100.0%
	▶ Processing: 2024-05-01 to 2024-05-31
		▶ BC Mass Conc. (880 nm)
			├─ Sample Rate    :  100.0%
			├─ Valid  Rate    :  100.0%
			└─ Total  Rate    :  100.0%
```

**Expected Output:**

- Hourly AE33 data with quality control applied monthly.
- Includes black carbon concentrations and absorption coefficients.
- Will generate a CSV file with the processed data.

### Scenario 3: SMPS with Specific Time Range

```python
smps_data = RawDataReader(
    instrument='SMPS',
    path=Path('/path/to/your/data/folder'),
    start=datetime(2024, 2, 1),
    end=datetime(2024, 8, 31),
    mean_freq='30min',
    size_range=(11.8, 593.5)  # user input size range
)
```

**Console Output:**

```pycon
╔════════════════════════════════════════════════════════════════════════════════╗
║     Reading SMPS RAW DATA from 2024-02-01 00:00:00 to 2024-08-31 23:59:59      ║
╚════════════════════════════════════════════════════════════════════════════════╝
▶ Reading SMPS files ━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00 240817.txt
	SMPS file: 240816.txt is not match the default size range (11.8, 593.5), it is (11.0, 593.5)  # print the unmatch file
		▶ Bins
			├─ Sample Rate    :    1.7%
			├─ Valid  Rate    :   93.3%
			└─ Total  Rate    :    1.6%

```

**Expected Output:**

- SMPS data for the summer months (June to August).
- 30-minute averaged data points.
- Includes particle size distribution information.

---

## Output Files

After processing, six files will be generated in the `{instrument}_outputs` directory:

1. `_read_{instrument}_raw.csv`: Merged raw data with original time resolution
2. `_read_{instrument}_raw.pkl`: Raw data in pickle format
3. `_read_{instrument}.csv`: Quality controlled data
4. `_read_{instrument}.pkl`: QC data in pickle format
5. `Output_{instrument}`: Final processed data file
6. `{instrument}.log`: Processing log file

---

## Supported Instruments

The AeroViz project currently supports data from the following [instruments](../../guide/instruments/index.md)
