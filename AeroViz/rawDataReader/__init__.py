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
                  mean_freq: str | None = None,
                  size_range: tuple[float, float] | None = None,
                  fill_missing: bool = True,
                  ignored_status_errors: list[str] | None = None,
                  output_dir: Path | str | None = None,
                  output_prefix: str | None = None,
                  save_pkl: bool = True,
                  save_intermediate_csv: bool = True,
                  save_report: bool = True,
                  quiet: bool = False,
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

    start : datetime or str, optional
        Start time for filtering the data. If omitted, starts at the first
        timestamp the files contain.

    end : datetime or str, optional
        End time for filtering the data. If omitted, ends at the last timestamp
        the files contain. Omit both ``start`` and ``end`` to get full coverage;
        check ``df.attrs['coverage_start'/'coverage_end']`` for what was found.

    mean_freq : str, optional
        Resampling frequency for averaging the output (e.g. '1h', '30min', '1D').
        If omitted, the data is returned at its native resolution — no
        resampling. Useful for already-aggregated / second-hand sources
        (e.g. EPA, IGAC, Minion, VOC, BAM1020).

    size_range : tuple[float, float], optional
        Size range in nanometers (min_size, max_size) for SMPS/APS data filtering

    append_stats : bool, default=False
        SMPS/APS only. The reader returns the dN/dlogDp distribution (diameters
        as columns). When True, the derived summary statistics (total / GMD /
        GSD / mode, per weighting and mode) are appended as extra columns of the
        returned frame. The default (False) keeps the return value a clean PSD
        matrix so it can be passed straight to ``psd_stats`` / ``merge_psd`` /
        ``SizeDist``; the statistics are always also written to
        ``{prefix}_stats.csv`` alongside the ``_dNdlogDp`` / ``_dSdlogDp`` /
        ``_dVdlogDp`` distribution files.

    fill_missing : bool, default=True
        Time-grid coverage of the output:
        True - reindex/pad out to the full requested [start, end] range
            (historical behaviour; a short file can become a large mostly-NaN
            frame).
        False - clamp the grid to the data's actual coverage, so the output
            never extends past what the files contain. Use ``df.attrs`` for the
            requested-vs-actual range.

    ignored_status_errors : list[str], optional
        SMPS only. Status-flag tokens that should NOT be treated as Status
        Error during QC, in addition to the normal "OK" value. The
        ``Instrument Errors`` column on TSI SMPS exports is often a
        comma-separated list of tokens (e.g. ``'Low aerosol flow,Neutralizer
        not active'``); a row is accepted when every token is either the OK
        value or in this whitelist. Use for operator-known benign warnings
        — e.g. ``ignored_status_errors=['Low aerosol flow']`` on an
        instrument running at a known-low sample-flow setting.

    output_dir : Path or str, optional
        Directory for all output files (pkl, csv, log, report).
        Default: ``path/{instrument}_outputs/``

    output_prefix : str, optional
        Prefix for output file names (e.g., ``'NZ_smps'`` → ``NZ_smps.csv``).
        Default: ``output_{instrument}``

    save_pkl : bool, default=True
        Whether to save pickle cache files. Existing pickles are still read
        when ``reset=False`` regardless of this setting.

    save_intermediate_csv : bool, default=True
        Whether to save intermediate ``_read_*_qc.csv`` / ``_read_*_raw.csv`` files.

    save_report : bool, default=True
        Whether to save ``report.json``.

    quiet : bool, default=False
        Suppress all console output (progress bar, timeline, log messages).
        Log file is still written.

    log_level : {'DEBUG', 'INFO', 'WARNING', 'ERROR'}
        Logging level for the log file (default: 'INFO')

    **kwargs
        Additional arguments to pass to the reader module

    Returns
    -------
    pd.DataFrame
        Processed data with specified QC and time range.

        Reader metadata is attached to ``df.attrs`` (survives pickling and
        ``resample`` in pandas >= 2):

        - Always: ``instrument``, ``station``, ``source_path``, ``n_files``,
          ``coverage_start`` / ``coverage_end`` (the real file span, ignoring
          NaN padding), ``requested_start`` / ``requested_end``, ``raw_freq``,
          ``aeroviz_version``, ``processed_at``.
        - When ``qc`` is enabled, additionally: ``mean_freq``, ``qc_applied``,
          ``qc_freq``, ``acquisition_rate``, ``yield_rate``, ``total_rate``.

        ``coverage_*`` is ``None`` when no data falls in the requested range.

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

    # Convert and verify input times. Both are optional: omit both to get the
    # files' full coverage, or pass just one side to bound only that end.
    # (string -> datetime conversion is naturally skipped when the value is None)
    if isinstance(start, str):
        try:
            start = datetime.fromisoformat(start.replace('Z', '+00:00'))
        except ValueError as e:
            raise ValueError(
                f"Invalid start time format. Please use ISO format (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS): {e}")

    if isinstance(end, str):
        try:
            end = datetime.fromisoformat(end.replace('Z', '+00:00'))
        except ValueError as e:
            raise ValueError(
                f"Invalid end time format. Please use ISO format (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS): {e}")

    if start is not None and end is not None and end <= start:
        raise ValueError(f"Invalid time range: start {start} is after end {end}")

    # Treat a bare end date (midnight) as end-of-day so the final day is included.
    if end is not None and end.hour == 0 and end.minute == 0:
        end = end.replace(hour=23, minute=59, second=59)

    # Verify the mean_freq format (only when resampling is requested)
    if mean_freq is not None:
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
        'fill_missing': fill_missing,
        'ignored_status_errors': ignored_status_errors,
        'output_dir': output_dir,
        'output_prefix': output_prefix,
        'save_pkl': save_pkl,
        'save_intermediate_csv': save_intermediate_csv,
        'save_report': save_report,
        'quiet': quiet,
        'log_level': log_level,
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
