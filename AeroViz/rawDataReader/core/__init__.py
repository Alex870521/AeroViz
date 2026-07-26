import json
from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator

import numpy as np
import pandas as pd
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TaskProgressColumn

from AeroViz.rawDataReader.config.supported_instruments import meta
from AeroViz.rawDataReader.core.logger import ReaderLogger
from AeroViz.rawDataReader.core.metadata import aeroviz_version, data_coverage, stamp_attrs
from AeroViz.rawDataReader.core.qc import (QualityControl, QCRule, QCFlagBuilder,
                                          ERROR, WARNING, SEVERITIES)
from AeroViz.rawDataReader.core.time_grid import detect_freq, resolve_freq, detect_isolated_dates, to_grid
from AeroViz.rawDataReader.core.report import calculate_rates, process_rates_report, process_timeline_report, print_timeline_visual

__all__ = ['AbstractReader', 'QCRule', 'QCFlagBuilder', 'ERROR', 'WARNING']

#: Short aliases for the two QC bookkeeping columns (see `QCFlagBuilder`).
FLAG_COLUMN = QCFlagBuilder.FLAG_COLUMN
INVALID_COLUMN = QCFlagBuilder.INVALID_COLUMN


# Bumped when the cached pkl layout/semantics change. v2 = canonical frames
# (snapped to native grid over the files' own coverage, NOT padded to a
# requested range) carrying parse provenance in df.attrs. Pre-v2 pkls (padded,
# no marker) are treated as stale and re-parsed.
# Bumped to 3 when QC gained flag severity: the cached QC frame now carries a
# `QC_Invalid` verdict column alongside `QC_Flag`. A version-2 pickle has no
# verdict, so it is re-parsed rather than silently treated as all-invalidating.
CACHE_FORMAT = 3


