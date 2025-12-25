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
from AeroViz.rawDataReader.core.qc import QualityControl, QCRule, QCFlagBuilder
from AeroViz.rawDataReader.core.report import calculate_rates, process_rates_report, process_timeline_report

__all__ = ['AbstractReader', 'QCRule', 'QCFlagBuilder']


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
                log_level : str
                    Logging level for the reader
                suppress_warnings : bool
                    If True, suppresses warning messages

        Notes
        -----
        Creates necessary output directories and initializes logging system.
        Sets up paths for pickle files, CSV files, and report outputs.
        """
        self.path = Path(path)
        self.meta = meta[self.nam]
        output_folder = self.path / f'{self.nam.lower()}_outputs'
        output_folder.mkdir(parents=True, exist_ok=True)

        self.logger = ReaderLogger(
            self.nam, output_folder,
            kwargs.get('log_level').upper() if not kwargs.get('suppress_warnings') else 'ERROR')

        self.reset = reset is True
        self.append = reset == 'append'
        self.qc = qc  # if qc, then calculate rate
        self.qc_freq = qc if isinstance(qc, str) else None
        self.kwargs = kwargs

        self.pkl_nam = output_folder / f'_read_{self.nam.lower()}_qc.pkl'
        self.csv_nam = output_folder / f'_read_{self.nam.lower()}_qc.csv'
        self.pkl_nam_raw = output_folder / f'_read_{self.nam.lower()}_raw.pkl'
        self.csv_nam_raw = output_folder / f'_read_{self.nam.lower()}_raw.csv'
        self.csv_out = output_folder / f'output_{self.nam.lower()}.csv'
        self.report_out = output_folder / 'report.json'

    def __call__(self,
                 start: datetime,
                 end: datetime,
                 mean_freq: str = '1h',
                 ) -> pd.DataFrame:
        """
        Process data for a specified time range.

        Parameters
        ----------
        start : datetime
            Start time for data processing
        end : datetime
            End time for data processing
        mean_freq : str, default='1h'
            Frequency for resampling the data

        Returns
        -------
        pd.DataFrame
            Processed and resampled data for the specified time range

        Notes
        -----
        The processed data is also saved to a CSV file.
        """

        _f_raw, _f_qc = self._run(start, end)

        if not self.qc: return _f_raw

        # Extract QC_Flag before processing
        qc_flag = _f_qc['QC_Flag'].copy() if 'QC_Flag' in _f_qc else None

        # Process QC_Flag
        if 'QC_Flag' in _f_qc:
            # Set rows with QC_Flag != "Valid" to NaN while preserving index
            invalid_mask = _f_qc['QC_Flag'] != 'Valid'
            if invalid_mask.any():
                # Get all numeric columns (excluding QC_Flag column)
                numeric_columns = [col for col in _f_qc.columns if col != 'QC_Flag']
                # Set invalid data to NaN
                _f_qc.loc[invalid_mask, numeric_columns] = np.nan

            # Drop QC_Flag column
            _f_qc.drop(columns=['QC_Flag'], inplace=True)

        # Generate data acquisition and quality rate report (instrument time resolution)
        self._generate_report(_f_raw.apply(pd.to_numeric, errors='coerce'),
                              _f_qc.apply(pd.to_numeric, errors='coerce'),
                              qc_flag=qc_flag)

        _f_qc = _f_qc.resample(mean_freq).mean().__round__(4)

        _f_qc.to_csv(self.csv_out)

        # Generate timeline data (hourly values)
        report_dict = process_timeline_report(self.report_dict, _f_qc)

        # Write report
        with open(self.report_out, 'w') as f:
            json.dump(report_dict, f, indent=4)

        return _f_qc

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
            else:
                calculate_rates(self.logger, raw_data, qc_flag, with_log=True)

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
        Handles time range filtering and data appending.
        """
        # Round timestamps and remove duplicates
        _df = _df.groupby(_df.index.floor('1min')).first()

        # Determine frequency
        freq = _df.index.inferred_freq or self.meta['freq']

        # Append new data if provided
        if append_df is not None:
            append_df.index = append_df.index.round('1min')
            _df = pd.concat([append_df.dropna(how='all'), _df.dropna(how='all')])
            _df = _df.loc[~_df.index.duplicated()]

        # Determine time range
        df_start, df_end = _df.index.sort_values()[[0, -1]]

        # Create new time index
        new_index = pd.date_range(user_start or df_start, user_end or df_end, freq=freq, name='time')

        # Process data: convert to numeric, resample, and reindex with controlled tolerance
        if freq in ['1min', 'min', 'T']:
            # For minute-level data, use smaller tolerance, e.g., 30 seconds
            return _df.reindex(new_index, method='nearest', tolerance='30s')
        elif freq in ['1h', 'h', 'H']:
            # For hourly data, use 30 minutes as tolerance
            # This way 08:20 matches to 08:00, but not to 09:00
            return _df.reindex(new_index, method='nearest', tolerance='30min')
        else:
            # For other frequencies, set tolerance to half the frequency
            if isinstance(freq, str) and freq[-1].isalpha():
                # If freq format is 'number+unit', e.g., '2h', '3min'
                try:
                    num = int(freq[:-1])
                    unit = freq[-1]
                    half_freq = f"{num // 2}{unit}" if num > 1 else f"30{'min' if unit == 'h' else 's'}"
                    return _df.reindex(new_index, method='nearest', tolerance=half_freq)
                except ValueError:
                    # Cannot parse freq, use default value
                    return _df.reindex(new_index, method='nearest', tolerance=freq)
            else:
                return _df.reindex(new_index, method='nearest', tolerance=freq)

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
            raw_data.to_pickle(self.pkl_nam_raw)
            raw_data.to_csv(self.csv_nam_raw)
            qc_data.to_pickle(self.pkl_nam)
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

        df_list = []

        # Context manager for progress bar display
        with self.progress_reading(files) as (progress, task):
            for file in files:
                progress.update(task, advance=1, filename=file.name)
                try:
                    if (df := self._raw_reader(file)) is not None and not df.empty:
                        df_list.append(df)
                    else:
                        self.logger.debug(f"File {file.name} produced an empty DataFrame or None.")

                except Exception as e:
                    self.logger.error(f"Error reading {file.name}: {e}")

        if not df_list:
            raise ValueError(f"\033[41m\033[97mAll files were either empty or failed to read.\033[0m")

        raw_data = pd.concat(df_list, axis=0).groupby(level=0).first()

        if self.nam in ['SMPS', 'APS', 'GRIMM']:
            raw_data = raw_data.sort_index(axis=1, key=lambda x: x.astype(float))

        raw_data = self._timeIndex_process(raw_data)

        raw_data = raw_data.apply(pd.to_numeric, errors='coerce').copy(deep=True)

        # Perform QC processing (raw data quality checks only)
        qc_data = self._QC(raw_data.copy(deep=True))

        # Perform processing (calculate derived parameters + validate)
        qc_data = self._process(qc_data)

        # Only convert numeric columns to numeric, preserve QC_Flag column string values
        if 'QC_Flag' in qc_data.columns:
            numeric_columns = qc_data.select_dtypes(exclude=['object', 'string']).columns
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
        pd.DataFrame
            Processed data for the specified time range

        Notes
        -----
        Coordinates the entire data processing workflow.
        """
        # read pickle if pickle file exists and 'reset=False' or process raw data or append new data
        if self.pkl_nam_raw.exists() and self.pkl_nam.exists() and not self.reset:
            self.logger.info_box(f"Reading {self.nam} PICKLE from {user_start} to {user_end}")

            _f_raw_done, _f_qc_done = pd.read_pickle(self.pkl_nam_raw), pd.read_pickle(self.pkl_nam)

            if self.append:
                self.logger.info_box(f"Appending New data from {user_start} to {user_end}")

                _f_raw_new, _f_qc_new = self._read_raw_files()
                _f_raw = self._timeIndex_process(_f_raw_done, append_df=_f_raw_new)
                _f_qc = self._timeIndex_process(_f_qc_done, append_df=_f_qc_new)

            else:
                _f_raw, _f_qc = _f_raw_done, _f_qc_done

                return _f_raw, _f_qc

        else:
            self.logger.info_box(f"Reading {self.nam} RAW DATA from {user_start} to {user_end}")

            _f_raw, _f_qc = self._read_raw_files()

        # process time index
        _f_raw = self._timeIndex_process(_f_raw, user_start, user_end)
        _f_qc = self._timeIndex_process(_f_qc, user_start, user_end)

        # process outlier
        _f_qc = self._outlier_process(_f_qc)

        # save
        self._save_data(_f_raw, _f_qc)

        return _f_raw, _f_qc

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

    @staticmethod
    def update_qc_flag(df: pd.DataFrame, mask: pd.Series, flag_name: str) -> pd.DataFrame:
        """
        Update QC_Flag column for rows matching the mask.

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame with QC_Flag column
        mask : pd.Series
            Boolean mask indicating rows to flag
        flag_name : str
            Name of the flag to add

        Returns
        -------
        pd.DataFrame
            DataFrame with updated QC_Flag column
        """
        if 'QC_Flag' not in df.columns:
            df['QC_Flag'] = 'Valid'

        # For rows that are already Valid, set to flag_name
        # For rows that already have flags, append the new flag
        valid_mask = df['QC_Flag'] == 'Valid'
        df.loc[mask & valid_mask, 'QC_Flag'] = flag_name
        df.loc[mask & ~valid_mask, 'QC_Flag'] = df.loc[mask & ~valid_mask, 'QC_Flag'] + ', ' + flag_name

        return df
