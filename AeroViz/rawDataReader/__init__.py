from datetime import datetime
from pathlib import Path
from typing import Literal

from pandas import Grouper, Timedelta

from AeroViz.rawDataReader.config.supported_instruments import meta
from AeroViz.rawDataReader.script import *

__all__ = ['RawDataReader']


def RawDataReader(instrument: str,
                  path: Path | str,
                  reset: bool | str = False,
                  qc: bool | str = True,
                  start: datetime | str = None,
                  end: datetime | str = None,
                  mean_freq: str = '1h',
                  size_range: tuple[float, float] | None = None,
                  suppress_warnings: bool = False,
                  log_level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR'] = 'INFO',
                  **kwargs):
    """
    Factory function to instantiate the appropriate reader module for a given instrument and
    return the processed data over the specified time range.

    Parameters
    ----------
    instrument : str
        The instrument name for which to read data, must be a valid key in the meta dictionary

    path : Path or str
        The directory where raw data files for the instrument are stored

    reset : bool or str
        Data processing control mode:
        False (default) - Use existing processed data if available
        True - Force reprocess all data from raw files
        'append' - Add new data to existing processed data

    qc : bool or str
        Quality control and rate calculation mode:
        True (default) - Apply QC and calculate overall rates
        False - Skip QC and return raw data only
        str - Calculate rates at specified intervals:
            'W' - Weekly rates
            'MS' - Month start rates
            'QS' - Quarter start rates
            'YS' - Year start rates
            Can add number prefix (e.g., '2MS' for bi-monthly)

    start : datetime
        Start time for filtering the data

    end : datetime
        End time for filtering the data

    mean_freq : str
        Resampling frequency for averaging the data (e.g., '1h' for hourly mean)

    size_range : tuple[float, float], optional
        Size range in nanometers (min_size, max_size) for SMPS/APS data filtering

    suppress_warnings : bool, optional
        Whether to suppress warning messages (default: False)

    log_level : {'DEBUG', 'INFO', 'WARNING', 'ERROR'}
        Logging level (default: 'INFO')

    **kwargs
        Additional arguments to pass to the reader module

    Returns
    -------
    pd.DataFrame
        Processed data with specified QC and time range

    Raises
    ------
    ValueError
        If QC mode or mean_freq format is invalid
    TypeError
        If parameters are of incorrect type
    KeyError
        If instrument name is not found in the supported instruments list
    FileNotFoundError
        If path does not exist or cannot be accessed

    See Also
    --------
    AeroViz.rawDataReader.core.AbstractReader
        A abstract reader class for reading raw data from different instruments

    Examples
    --------
    >>> from AeroViz import RawDataReader
    >>>
    >>> # Using string inputs
    >>> df_ae33 = RawDataReader(
    ...     instrument='AE33',
    ...     path='/path/to/your/data/folder',
    ...     reset=True,
    ...     qc='1MS',
    ...     start='2024-01-01',
    ...     end='2024-06-30',
    ...     mean_freq='1h',
    ... )

    >>> # Using Path and datetime objects
    >>> from pathlib import Path
    >>> from datetime import datetime
    >>>
    >>> df_ae33 = RawDataReader(
    ...     instrument='AE33',
    ...     path=Path('/path/to/your/data/folder'),
    ...     reset=True,
    ...     qc='1MS',
    ...     start=datetime(2024, 1, 1),
    ...     end=datetime(2024, 6, 30),
    ...     mean_freq='1h',
    ... )
    """

    # Dynamically build instrument class map from meta configuration
    # This avoids hardcoding the list and automatically includes new instruments
    import AeroViz.rawDataReader.script as script_module
    instrument_class_map = {}
    for instrument_name in meta.keys():
        if hasattr(script_module, instrument_name):
            instrument_class_map[instrument_name] = getattr(script_module, instrument_name)

    # Check if the instrument name is in the map
    if instrument not in instrument_class_map:
        raise KeyError(f"Instrument name '{instrument}' is not valid. \nMust be one of: {list(instrument_class_map.keys())}")

    # Check if path exists and is a directory
    if not isinstance(path, Path):
        path = Path(path)
    if not path.exists() or not path.is_dir():
        raise FileNotFoundError(f"The specified path '{path}' does not exist or is not a directory.")

    # Validate the QC frequency
    if isinstance(qc, str):
        try:
            Grouper(freq=qc)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid frequency: {qc}. Must be one of: "
                             f"W (week), MS (month start), QS (quarter start), YS (year start)")

    # Convert and verify input times
    if not (start and end):
        raise ValueError("Both start and end times must be provided.")

    # Convert start time if it's a string
    if isinstance(start, str):
        try:
            start = datetime.fromisoformat(start.replace('Z', '+00:00'))
        except ValueError as e:
            raise ValueError(
                f"Invalid start time format. Please use ISO format (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS): {e}")

    # Convert end time if it's a string
    if isinstance(end, str):
        try:
            end = datetime.fromisoformat(end.replace('Z', '+00:00'))
        except ValueError as e:
            raise ValueError(
                f"Invalid end time format. Please use ISO format (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS): {e}")

    if end <= start:
        raise ValueError(f"Invalid time range: start {start} is after end {end}")

    end = end.replace(hour=23, minute=59, second=59) if end.hour == 0 and end.minute == 0 else end

    # Verify that mean_freq format
    try:
        Timedelta(mean_freq)
    except ValueError:
        raise ValueError(
            f"Invalid mean_freq: '{mean_freq}'. It should be a valid frequency string (e.g., '1h', '30min', '1D').")

    # Validate size range
    if size_range is not None:
        SIZE_RANGE_INSTRUMENTS = ['SMPS', 'APS', 'GRIMM']
        if instrument not in SIZE_RANGE_INSTRUMENTS:
            raise ValueError(f"Size range filtering is only supported for {SIZE_RANGE_INSTRUMENTS}")

        min_size, max_size = size_range
        if not isinstance(min_size, (int, float)) or not isinstance(max_size, (int, float)):
            raise ValueError("Size range values must be numeric")
        if min_size >= max_size:
            raise ValueError("Minimum size must be less than maximum size")

        if instrument == 'SMPS':
            if not (1 <= min_size <= 1000) or not (1 <= max_size <= 1000):
                raise ValueError("SMPS size range must be between 1 and 1000 nm")
        elif instrument == 'APS':
            if not (500 <= min_size <= 20000) or not (500 <= max_size <= 20000):
                raise ValueError("APS size range must be between 500 and 20000 nm")

        kwargs.update({'size_range': size_range})

    kwargs.update({
        'suppress_warnings': suppress_warnings,
        'log_level': log_level
    })

    # Instantiate the class and return the instance
    reader_module = instrument_class_map[instrument].Reader(
        path=path,
        reset=reset,
        qc=qc,
        **kwargs
    )
    return reader_module(
        start=start,
        end=end,
        mean_freq=mean_freq,
    )