class AbstractReader(ABC):
    """
    Abstract class for reading raw data from different instruments.

    This class serves as a base class for reading raw data from various instruments. Each instrument
    should have a separate class that inherits from this class and implements the abstract methods.
    The abstract methods are `_raw_reader` and `_QC`.

    The class handles file management, including reading from and writing to pickle files, and
    implements quality control measures. It can process data in both batch and streaming modes.

    Attributes
    ----------
    nam : str
        Name identifier for the reader class
    path : Path
        Path to the raw data files
    meta : dict
        Metadata configuration for the instrument
    logger : ReaderLogger
        Custom logger instance for the reader
    reset : bool
        Flag to indicate whether to reset existing processed data
    append : bool
        Flag to indicate whether to append new data to existing processed data
    qc : bool or str
        Quality control settings
    qc_freq : str or None
        Frequency for quality control calculations
    """

    nam = 'AbstractReader'

    #: Summary table stashed by `_QC` for readers whose `_process` adds a
    #: further rule (see `extend_qc_summary`). None when `_QC` logged it itself.
    _qc_summary = None

    def __init__(self,
                 path: Path | str,
                 reset: bool | str = False,
                 qc: bool | str = True,
                 **kwargs):
        """
        Initialize the AbstractReader.

        Parameters
        ----------
        path : Path or str
            Path to the directory containing raw data files
        reset : bool or str, default=False
            If True, forces re-reading of raw data
            If 'append', appends new data to existing processed data
        qc : bool or str, default=True
            If True, performs quality control
            If str, specifies the frequency for QC calculations
        **kwargs : dict
            Additional keyword arguments:
                raw_freq : str
                    Override raw data frequency (e.g., '6min', '1h').
                    If not set, frequency is auto-inferred from the data.
                drop_outlier_dates : bool, default=False
                    Stray timestamps far outside the data's bulk (e.g. a
                    year-2000 row in 2023 data) are always detected and warned
                    about, since they balloon the native grid. By default they
                    are kept (the warning explains how to fix the source); set
                    True to drop them automatically before the grid is built.
                log_level : str
                    Logging level for the log file
                quiet : bool
                    If True, suppresses all console output

        Notes
        -----
        Creates necessary output directories and initializes logging system.
        Sets up paths for pickle files, CSV files, and report outputs.
        """
        self.path = Path(path)
        self.meta = meta[self.nam]

        # Output directory (customisable, default preserves original behaviour)
        _output_dir = kwargs.get('output_dir')
        if _output_dir is not None:
            output_folder = Path(_output_dir)
        else:
            output_folder = self.path / f'{self.nam.lower()}_outputs'
        output_folder.mkdir(parents=True, exist_ok=True)
        self._output_folder = output_folder

        self.quiet = kwargs.get('quiet', False)
        self.logger = ReaderLogger(
            self.nam, output_folder,
            kwargs.get('log_level', 'INFO').upper(),
            quiet=self.quiet)

        self.reset = reset is True
        self.append = reset == 'append'
        self.qc = qc  # if qc, then calculate rate
        self.qc_freq = qc if isinstance(qc, str) else None
        self.raw_freq = kwargs.get('raw_freq', None)
        self.fill_missing = kwargs.get('fill_missing', True)
        self.kwargs = kwargs

        # Per-run reclassification of QC rules, e.g.
        # flag_severity={'Insufficient': 'warning'} to keep sparse-hour readings.
        self.qc_severity_overrides = dict(kwargs.get('flag_severity') or {})

        # Metadata collected during a run, stamped onto df.attrs before return
        self._n_files = None          # number of raw files read this run
        self._resolved_freq = None    # native frequency resolved from the files
        self._freq_mixed = False      # True if files had differing resolutions
        self.overall_rates = None     # overall acquisition/yield/total rates dict

        # Rate/timeline report accumulated by `_generate_report`. Defaulted here
        # so a reader whose `_QC` produces no `QC_Flag` degrades to a
        # rate-less report instead of raising AttributeError in `__call__`.
        self.report_dict = {}

        # Selective output control
        self.save_pkl = kwargs.get('save_pkl', True)
        self.save_intermediate_csv = kwargs.get('save_intermediate_csv', True)
        self.save_report = kwargs.get('save_report', True)

        # Output prefix (customisable)
        self._output_prefix = kwargs.get('output_prefix') or f'output_{self.nam.lower()}'

        # Cache file paths
        self.pkl_nam = output_folder / f'_read_{self.nam.lower()}_qc.pkl'
        self.csv_nam = output_folder / f'_read_{self.nam.lower()}_qc.csv'
        self.pkl_nam_raw = output_folder / f'_read_{self.nam.lower()}_raw.pkl'
        self.csv_nam_raw = output_folder / f'_read_{self.nam.lower()}_raw.csv'

        # Final output file paths (use custom prefix)
        self.csv_out = output_folder / f'{self._output_prefix}.csv'
        self.report_out = output_folder / 'report.json'

    def __call__(self,
                 start: datetime = None,
                 end: datetime = None,
                 mean_freq: str = None,
                 ) -> pd.DataFrame:
        """
        Process data for a specified time range.

        Parameters
        ----------
        start : datetime, optional
            Start time for data processing; defaults to the data's first timestamp
        end : datetime, optional
            End time for data processing; defaults to the data's last timestamp
        mean_freq : str, optional
            Frequency for resampling the output; if None, no resampling is done
            and the data is returned at its native resolution

        Returns
        -------
        pd.DataFrame
            Processed and resampled data for the specified time range

        Notes
        -----
        The processed data is also saved to a CSV file.
        """

        _f_raw, _f_qc = self._run(start, end)

        if not self.qc:
            # The raw branch honours `mean_freq` too. It used to ignore it
            # silently, so `qc=False, mean_freq='1h'` returned native-resolution
            # data that looked hourly-averaged.
            _f_raw = self._resample(_f_raw, mean_freq)
            return self._stamp(_f_raw, start, end, mean_freq=mean_freq, with_qc=False)

        # Keep the flag record for the report before it is dropped.
        qc_flag = _f_qc[FLAG_COLUMN].copy() if FLAG_COLUMN in _f_qc else None

        # Apply the verdict. `QC_Invalid` is what decides masking, NOT the mere
        # presence of a flag: an advisory flag (below a detection limit, an
        # upscale warning) is recorded without deleting the measurement. Frames
        # from a reader that predates severity — or a hand-built one — have no
        # verdict column, so fall back to "any flag invalidates".
        meta_columns = [c for c in (FLAG_COLUMN, INVALID_COLUMN) if c in _f_qc]
        if meta_columns:
            if INVALID_COLUMN in _f_qc:
                invalid_mask = _f_qc[INVALID_COLUMN].fillna(False).astype(bool)
            else:
                invalid_mask = _f_qc[FLAG_COLUMN] != 'Valid'

            if invalid_mask.any():
                data_columns = [col for col in _f_qc.columns if col not in meta_columns]
                _f_qc.loc[invalid_mask, data_columns] = np.nan

            # Neither column belongs in the public output.
            _f_qc.drop(columns=meta_columns, inplace=True)
            valid_mask = ~invalid_mask
        else:
            valid_mask = None

        # Generate data acquisition and quality rate report (instrument time
        # resolution). Yield counts rows that survived the verdict, so a row kept
        # under an advisory flag counts as data obtained.
        self._generate_report(_f_raw.apply(pd.to_numeric, errors='coerce'),
                              _f_qc.apply(pd.to_numeric, errors='coerce'),
                              qc_flag=valid_mask if valid_mask is not None else qc_flag)

        # Resample only when a frequency is requested; otherwise return the
        # data at its native resolution (e.g. already-aggregated sources).
        _f_qc = self._resample(_f_qc, mean_freq)

        _f_qc.to_csv(self.csv_out)

        # Generate timeline data (hourly values)
        report_dict = process_timeline_report(self.report_dict, _f_qc, show_visual=not self.quiet)

        # Write report
        if self.save_report:
            with open(self.report_out, 'w') as f:
                json.dump(report_dict, f, indent=4)

        return self._stamp(_f_qc, start, end, mean_freq=mean_freq, with_qc=True)

    def _resample(self, df: pd.DataFrame, mean_freq: str | None) -> pd.DataFrame:
        """Average ``df`` onto ``mean_freq``; a no-op when none was requested.

        ``mean()`` silently drops non-numeric columns, which is how text metadata
        (a status string, an instrument ID) vanishes between the native-resolution
        and resampled outputs. That is the right behaviour — there is no sensible
        mean of a status string — but it should not be silent, so the dropped
        columns are named in the log once.
        """
        if mean_freq is None or df.empty:
            return df

        numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        dropped = [c for c in df.columns if c not in numeric]

        if dropped:
            shown = ', '.join(str(c) for c in dropped[:8])
            if len(dropped) > 8:
                shown += f', ... (+{len(dropped) - 8} more)'
            self.logger.info(
                f"Resampling to {mean_freq}: dropping {len(dropped)} non-numeric "
                f"column(s) with no meaningful average ({shown}). Omit mean_freq "
                f"to keep them at native resolution.")

        # Select explicitly rather than relying on `mean()` to skip them: with an
        # object column present it raises instead of dropping.
        return df[numeric].resample(mean_freq).mean().__round__(4)

    def _stamp(self, df: pd.DataFrame, start, end, *, mean_freq=None, with_qc=False) -> pd.DataFrame:
        """Attach reader metadata to ``df.attrs`` just before returning.

        Always records provenance (instrument, station, coverage, requested
        range, native frequency). When ``with_qc`` is True it additionally
        records the output frequency and the overall QC rates; the plain raw
        path (``qc=False``) gets provenance only.

        See ``core.metadata`` for why this is the single, final stamping point.
        """
        cov_start, cov_end = data_coverage(df)
        meta = dict(
            instrument=self.nam,
            station=self.path.name[:2],
            source_path=str(self.path),
            n_files=self._n_files,
            coverage_start=cov_start,
            coverage_end=cov_end,
            requested_start=pd.Timestamp(start) if start is not None else None,
            requested_end=pd.Timestamp(end) if end is not None else None,
            raw_freq=self._resolved_freq or self.meta.get('freq'),
            freq_mixed=self._freq_mixed,
            fill_missing=self.fill_missing,
            # Recorded on both branches: the raw path resamples too, so the
            # attrs must say what grid the frame is actually on.
            mean_freq=mean_freq,
            aeroviz_version=aeroviz_version(),
            processed_at=datetime.now().isoformat(timespec='seconds'),
        )
        if with_qc:
            meta.update(
                qc_applied=True,
                qc_freq=self.qc_freq,
                **(self.overall_rates or {}),
            )
        # Drop the internal cache marker carried over from the canonical frame.
        df.attrs.pop('cache_format', None)
        return stamp_attrs(df, **meta)

    @abstractmethod
    def _raw_reader(self, file):
        """
        Abstract method to read raw data files.

        Parameters
        ----------
        file : Path or str
            Path to the raw data file

        Returns
        -------
        pd.DataFrame
            Raw data read from the file

        Notes
        -----
        Must be implemented by child classes to handle specific file formats.
        """
        pass

    @abstractmethod
    def _QC(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Abstract method for quality control processing.

        Parameters
        ----------
        df : pd.DataFrame
            Input DataFrame containing raw data

        Returns
        -------
        pd.DataFrame
            Quality controlled data with QC_Flag column

        Notes
        -----
        Must be implemented by child classes to handle instrument-specific QC.
        This method should only check raw data quality (status, range, completeness).
        Derived parameter validation should be done in _process().
        """
        return df

    def _process(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process data to calculate derived parameters.

        This method is called after _QC() to calculate instrument-specific
        derived parameters (e.g., absorption coefficients, AAE, SAE).

        Parameters
        ----------
        df : pd.DataFrame
            Quality-controlled DataFrame with QC_Flag column

        Returns
        -------
        pd.DataFrame
            DataFrame with derived parameters added and QC_Flag updated

        Notes
        -----
        Default implementation returns the input unchanged.
        Override in child classes to implement instrument-specific processing.

        The method should:
        1. Skip calculation for rows where QC_Flag != 'Valid' (optional optimization)
        2. Calculate derived parameters
        3. Validate derived parameters and update QC_Flag if invalid
        """
        return df

    def _generate_report(self, raw_data, qc_data, qc_flag=None) -> None:
        """
        Calculate and log data quality rates for different time periods.

        Parameters
        ----------
        raw_data : pd.DataFrame
            Raw data before quality control
        qc_data : pd.DataFrame
            Data after quality control
        qc_flag : pd.Series, optional
            QC flag series indicating validity of each row

        Notes
        -----
        Calculates rates for specified QC frequency if set.
        Updates the quality report with calculated rates.
        """
        if qc_flag is not None:
            # Add blank line before rate section
            self.logger.info("")

            if self.qc_freq is not None:
                raw_data_grouped = raw_data.groupby(pd.Grouper(freq=self.qc_freq))
                qc_flag_grouped = qc_flag.groupby(pd.Grouper(freq=self.qc_freq))

                for (month, _sub_raw_data), (_, _sub_qc_flag) in zip(raw_data_grouped, qc_flag_grouped):
                    self.logger.info(
                        f"{self.logger.BLUE}Period: {_sub_raw_data.index[0].strftime('%Y-%m-%d')} ~ "
                        f"{_sub_raw_data.index[-1].strftime('%Y-%m-%d')}{self.logger.RESET}")

                    calculate_rates(self.logger, _sub_raw_data, _sub_qc_flag, with_log=True)

                # Overall rates across the whole period (for df.attrs); not re-logged
                self.overall_rates = calculate_rates(self.logger, raw_data, qc_flag, with_log=False)
            else:
                self.overall_rates = calculate_rates(self.logger, raw_data, qc_flag, with_log=True)

            # 使用 Grouper 對數據按週和月進行分組
            current_time = datetime.now()

            # 按週分組 (使用星期一作為每週的開始)
            weekly_raw_groups = raw_data.groupby(pd.Grouper(freq='W-MON', label="left", closed="left"))
            weekly_flag_groups = qc_flag.groupby(pd.Grouper(freq='W-MON', label="left", closed="left"))

            # 按月分組 (使用月初作為每月的開始)
            monthly_raw_groups = raw_data.groupby(pd.Grouper(freq='MS'))
            monthly_flag_groups = qc_flag.groupby(pd.Grouper(freq='MS'))

            # 報告基本資訊
            report_dict = {
                'startDate': qc_data.index.min().strftime('%Y/%m/%d %H:%M'),
                'endDate': qc_data.index.max().strftime('%Y/%m/%d %H:%M'),
                "report_time": current_time.strftime('%Y-%m-%d %H:%M:%S'),
                "instrument_id": f"{self.path.name[:2]}_{self.nam}",
                "instrument": self.nam,
            }

            # 生成報告資料
            self.report_dict = process_rates_report(
                self.logger, report_dict,
                weekly_raw_groups, monthly_raw_groups,
                weekly_flag_groups, monthly_flag_groups
            )

    def _partition_compatible_scans(self, df_list: list, files: list) -> list:
        """Drop frames whose scan schema differs from the dominant group.

        Default is a no-op — overridden by readers (currently SMPS) where the
        same instrument can export at *different* size-bin grids depending on
        the host software version (AIM 10.3 .TXT vs AIM 11.x .CSV). The outer
        join inside ``pd.concat`` happily concatenates frames with disjoint
        columns, but the NaN holes break per-bin completeness QC. The
        well-defined repair is to treat each grid as its own scan: keep the
        majority group, drop the minority and tell the user which files were
        skipped so they can re-run them in isolation if they want both.

        ``df_list`` and ``files`` are aligned and contain only successfully
        parsed entries.
        """
        return df_list

    def _flag_outlier_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect and warn about stray timestamps; drop them only if asked.

        A single bad row — e.g. a ``2000-01-01`` stamp in otherwise-2023 data —
        stretches the canonical native grid (built over the data's own min->max
        in ``_read_raw_files``, *before* any requested range applies) across the
        whole bogus span, inflating the cached frame to millions of NaN rows
        even when the caller only asked for 2023. Such stamps are almost always
        a source-data error, so by default we *warn and tell the user how to fix
        it* rather than silently changing their data; pass
        ``drop_outlier_dates=True`` to have them excluded automatically.
        """
        if df.empty:
            return df

        mask = detect_isolated_dates(df.index)
        if not mask.any():
            return df

        strays = pd.DatetimeIndex(df.index[mask])
        kept = pd.DatetimeIndex(df.index[~mask])
        shown = ', '.join(s.isoformat() for s in strays[:5])
        if len(strays) > 5:
            shown += f', ... (+{len(strays) - 5} more)'

        self.logger.warning(
            f"Detected {len(strays)} isolated timestamp(s) far outside the data "
            f"bulk ({kept.min()} ~ {kept.max()}): {shown}.")

        if self.kwargs.get('drop_outlier_dates', False):
            self.logger.warning(
                "Excluding them from the grid (drop_outlier_dates=True).")
            return df.loc[~mask]

        self.logger.warning(
            f"These are almost certainly bad timestamps in the source files. "
            f"Left as-is, the native grid will span {df.index.min()} ~ "
            f"{df.index.max()} (mostly NaN), bloating the output and cache. "
            f"Fix the timestamp(s) in the raw file, or pass drop_outlier_dates=True "
            f"to drop them automatically.")
        return df

    def _timeIndex_process(self, _df, user_start=None, user_end=None, append_df=None):
        """
        Process time index of the DataFrame.

        Parameters
        ----------
        _df : pd.DataFrame
            Input DataFrame to process
        user_start : datetime, optional
            User-specified start time
        user_end : datetime, optional
            User-specified end time
        append_df : pd.DataFrame, optional
            DataFrame to append to

        Returns
        -------
        pd.DataFrame
            DataFrame with processed time index

        Notes
        -----
        Frequency is resolved once per run in ``_read_raw_files`` (per-file
        detection, see ``self._resolved_freq``); this method only places the
        data on that grid via ``to_grid`` — snapping off-grid timestamps to
        their nearest bin without the duplicate-fill of ``method='nearest'``.
        """
        # Ensure index is DatetimeIndex
        if not isinstance(_df.index, pd.DatetimeIndex):
            _df.index = pd.to_datetime(_df.index, errors='coerce')
            # Filter out rows with invalid timestamps (NaT)
            _df = _df.loc[_df.index.notna()]

        freq = self._resolved_freq or self.meta['freq']

        # Append new data if provided
        if append_df is not None:
            _df = pd.concat([append_df.dropna(how='all'), _df.dropna(how='all')])
            _df = _df.loc[~_df.index.duplicated()]

        # Log how many timestamps were off the grid (now snapped, not dropped)
        n_off_grid = int((_df.index != _df.index.round(freq)).sum())
        if n_off_grid:
            self.logger.debug(f"Snapped {n_off_grid} off-grid timestamps to the {freq} grid.")

        return to_grid(_df, freq, start=user_start, end=user_end,
                       fill_missing=self.fill_missing, logger=self.logger)

    def _outlier_process(self, _df):
        """
        Process outliers in the data.

        Parameters
        ----------
        _df : pd.DataFrame
            Input DataFrame containing potential outliers

        Returns
        -------
        pd.DataFrame
            DataFrame with outliers processed

        Notes
        -----
        Implementation depends on specific instrument requirements.
        """
        outlier_file = self.path / 'outlier.json'

        if not outlier_file.exists():
            return _df

        with outlier_file.open('r', encoding='utf-8', errors='ignore') as f:
            outliers = json.load(f)

        for _st, _ed in outliers.values():
            _df.loc[_st:_ed] = np.nan

        return _df

    def _save_data(self, raw_data: pd.DataFrame, qc_data: pd.DataFrame) -> None:
        """
        Save processed data to files.

        Parameters
        ----------
        raw_data : pd.DataFrame
            Raw data to save
        qc_data : pd.DataFrame
            Quality controlled data to save

        Notes
        -----
        Saves data in both pickle and CSV formats.
        """
        try:
            if self.save_pkl:
                raw_data.to_pickle(self.pkl_nam_raw)
                qc_data.to_pickle(self.pkl_nam)
            if self.save_intermediate_csv:
                raw_data.to_csv(self.csv_nam_raw)
                qc_data.to_csv(self.csv_nam)

        except Exception as e:
            raise IOError(f"Error saving data. {e}")

    @contextmanager
    def progress_reading(self, files: list) -> Generator:
        """
        Context manager for tracking file reading progress.

        Parameters
        ----------
        files : list
            List of files to process

        Yields
        ------
        Progress
            Progress bar object for tracking

        Notes
        -----
        Uses rich library for progress display.
        """
        if self.quiet:
            # Quiet mode: no progress bar, just yield a dummy progress/task
            yield None, None
            return

        # Create message temporary storage and replace logger method
        logs = {level: [] for level in ['info', 'warning', 'error']}
        original = {level: getattr(self.logger, level) for level in logs}

        for level, msgs in logs.items():
            setattr(self.logger, level, msgs.append)

        try:
            with Progress(
                    SpinnerColumn(finished_text="✓"),
                    BarColumn(bar_width=25, complete_style="green", finished_style="bright_green"),
                    TaskProgressColumn(style="bold", text_format="[bright_green]{task.percentage:>3.0f}%"),
                    TextColumn("{task.description}", style="bold blue"),
                    TextColumn("{task.fields[filename]}", style="bold blue"),
                    console=Console(force_terminal=True, color_system="auto", width=120),
                    expand=False
            ) as progress:
                task = progress.add_task(f"Reading {self.nam} files:", total=len(files), filename="")
                yield progress, task
        finally:
            # Restore logger method and output message
            for level, msgs in logs.items():
                setattr(self.logger, level, original[level])
                for msg in msgs:
                    original[level](msg)

    def _read_raw_files(self) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
        """
        Read and process raw data files.

        Returns
        -------
        tuple[pd.DataFrame | None, pd.DataFrame | None]
            Tuple containing:
                - Raw data DataFrame or None
                - Quality controlled DataFrame or None

        Notes
        -----
        Handles file reading and initial processing.
        """
        files = [f
                 for file_pattern in self.meta['pattern']
                 for pattern in {file_pattern.lower(), file_pattern.upper(), file_pattern}
                 for f in self.path.glob(pattern)
                 if f.name not in [self.csv_out.name, self.csv_nam.name, self.csv_nam_raw.name, f'{self.nam}.log']]

        if not files:
            raise FileNotFoundError(f"No files in '{self.path}' could be read. Please check the current path.")

        self._n_files = len(files)
        df_list = []
        parsed_files = []  # kept aligned with df_list for _partition_compatible_scans
        per_file_freq = {}

        # Context manager for progress bar display
        with self.progress_reading(files) as (progress, task):
            for file in files:
                if progress is not None:
                    progress.update(task, advance=1, filename=file.name)
                try:
                    if (df := self._raw_reader(file)) is not None and not df.empty:
                        df_list.append(df)
                        parsed_files.append(file)
                        # Detect each file's native resolution before they are merged,
                        # so a mixed-resolution batch can be flagged.
                        per_file_freq[file.name] = detect_freq(df.index)
                    else:
                        self.logger.debug(f"File {file.name} produced an empty DataFrame or None.")

                except Exception as e:
                    self.logger.error(f"Error reading {file.name}: {e}")

        if not df_list:
            raise ValueError(f"\033[41m\033[97mAll files were either empty or failed to read.\033[0m")

        # Resolve one grid frequency from the per-file detections (logger is
        # restored here, so a mixed-resolution warning surfaces normally).
        self._resolved_freq, self._freq_mixed = resolve_freq(
            per_file_freq,
            override=self.raw_freq,
            fallback=self.meta.get('freq'),
            logger=self.logger,
        )

        # Drop files that belong to an incompatible scan group before they can
        # contaminate the concat (default no-op; SMPS overrides). Two AIM
        # versions of the same instrument produce different bin grids, and an
        # outer-join concat fills the mismatched columns with NaN — which
        # silently fails downstream completeness QC. Isolation up front is
        # cleaner than trying to reconcile after the fact.
        df_list = self._partition_compatible_scans(df_list, parsed_files)

        raw_data = pd.concat(df_list, axis=0).groupby(level=0).first()

        # Warn about stray timestamps (e.g. a single year-2000 row in 2023 data)
        # that would otherwise stretch the canonical native grid across a bogus
        # span; only dropped when the caller opts in via drop_outlier_dates=True.
        raw_data = self._flag_outlier_dates(raw_data)

        if self.nam in ['SMPS', 'APS', 'GRIMM']:
            # Separate numeric and non-numeric columns
            numeric_cols = []
            non_numeric_cols = []
            for col in raw_data.columns:
                try:
                    float(col)
                    numeric_cols.append(col)
                except (ValueError, TypeError):
                    non_numeric_cols.append(col)

            # Sort only numeric columns by their float value
            numeric_cols_sorted = sorted(numeric_cols, key=lambda x: float(x))

            # Reorder: numeric columns first (sorted), then non-numeric columns
            raw_data = raw_data[numeric_cols_sorted + non_numeric_cols]

        raw_data = self._timeIndex_process(raw_data)

        # Smart to_numeric: preserve truly non-numeric (text) columns
        _preserved_text = {}
        for col in raw_data.select_dtypes(include=['object', 'string']).columns:
            converted = pd.to_numeric(raw_data[col], errors='coerce')
            if converted.isna().all() and raw_data[col].notna().any():
                _preserved_text[col] = raw_data[col].copy()

        raw_data = raw_data.apply(pd.to_numeric, errors='coerce').copy(deep=True)

        for col, data in _preserved_text.items():
            raw_data[col] = data

        # Perform QC processing (raw data quality checks only)
        qc_data = self._QC(raw_data.copy(deep=True))

        # Perform processing (calculate derived parameters + validate)
        qc_data = self._process(qc_data)

        # Coerce measurements to numeric, leaving the QC bookkeeping columns alone
        # (`QC_Flag` is text, `QC_Invalid` is boolean — to_numeric would turn the
        # latter into 0/1 and lose the dtype the mask relies on).
        qc_meta_columns = [c for c in (FLAG_COLUMN, INVALID_COLUMN) if c in qc_data.columns]
        if qc_meta_columns:
            numeric_columns = [c for c in qc_data.select_dtypes(exclude=['object', 'string']).columns
                               if c not in qc_meta_columns]
            qc_data[numeric_columns] = qc_data[numeric_columns].apply(pd.to_numeric, errors='coerce')
        else:
            qc_data = qc_data.apply(pd.to_numeric, errors='coerce')

        # Make a deep copy to ensure data integrity
        qc_data_copy = qc_data.copy(deep=True)

        return raw_data, qc_data_copy

    def _run(self, user_start, user_end):
        """
        Main execution method for data processing.

        Parameters
        ----------
        user_start : datetime
            Start time for processing
        user_end : datetime
            End time for processing

        Returns
        -------
        tuple[pd.DataFrame, pd.DataFrame]
            Raw and quality-controlled frames for the requested range.

        Notes
        -----
        Two layers. ``_load_or_parse`` returns the *canonical* parsed frames
        (from the pkl cache when valid, else by reading the raw files). The
        presentation step below — grid placement to the requested range, with
        ``fill_missing`` — runs on **every** call, so a cache hit honours the
        current call's range/``fill_missing`` instead of replaying whatever was
        stored. Parse provenance restored by ``_load_or_parse`` feeds the
        ``df.attrs`` stamp in ``__call__``.
        """
        raw_base, qc_base = self._load_or_parse()

        # Presentation layer (applied every call, cache hit or fresh)
        _f_raw = self._timeIndex_process(raw_base, user_start, user_end)
        _f_qc = self._timeIndex_process(qc_base, user_start, user_end)
        _f_qc = self._outlier_process(_f_qc)

        return _f_raw, _f_qc

    def _load_or_parse(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Return the canonical parsed (raw, qc) frames, using the pkl cache when
        it exists and is current.

        Canonical = snapped to the native grid over the files' own coverage,
        NOT padded to any requested range. Parse provenance (``n_files``,
        ``raw_freq``, ``freq_mixed``) is persisted in ``df.attrs`` so a cache
        hit restores it onto ``self``. The requested range / ``fill_missing``
        is applied later, in ``_run``.
        """
        cache_exists = self.pkl_nam_raw.exists() and self.pkl_nam.exists() and not self.reset

        if cache_exists:
            raw = pd.read_pickle(self.pkl_nam_raw)
            qc = pd.read_pickle(self.pkl_nam)

            if self._cache_is_current(raw) and self._cache_is_current(qc):
                self.logger.info_box(f"Reading {self.nam} PICKLE")
                self._restore_parse_meta(raw)

                if not self.append:
                    return raw, qc

                self.logger.info_box(f"Appending new {self.nam} data")
                raw_new, qc_new = self._read_raw_files()
                raw = self._timeIndex_process(raw, append_df=raw_new)
                qc = self._timeIndex_process(qc, append_df=qc_new)
                self._stamp_parse_meta(raw)
                self._stamp_parse_meta(qc)
                self._save_data(raw, qc)
                return raw, qc

            self.logger.warning(
                f"{self.nam} cache is an older format; re-reading raw data.")

        # Fresh parse — produces canonical frames (gridded over their own span)
        self.logger.info_box(f"Reading {self.nam} RAW DATA")
        raw, qc = self._read_raw_files()
        self._stamp_parse_meta(raw)
        self._stamp_parse_meta(qc)
        self._save_data(raw, qc)
        return raw, qc

    def _cache_is_current(self, df: pd.DataFrame) -> bool:
        """True if the cached frame was written by the current cache format."""
        return df.attrs.get('cache_format') == CACHE_FORMAT

    def _stamp_parse_meta(self, df: pd.DataFrame) -> None:
        """Persist parse provenance into df.attrs so it survives the pkl cache."""
        df.attrs['cache_format'] = CACHE_FORMAT
        df.attrs['n_files'] = self._n_files
        df.attrs['raw_freq'] = self._resolved_freq
        df.attrs['freq_mixed'] = self._freq_mixed

    def _restore_parse_meta(self, df: pd.DataFrame) -> None:
        """Pull parse provenance off a cached frame back onto self (cache hit)."""
        self._n_files = df.attrs.get('n_files')
        self._resolved_freq = df.attrs.get('raw_freq')
        self._freq_mixed = df.attrs.get('freq_mixed', False)

    @staticmethod
    def reorder_dataframe_columns(df, order_lists: list[list], keep_others: bool = False):
        """
        Reorder DataFrame columns according to specified lists.

        Parameters
        ----------
        df : pd.DataFrame
            Input DataFrame
        order_lists : list[list]
            Lists specifying column order
        keep_others : bool, default=False
            If True, keeps unspecified columns at the end

        Returns
        -------
        pd.DataFrame
            DataFrame with reordered columns
        """
        new_order = []

        for order in order_lists:
            # Only add column that exist in the DataFrame and do not add them repeatedly
            new_order.extend([col for col in order if col in df.columns and col not in new_order])

        if keep_others:
            # Add all original fields not in the new order list, keeping their original order
            new_order.extend([col for col in df.columns if col not in new_order])

        return df[new_order]

    @staticmethod
    def QC_control():
        return QualityControl()

    def check_status_columns(self, df: pd.DataFrame, candidates) -> list[str]:
        """Which of ``candidates`` are present, warning loudly when none are.

        ``filter_error_status`` returns all-False for a column it cannot find, so
        a renamed status column degrades to "this instrument reported no errors,
        ever" — indistinguishable from a healthy instrument. Vendors *do* rename
        it between host-software versions (SMPS AIM 10.3 vs 11.x split the same
        information across differently-named columns), so the absence has to be
        visible.

        Returns the present names so a caller can OR their masks together.
        """
        candidates = list(candidates)
        present = [c for c in candidates if c in df.columns]

        if not present:
            seen = [str(c) for c in df.columns[:12]]
            if len(df.columns) > 12:
                seen.append('...')
            self.logger.warning(
                f"No status column found — the 'Status Error' rule cannot fire for "
                f"these files, so instrument faults will pass QC unnoticed. Looked "
                f"for: {', '.join(candidates)}. Columns present: {', '.join(seen)}. "
                f"If this export dialect names it differently, add the name to the "
                f"reader's status-column list.")

        return present

    def qc_builder(self) -> QCFlagBuilder:
        """A `QCFlagBuilder` carrying this run's severity overrides.

        Readers should use this instead of `QCFlagBuilder()` directly so that
        ``flag_severity={'Insufficient': 'warning'}`` reaches their rules, and so
        a rule that raises is reported through the reader's log.
        """
        return QCFlagBuilder(self.qc_severity_overrides, logger=self.logger)

    @staticmethod
    def qc_columns(df: pd.DataFrame) -> list[str]:
        """The QC bookkeeping columns present in ``df``, in a stable order.

        Readers that narrow their output to a fixed column list must carry both
        of them through — ``QC_Flag`` (the record) *and* ``QC_Invalid`` (the
        verdict the presentation layer masks on). Slicing with a hard-coded
        ``+ ['QC_Flag']`` silently drops the verdict, which would make every flag
        fatal again.
        """
        return [c for c in (FLAG_COLUMN, INVALID_COLUMN) if c in df.columns]

    def extend_qc_summary(self, summary: pd.DataFrame, df: pd.DataFrame, rule: str,
                          mask: pd.Series, description: str = '',
                          severity: str = ERROR) -> pd.DataFrame:
        """Add a `_process`-stage rule to a `_QC` summary and refresh the totals.

        `_QC` builds the summary before derived quantities exist, so a rule like
        ``Invalid AAE`` can only be counted later. The new row is inserted *above*
        the trailing ``Valid`` / ``Usable`` totals, and both totals are then
        recomputed from ``df``'s QC columns so they account for the late rule.

        Parameters
        ----------
        summary : pd.DataFrame
            The table returned by `QCFlagBuilder.get_summary`.
        df : pd.DataFrame
            The frame *after* `update_qc_flag` applied ``rule``.
        rule, mask, description, severity
            The late rule's name, boolean mask, description and severity.
        """
        total = len(df) or 1
        count = int(mask.sum())
        row = pd.DataFrame([{
            'Rule': rule,
            'Count': count,
            'Percentage': f'{count / total * 100:.1f}%',
            'Severity': severity,
            'Description': description,
        }])

        totals = summary['Rule'].isin(('Valid', 'Usable'))
        out = pd.concat([summary[~totals], row, summary[totals]], ignore_index=True)

        # Recompute the totals from the real columns rather than trusting the
        # pre-`_process` counts.
        if FLAG_COLUMN in df.columns:
            valid = int((df[FLAG_COLUMN] == 'Valid').sum())
            out.loc[out['Rule'] == 'Valid', ['Count', 'Percentage']] = [
                valid, f'{valid / total * 100:.1f}%']
        if INVALID_COLUMN in df.columns:
            usable = int((~df[INVALID_COLUMN].fillna(False).astype(bool)).sum())
            out.loc[out['Rule'] == 'Usable', ['Count', 'Percentage']] = [
                usable, f'{usable / total * 100:.1f}%']

        return out

    def log_qc_summary(self, summary: pd.DataFrame) -> None:
        """Log a `QCFlagBuilder.get_summary` table.

        Advisory rules are marked so it is obvious which flags kept their data.
        ``Valid`` (passed everything) and ``Usable`` (nothing invalidating) are
        both reported — they differ by the rows carrying only advisory flags.
        """
        self.logger.info(f"{self.nam} QC Summary:")
        for _, row in summary.iterrows():
            note = ' [advisory]' if row.get('Severity') == WARNING else ''
            self.logger.info(
                f"  {row['Rule']}: {row['Count']} ({row['Percentage']}){note}")

    def log_below_mdl(self, df: pd.DataFrame, mdl: dict, *, top: int = 10) -> pd.DataFrame:
        """Report, per column, how much of it sits below its detection limit.

        A value below the MDL is a *valid measurement of a low concentration* (or
        a non-detect), not a broken row — so this is a diagnostic, not a QC rule.
        Deliberately so: any non-``Valid`` flag NaNs the whole row in
        ``__call__``, and with tens of species/elements per row "any one below
        MDL" is true almost always, which would delete the dataset. Use this to
        see which species are near their limits, then decide per analysis.

        Parameters
        ----------
        df : pd.DataFrame
            The frame to inspect (columns not in ``mdl`` are ignored).
        mdl : dict
            ``{column: limit}``; entries whose limit is ``None`` are skipped.
        top : int, default=10
            How many of the worst-affected columns to log.

        Returns
        -------
        pd.DataFrame
            One row per column with ``below``, ``measured`` and ``percentage``,
            sorted worst-first. Empty if nothing could be evaluated.
        """
        rows = []
        for col, limit in (mdl or {}).items():
            if limit is None or col not in df.columns:
                continue
            values = pd.to_numeric(df[col], errors='coerce')
            measured = int(values.notna().sum())
            if not measured:
                continue
            below = int((values < limit).sum())
            rows.append({'column': col, 'limit': limit, 'below': below,
                         'measured': measured, 'percentage': below / measured * 100})

        if not rows:
            return pd.DataFrame(columns=['column', 'limit', 'below', 'measured', 'percentage'])

        report = (pd.DataFrame(rows)
                  .sort_values('percentage', ascending=False)
                  .reset_index(drop=True))

        self.logger.info(f"{self.nam} below detection limit (diagnostic, not flagged):")
        for _, row in report.head(top).iterrows():
            self.logger.info(
                f"  {row['column']}: {row['below']}/{row['measured']} "
                f"({row['percentage']:.1f}%) < MDL {row['limit']}")
        if len(report) > top:
            self.logger.info(f"  ... ({len(report) - top} more columns)")

        return report

    @staticmethod
    def update_qc_flag(df: pd.DataFrame, mask: pd.Series, flag_name: str,
                       severity: str = ERROR) -> pd.DataFrame:
        """
        Add a flag to ``QC_Flag`` for rows matching the mask, after ``_QC`` ran.

        Used by ``_process`` to flag something that can only be judged once
        derived quantities exist (e.g. ``Invalid AAE``).

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame with QC_Flag column
        mask : pd.Series
            Boolean mask indicating rows to flag
        flag_name : str
            Name of the flag to add
        severity : {'error', 'warning'}, default='error'
            ``'error'`` also marks the rows invalid, so they are masked in the
            public output; ``'warning'`` records the flag only.

        Returns
        -------
        pd.DataFrame
            DataFrame with updated ``QC_Flag`` (and ``QC_Invalid`` when the flag
            is invalidating)
        """
        if severity not in SEVERITIES:
            raise ValueError(f"severity={severity!r}; expected one of {SEVERITIES}")

        if FLAG_COLUMN not in df.columns:
            df[FLAG_COLUMN] = 'Valid'
        if INVALID_COLUMN not in df.columns:
            df[INVALID_COLUMN] = df[FLAG_COLUMN] != 'Valid'

        mask = mask.reindex(df.index).fillna(False).astype(bool)

        # For rows that are already Valid, set to flag_name
        # For rows that already have flags, append the new flag
        valid_mask = df[FLAG_COLUMN] == 'Valid'
        df.loc[mask & valid_mask, FLAG_COLUMN] = flag_name
        df.loc[mask & ~valid_mask, FLAG_COLUMN] = df.loc[mask & ~valid_mask, FLAG_COLUMN] + ', ' + flag_name

        if severity == ERROR:
            df.loc[mask, INVALID_COLUMN] = True

        return df
