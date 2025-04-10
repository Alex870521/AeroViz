# RawDataReader Documentation

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Basic Usage](#basic-usage)
- [Examples](#examples)
- [Output Files](#output-files)
- [Function Signature](#function-signature)
- [Supported Instruments](#supported-instruments)
- [API Reference](#api-reference)

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

#### Console Output

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

#### Console Output

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

#### Console Output

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

## Function Signature

```python
def RawDataReader(
        instrument: str,
        path: Path | str,
        reset: bool | str = False,
        qc: bool | str = True,
        start: datetime = None,
        end: datetime = None,
        mean_freq: str = '1h',
) -> DataFrame:
```

### Parameters

- `instrument` (str): Name of the instrument (e.g., 'NEPH', 'AE33', 'SMPS')
- `path` (Path | str): Directory path where raw data files are stored
- `reset` (bool | str, default=False):
    - `True`: Force reprocess all data
    - `False`: Use existing processed data if available
    - `'append'`: Add new data to existing processed data
- `qc` (bool | str, default=True):
    - `True`: Apply default quality control
    - `False`: Skip QC
    - `str`: QC frequency (e.g., '1M', '1W')
- `start` (datetime): Start date for processing
- `end` (datetime): End date for processing
- `mean_freq` (str, default='1h'): Frequency for data averaging

### Raises

- ValueError: If instrument is invalid
- ValueError: If path doesn't exist
- ValueError: If QC frequency is invalid
- ValueError: If start/end times are invalid
- ValueError: If mean_freq is invalid

### Returns

- DataFrame: An instance of the reader module corresponding to the specified instrument, which processes the data and
  returns it in a usable format.

---

## Supported Instruments

### The AeroViz project currently supports data from the following instruments:

| Instrument                                             | Time Resolution | File Type   | Display Columns                                       | QAQC method |
|:-------------------------------------------------------|:---------------:|:------------|-------------------------------------------------------|:-----------:|
| NEPH (Nephelometer)                                    |      5min       | .dat        | G                                                     |   default   |
| Aurora (Nephelometer)                                  |      1min       | .csv        | G                                                     |   default   |
| SMPS (Scanning Mobility Particle Sizer)                |      6min       | .txt, .csv  | all                                                   |   default   |
| GRIMM (GRIMM Aerosol Technik)                          |      6min       | .dat        | all                                                   |   default   |
| APS_3321 (Aerodynamic Particle Sizer)                  |      6min       | .txt        | all                                                   |   default   |
| AE33 (Aethalometer Model 33)                           |      1min       | .dat        | BC6                                                   |   default   |
| AE43 (Aethalometer Model 43)                           |      1min       | .dat        | BC6                                                   |   default   |
| BC1054 (Black Carbon Monitor 1054)                     |      1min       | .csv        | BC9                                                   |   default   |
| MA350 (MicroAeth MA350)                                |      1min       | .csv        | BC5                                                   |   default   |
| BAM1020 (Beta Attenuation Mass Monitor)                |       1h        | .csv        | Conc                                                  |   default   |
| TEOM (Continuous Ambient Particulate Monitor)          |      6min       | .csv        | PM_Total, PM_NV                                       |   default   |
| OCEC (Sunset Organic Carbon Elemental Carbon Analyzer) |       1h        | *LCRes.csv  | Thermal_OC, Thermal_EC, Optical_OC, Optical_EC        |   default   |
| IGAC (In-situ Gas and Aerosol Compositions monitor)    |       1h        | .csv        | Na+, NH4+, K+, Mg2+, Ca2+, Cl-, NO2-, NO3-, SO42-     |   default   |
| XRF (X-ray Fluorescence Spectrometer)                  |       1h        | .csv        | Al, Si, P, S, Cl, K, Ca, Ti, V, Cr, Mn, Fe, Ni, Cu... |   default   |
| VOC (Volatile Organic Compounds Monitor)               |       1h        | .csv        | voc                                                   |   default   |
| EPA                                                    |       1h        | .csv        | all                                                   |   default   |
| Minion                                                 |       1h        | .csv, .xlsx | Na+, NH4+, Cl-, NO3-, SO42-, Al, Ti, V, Cr, Mn, Fe    |   default   |

```{note}
Notes:
1. For VOC, due to the numerous display columns, we've simply noted "voc" in the table. In reality, it includes many specific VOC compound names.
2. For instruments marked with "all", it means all available columns or intervals are displayed.
3. The display columns for XRF include a large number of element names, all of which are listed.
4. The file types for AE33 and AE43 actually have more specific patterns, but are simplified to ".dat" in this table.
```

---

## API Reference

### AbstractReader Class

Base class for reading raw data from different instruments.

```python
class AbstractReader(ABC):
  def __init__(self,
               path: Path | str,
               reset: bool | str = False,
               qc: bool | str = True):
    pass
```

#### Abstract Methods

- `_raw_reader(self, file)`: Implement in child classes to read raw data files
- `_QC(self, df: DataFrame) -> DataFrame`: Implement in child classes for quality control

#### Key Methods

- `__call__(self, start: datetime, end: datetime, mean_freq: str = '1h') -> DataFrame`: Process data for specified time
  range

```python
def __call__(self,
             start: datetime,
             end: datetime,
             mean_freq: str = '1h',
             ) -> DataFrame:
```

- `_timeIndex_process(self, _df, user_start=None, user_end=None, append_df=None)`: Process time index and resampling
- `_outlier_process(self, _df)`: Process outliers
- `_save_data(self, raw_data: DataFrame, qc_data: DataFrame) -> None`: Save data to files
- `_read_raw_files(self) -> tuple[DataFrame | None, DataFrame | None]`: Read and process raw files

#### Static Methods

- `reorder_dataframe_columns(df, order_lists, others_col=False)`: Reorder DataFrame columns
- `n_sigma_QC(df: DataFrame, std_range: int = 5) -> DataFrame`: Perform n-sigma quality control
- `IQR_QC(df: DataFrame, log_dist=False) -> tuple[DataFrame, DataFrame]`: Perform IQR quality control