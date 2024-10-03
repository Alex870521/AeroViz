from datetime import datetime
from pathlib import Path

from pandas import Grouper, Timedelta

from AeroViz.rawDataReader.config.supported_instruments import meta
from AeroViz.rawDataReader.script import *

__all__ = ['RawDataReader']

SUPPORTED_INSTRUMENTS = [
    NEPH, Aurora, SMPS, GRIMM, APS_3321, AE33, AE43, BC1054,
    MA350, TEOM, OCEC, IGAC, VOC, EPA, Minion
]


def RawDataReader(instrument_name: str,
                  path: Path,
                  reset: bool = False,
                  qc: bool | str = True,
                  qc_freq: str | None = None,
                  rate: bool = True,
                  append_data: bool = False,
                  start: datetime = None,
                  end: datetime = None,
                  mean_freq: str = '1h',
                  csv_out: bool = True,
                  ):
    """
    Factory function to instantiate the appropriate reader module for a given instrument and
    return the processed data over the specified time range.

    :param instrument_name: The name of the instrument for which to read data. Must be a valid key in the `meta` dictionary.
    :param path: The directory where raw data files for the instrument are stored.
    :param reset: If True, reset the state and reprocess the data from scratch.
    :param qc: If True, apply quality control (QC) to the raw data.
    :param qc_freq: Frequency at which to perform QC. Must be one of 'W', 'M', 'Q', 'Y' for weekly, monthly, quarterly, or yearly.
    :param rate: If True, calculate rates from the data.
    :param append_data: If True, append new data to the existing dataset instead of overwriting it.
    :param start: Start time for filtering the data. If None, no start time filtering will be applied.
    :param end: End time for filtering the data. If None, no end time filtering will be applied.
    :param mean_freq: Resampling frequency for averaging the data. Example: '1h' for hourly mean.
    :param csv_out: If True, output the processed data as a CSV file.

    :return: An instance of the reader module corresponding to the specified instrument, which processes the data and returns it in a usable format.

    :raises ValueError: If the `instrument_name` provided is not a valid key in the `meta` dictionary.
    :raises ValueError: If the specified path does not exist or is not a directory.
    :raises ValueError: If the QC frequency is invalid.
    :raises ValueError: If start and end times are not both provided or are invalid.
    :raises ValueError: If the mean_freq is not a valid frequency string.

    :Example:

    To read and process data for the BC1054 instrument:

    >>> from pathlib import Path
    >>> from datetime import datetime
    >>>
    >>> data = RawDataReader(
    ...     instrument_name='BC1054',
    ...     path=Path('/path/to/data'),
    ...     start=datetime(2024, 2, 1),
    ...     end=datetime(2024, 7, 31, 23))
    """
    # Mapping of instrument names to their respective classes
    instrument_class_map = {cls.__name__.split('.')[-1]: cls for cls in SUPPORTED_INSTRUMENTS}

    # Check if the instrument name is in the map
    if instrument_name not in meta.keys():
        raise ValueError(f"Instrument name '{instrument_name}' is not valid. \nMust be one of: {list(meta.keys())}")

    # 檢查 path 是否存在且是一個目錄
    if not isinstance(path, Path):
        path = Path(path)
    if not path.exists() or not path.is_dir():
        raise ValueError(f"The specified path '{path}' does not exist or is not a directory.")

    # Validate the QC frequency
    if qc_freq is not None:
        try:
            Grouper(freq=qc_freq)
        except ValueError as e:
            raise ValueError(f"Invalid frequency: {qc_freq}. Error: {str(e)}")
        except TypeError as e:
            raise ValueError(f"Invalid frequency type: {qc_freq}. Frequency should be a string.")

    if start and end:
        if end.hour == 0 and end.minute == 0 and end.second == 0:
            end = end.replace(hour=23)
    else:
        raise ValueError("Both start and end times must be provided.")
    if end <= start:
        raise ValueError(f"Invalid time range: start {start} is after end {end}")

    # 驗證 mean_freq 的格式是否正確
    try:
        Timedelta(mean_freq)
    except ValueError:
        raise ValueError(
            f"Invalid mean_freq: '{mean_freq}'. It should be a valid frequency string (e.g., '1H', '30min', '1D').")

    # Instantiate the class and return the instance
    reader_module = instrument_class_map[instrument_name].Reader(
        path=path,
        reset=reset,
        qc=qc,
        qc_freq=qc_freq,
        rate=rate,
        append_data=append_data
    )
    return reader_module(
        start=start,
        end=end,
        mean_freq=mean_freq,
        csv_out=csv_out,
    )
