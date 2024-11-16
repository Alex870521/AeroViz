# RawDataReader API Reference

## RawDataReader Function

### Overview

`RawDataReader` is a factory function that instantiates the appropriate reader module for a given instrument and returns
the processed data over a specified time range.

### Function Signature

```python
def RawDataReader(
    instrument_name: str,
    path: Path | str,
    reset: bool = False,
    qc: bool | str = True,
    qc_freq: str | None = None,
    rate: bool = True,
    append_data: bool = False,
    start: datetime = None,
    end: datetime = None,
    mean_freq: str = '1h',
    csv_out: bool = True,
) -> DataFrame:
```

### Parameters

- `instrument_name` (str): The name of the instrument for which to read data. Must be a valid key in the `meta`
  dictionary.
- `path` (Path | str): The directory where raw data files for the instrument are stored.
- `reset` (bool, optional): If True, reset the state and reprocess the data from scratch. Default is False.
- `qc` (bool | str, optional): If True, apply quality control (QC) to the raw data. Default is True.
- `qc_freq` (str | None, optional): Frequency at which to perform QC. Must be one of 'W', 'M', 'Q', 'Y' for weekly,
  monthly, quarterly, or yearly. Default is None.
- `rate` (bool, optional): If True, calculate rates from the data. Default is True.
- `append_data` (bool, optional): If True, append new data to the existing dataset instead of overwriting it. Default is
  False.
- `start` (datetime, optional): Start time for filtering the data. If None, no start time filtering will be applied.
- `end` (datetime, optional): End time for filtering the data. If None, no end time filtering will be applied.
- `mean_freq` (str, optional): Resampling frequency for averaging the data. Example: '1h' for hourly mean. Default is '
  1h'.
- `csv_out` (bool, optional): If True, output the processed data as a CSV file. Default is True.

### Returns

- DataFrame: An instance of the reader module corresponding to the specified instrument, which processes the data and
  returns it in a usable format.

### Raises

- ValueError: If the `instrument_name` provided is not a valid key in the `meta` dictionary.
- ValueError: If the specified path does not exist or is not a directory.
- ValueError: If the QC frequency is invalid.
- ValueError: If start and end times are not both provided or are invalid.
- ValueError: If the mean_freq is not a valid frequency string.

### Example

```python
from pathlib import Path
from datetime import datetime
from AeroViz import RawDataReader

data = RawDataReader(
    instrument_name='AE33',
    path=Path('/path/to/data'),
    start=datetime(2024, 2, 1),
    end=datetime(2024, 8, 31, 23)
)
```

[]()

## AbstractReader Class

### Overview

`AbstractReader` is an abstract base class for reading raw data from different instruments. Each instrument should have
a separate class that inherits from this class and implements the abstract methods.

### Class Definition

```python
class AbstractReader(ABC):
```

### Constructor

```python
def __init__(self,
             path: Path | str,
             reset: bool = False,
             qc: bool = True,
             qc_freq: Optional[str] = None,
             rate: bool = True,
             append_data: bool = False):
```

#### Parameters

- `path` (Path | str): The directory path where raw data files are stored.
- `reset` (bool, optional): If True, reprocess the data from scratch. Default is False.
- `qc` (bool, optional): If True, apply quality control to the data. Default is True.
- `qc_freq` (str, optional): Frequency at which to perform QC. Default is None.
- `rate` (bool, optional): If True, calculate rates from the data. Default is True.
- `append_data` (bool, optional): If True, append new data to existing dataset. Default is False.

### Abstract Methods

#### _raw_reader

```python
@abstractmethod
def _raw_reader(self, file):
    pass
```

This method should be implemented in child classes to read raw data files.

#### _QC

```python
@abstractmethod
def _QC(self, df: DataFrame) -> DataFrame:
    return df
```

This method should be implemented in child classes to perform quality control on the data.

### Key Methods

#### __call__

```python
def __call__(self,
             start: datetime,
             end: datetime,
             mean_freq: str = '1h',
             csv_out: bool = True,
             ) -> DataFrame:
```

This method processes the data for the specified time range and returns the result.

#### _timeIndex_process

```python
def _timeIndex_process(self, _df, user_start=None, user_end=None, append_df=None):
```

Processes time index, resamples data, extracts specified time range, and optionally appends new data.

#### _outlier_process

```python
def _outlier_process(self, _df):
```

Processes outliers based on a JSON file containing outlier information.

#### _save_data

```python
def _save_data(self, raw_data: DataFrame, qc_data: DataFrame) -> None:
```

Saves raw and quality-controlled data to pickle and CSV files.

#### _read_raw_files

```python
def _read_raw_files(self) -> tuple[DataFrame | None, DataFrame | None]:
```

Reads raw data files and performs initial processing and quality control.

### Static Methods

#### reorder_dataframe_columns

```python
@staticmethod
def reorder_dataframe_columns(df, order_lists, others_col=False):
```

Reorders DataFrame columns based on specified order lists.

#### n_sigma_QC

```python
@staticmethod
def n_sigma_QC(df: DataFrame, std_range: int = 5) -> DataFrame:
```

Performs n-sigma quality control on the data.

#### IQR_QC

```python
@staticmethod
def IQR_QC(df: DataFrame, log_dist=False) -> tuple[DataFrame, DataFrame]:
```

Performs Inter-quartile Range (IQR) quality control on the data.