import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from pandas import DataFrame, concat, read_pickle
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, TaskProgressColumn

from AeroViz.rawDataReader.config.supported_instruments import meta

__all__ = ['AbstractReader']


class AbstractReader(ABC):
    """
    Abstract class for reading raw data from different instruments. Each instrument should have a separate class that
    inherits from this class and implements the abstract methods. The abstract methods are `_raw_reader` and `_QC`.

    List the file in the path and read pickle file if it exists, else read raw data and dump the pickle file the
    pickle file will be generated after read raw data first time, if you want to re-read the rawdata, please set
    'reset=True'
    """

    nam = 'AbstractReader'

    def __init__(self,
                 path: Path | str,
                 reset: bool = False,
                 qc: bool = True,
                 qc_freq: Optional[str] = None,
                 rate: bool = True,
                 append_data: bool = False):

        self.path = Path(path)
        self.meta = meta[self.nam]
        self.logger = self._setup_logger()

        self.reset = reset
        self.qc = qc
        self.qc_freq = qc_freq
        self.rate = rate
        self.append = append_data and reset

        self.pkl_nam = self.path / f'_read_{self.nam.lower()}.pkl'
        self.csv_nam = self.path / f'_read_{self.nam.lower()}.csv'
        self.pkl_nam_raw = self.path / f'_read_{self.nam.lower()}_raw.pkl'
        self.csv_nam_raw = self.path / f'_read_{self.nam.lower()}_raw.csv'
        self.csv_out = self.path / f'output_{self.nam.lower()}.csv'

    def __call__(self,
                 start: datetime,
                 end: datetime,
                 mean_freq: str = '1h',
                 csv_out: bool = True,
                 ) -> DataFrame:

        data = self._run(start, end)

        if data is not None:
            if mean_freq:
                data = data.resample(mean_freq).mean()
            if csv_out:
                data.to_csv(self.csv_out)

        return data

    @abstractmethod
    def _raw_reader(self, file):
        pass

    @abstractmethod
    def _QC(self, df: DataFrame) -> DataFrame:
        return self.n_sigma_QC(df)

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger(self.nam)
        logger.setLevel(logging.INFO)

        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        handler = logging.FileHandler(self.path / f'{self.nam}.log')
        handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
        logger.addHandler(handler)
        return logger

    def _rate_calculate(self, raw_data, qc_data) -> None:
        def __base_rate(raw_data, qc_data):
            period_size = len(raw_data.resample('1h').mean().index)

            for _nam, _key in self.meta['deter_key'].items():
                _key, _drop_how = (qc_data.keys(), 'all') if _key is ['all'] else (_key, 'any')

                sample_size = len(raw_data[_key].resample('1h').mean().copy().dropna(how=_drop_how).index)
                qc_size = len(qc_data[_key].resample('1h').mean().copy().dropna(how=_drop_how).index)

                # validate rate calculation
                if period_size < sample_size or sample_size < qc_size or period_size == 0 or sample_size == 0:
                    raise ValueError(f"Invalid sample sizes: period={period_size}, sample={sample_size}, QC={qc_size}")

                _acq_rate = round((sample_size / period_size) * 100, 1)
                _yid_rate = round((qc_size / sample_size) * 100, 1)

                self.logger.info(f'{_nam}:')
                self.logger.info(f"\tAcquisition rate: {_acq_rate}%")
                self.logger.info(f'\tYield       rate: {_yid_rate}%')
                self.logger.info(f"{'=' * 60}")

                print(f'\n\t{_nam} : ')
                print(f'\t\tacquisition rate : \033[91m{_acq_rate}%\033[0m')
                print(f'\t\tyield       rate : \033[91m{_yid_rate}%\033[0m')

        if self.meta['deter_key'] is not None:
            # use qc_freq to calculate each period rate
            if self.qc_freq is not None:
                raw_data_grouped = raw_data.groupby(pd.Grouper(freq=self.qc_freq))
                qc_data_grouped = qc_data.groupby(pd.Grouper(freq=self.qc_freq))

                for (month, _sub_raw_data), (_, _sub_qc_data) in zip(raw_data_grouped, qc_data_grouped):
                    self.logger.info(
                        f"\tProcessing: {_sub_raw_data.index[0].strftime('%F')} to {_sub_raw_data.index[-1].strftime('%F')}")
                    print(
                        f"\n\tProcessing: {_sub_raw_data.index[0].strftime('%F')} to {_sub_raw_data.index[-1].strftime('%F')}")

                    __base_rate(_sub_raw_data, _sub_qc_data)

            else:
                __base_rate(raw_data, qc_data)

    def _timeIndex_process(self, _df, user_start=None, user_end=None, append_df=None):
        """
        Process time index, resample data, extract specified time range, and optionally append new data.

        :param _df: Input DataFrame with time index
        :param user_start: Start of user-specified time range (optional)
        :param user_end: End of user-specified time range (optional)
        :param append_df: DataFrame to append (optional)
        :return: Processed DataFrame
        """
        # Round timestamps and remove duplicates
        _df = _df.groupby(_df.index.round('1min')).first()

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

        # Process data: convert to numeric, resample, and reindex
        return (_df.apply(pd.to_numeric, errors='coerce')
                .resample(freq).mean()
                .reindex(new_index))

    def _outlier_process(self, _df):
        outlier_file = self.path / 'outlier.json'

        if not outlier_file.exists():
            return _df

        with outlier_file.open('r', encoding='utf-8', errors='ignore') as f:
            outliers = json.load(f)

        for _st, _ed in outliers.values():
            _df.loc[_st:_ed] = np.nan

        return _df

    def _save_data(self, raw_data: DataFrame, qc_data: DataFrame) -> None:
        try:
            raw_data.to_pickle(self.pkl_nam_raw)
            raw_data.to_csv(self.csv_nam_raw)

            if self.meta['deter_key'] is not None:
                qc_data.to_pickle(self.pkl_nam)
                qc_data.to_csv(self.csv_nam)

        except Exception as e:
            raise IOError(f"Error saving data. {e}")

    def _read_raw_files(self) -> tuple[DataFrame | None, DataFrame | None]:
        files = [f
                 for file_pattern in self.meta['pattern']
                 for pattern in {file_pattern.lower(), file_pattern.upper(), file_pattern}
                 for f in self.path.glob(pattern)
                 if f.name not in [self.csv_out.name, self.csv_nam.name, self.csv_nam_raw.name, f'{self.nam}.log']]

        if not files:
            raise FileNotFoundError(f"No files in '{self.path}' could be read. Please check the current path.")

        df_list = []
        with Progress(
                TextColumn("[bold blue]{task.description}", style="bold blue"),
                BarColumn(bar_width=18, complete_style="green", finished_style="bright_green"),
                TaskProgressColumn(),
                TimeRemainingColumn(),
                TextColumn("{task.fields[filename]}", style="yellow"),
                console=Console(force_terminal=True, color_system="auto"),
                expand=False
        ) as progress:
            task = progress.add_task(f"Reading {self.nam} files", total=len(files), filename="")
            for file in files:
                progress.update(task, advance=1, filename=file.name)
                try:
                    df = self._raw_reader(file)

                    if df is not None and not df.empty:
                        df_list.append(df)
                    else:
                        self.logger.warning(f"File {file.name} produced an empty DataFrame or None.")

                except pd.errors.ParserError as e:
                    self.logger.error(f"Error tokenizing data: {e}")

                except Exception as e:
                    self.logger.error(f"Error reading {file.name}: {e}")

        if not df_list:
            raise ValueError("All files were either empty or failed to read.")

        raw_data = concat(df_list, axis=0).groupby(level=0).first()

        raw_data = self._timeIndex_process(raw_data)
        qc_data = self._QC(raw_data)

        return raw_data, qc_data

    def _run(self, user_start, user_end):
        # read pickle if pickle file exists and 'reset=False' or process raw data or append new data
        if self.pkl_nam_raw.exists() and self.pkl_nam.exists() and not self.reset:
            print(f"\n{datetime.now().strftime('%m/%d %X')} : Reading {self.nam} \033[96mPICKLE\033[0m "
                  f"from {user_start} to {user_end}\n")

            _f_raw_done, _f_qc_done = read_pickle(self.pkl_nam_raw), read_pickle(self.pkl_nam)

            if self.append:
                print(f"Appending new data from {user_start} to {user_end}")
                _f_raw_new, _f_qc_new = self._read_raw_files()
                _f_raw = self._timeIndex_process(_f_raw_done, append_df=_f_raw_new)
                _f_qc = self._timeIndex_process(_f_qc_done, append_df=_f_qc_new)
            else:
                _f_raw, _f_qc = _f_raw_done, _f_qc_done
                return _f_qc if self.qc else _f_raw

        else:
            print(f"\n{datetime.now().strftime('%m/%d %X')} : Reading {self.nam} \033[96mRAW DATA\033[0m "
                  f"from {user_start} to {user_end}\n")

            _f_raw, _f_qc = self._read_raw_files()

        # process time index
        data_start, data_end = _f_raw.index.sort_values()[[0, -1]]

        _f_raw = self._timeIndex_process(_f_raw, user_start, user_end)
        _f_qc = self._timeIndex_process(_f_qc, user_start, user_end)
        _f_qc = self._outlier_process(_f_qc)

        # save
        self._save_data(_f_raw, _f_qc)

        self.logger.info(f"{'=' * 60}")
        self.logger.info(f"Raw data time : {data_start} to {data_end}")
        self.logger.info(f"Output   time : {user_start} to {user_end}")
        self.logger.info(f"{'-' * 60}")

        if self.rate:
            self._rate_calculate(_f_raw, _f_qc)

        return _f_qc if self.qc else _f_raw

    @staticmethod
    def reorder_dataframe_columns(df, order_lists, others_col=False):
        new_order = []

        for order in order_lists:
            # 只添加存在於DataFrame中的欄位，且不重複添加
            new_order.extend([col for col in order if col in df.columns and col not in new_order])

        if others_col:
            # 添加所有不在新順序列表中的原始欄位，保持它們的原始順序
            new_order.extend([col for col in df.columns if col not in new_order])

        return df[new_order]

    @staticmethod
    def n_sigma_QC(df: DataFrame, std_range: int = 5) -> DataFrame:
        df_ave, df_std = df.mean(), df.std()
        df_lowb, df_highb = df < (df_ave - df_std * std_range), df > (df_ave + df_std * std_range)

        return df.mask(df_lowb | df_highb).copy()

    # "四分位數範圍法"（Inter-quartile Range Method）
    @staticmethod
    def IQR_QC(df: DataFrame, log_dist=False) -> tuple[DataFrame, DataFrame]:
        df = np.log10(df) if log_dist else df

        _df_qua = df.quantile([.25, .75])
        _df_q1, _df_q3 = _df_qua.loc[.25].copy(), _df_qua.loc[.75].copy()
        _df_iqr = _df_q3 - _df_q1

        _se = concat([_df_q1 - 1.5 * _df_iqr] * len(df), axis=1).T.set_index(df.index)
        _le = concat([_df_q3 + 1.5 * _df_iqr] * len(df), axis=1).T.set_index(df.index)

        return (10 ** _se, 10 ** _le) if log_dist else (_se, _le)
