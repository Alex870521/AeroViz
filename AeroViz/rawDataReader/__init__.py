from datetime import datetime
from pathlib import Path

from AeroViz.rawDataReader.config.supported_instruments import meta
from AeroViz.rawDataReader.script import *

__all__ = ['RawDataReader']


def RawDataReader(instrument_name: str,
                  path: Path,
                  qc: bool = True,
                  csv_raw: bool = True,
                  reset: bool = False,
                  rate: bool = True,
                  append_data: bool = False,
                  start: datetime | None = None,
                  end: datetime | None = None,
                  mean_freq='1h',
                  csv_out=True,
                  ):
    """
    Factory function to instantiate the appropriate reader module for a given instrument and
    return the processed data over the specified time range.

    Parameters
    ----------
    instrument_name : str
        The name of the instrument for which to read data. Must be a valid key in the `meta` dictionary.
    path : Path
        The directory where raw data files for the instrument are stored.
    qc : bool, optional (default=True)
        If True, apply quality control (QC) to the raw data.
    csv_raw : bool, optional (default=True)
        If True, read raw data from CSV files.
    reset : bool, optional (default=False)
        If True, reset the state and reprocess the data from scratch.
    rate : bool, optional (default=False)
        If True, calculate rates from the data.
    append_data : bool, optional (default=False)
        If True, append new data to the existing dataset instead of overwriting it.
    start : datetime, optional
        Start time for filtering the data. If None, no start time filtering will be applied.
    end : datetime, optional
        End time for filtering the data. If None, no end time filtering will be applied.
    mean_freq : str, optional (default='1h')
        Resampling frequency for averaging the data. Example: '1h' for hourly mean.
    csv_out : bool, optional (default=True)
        If True, output the processed data as a CSV file.

    Return
    ------
    reader_module : Reader
        An instance of the reader module corresponding to the specified instrument, which processes
        the data and returns it in a usable format.

    Raises
    ------
    ValueError
        If the `instrument_name` provided is not a valid key in the `meta` dictionary.

    Example
    -------
    To read and process data for the BC1054 instrument:

    >>> from pathlib import Path
    >>> from datetime import datetime
    >>> data = RawDataReader(instrument_name='BC1054', path=Path('/path/to/data'),
    >>>                      start=datetime(2024, 1, 1), end=datetime(2024, 2, 1))
    """
    # Mapping of instrument names to their respective classes
    instrument_class_map = {
        'NEPH': NEPH,
        'Aurora': Aurora,
        'SMPS': SMPS,
        'GRIMM': GRIMM,
        'APS_3321': APS_3321,
        'AE33': AE33,
        'AE43': AE43,
        'BC1054': BC1054,
        'MA350': MA350,
        'TEOM': TEOM,
        'OCEC': OCEC,
        'IGAC': IGAC,
        'VOC': VOC,
        'Table': Table,
        'EPA_vertical': EPA_vertical,
        'Minion': Minion
        # Add other instruments and their corresponding classes here
    }

    # Check if the instrument name is in the map
    if instrument_name not in meta.keys():
        raise ValueError(f"Instrument name '{instrument_name}' is not valid. \nMust be one of: {list(meta.keys())}")

    # Instantiate the class and return the instance
    reader_module = instrument_class_map[instrument_name].Reader(
        path=path,
        qc=qc,
        csv_raw=csv_raw,
        reset=reset,
        rate=rate,
        append_data=append_data
    )
    return reader_module(
        start=start,
        end=end,
        mean_freq=mean_freq,
        csv_out=csv_out,
    )
