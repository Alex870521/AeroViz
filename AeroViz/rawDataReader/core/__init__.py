import json as jsn
import logging
import pickle as pkl
from abc import ABC, abstractmethod
from datetime import datetime as dtm
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pandas import DataFrame, date_range, concat, to_numeric, to_datetime

from ..config.supported_instruments import meta

__all__ = ['AbstractReader']


class AbstractReader(ABC):
    nam = 'AbstractReader'

    # initial data
    # input : file path, reset switch

    # list the file in the path and read pickle file if it exists, else read raw data and dump the pickle file the
    # pickle file will be generated after read raw data first time, if you want to re-read the rawdata, please set
    # 'reset=True'

    def __init__(self,
                 path: Path | str,
                 qc: bool = True,
                 csv_raw: bool = True,
                 reset: bool = False,
                 rate: bool = False,
                 append_data: bool = False):

        self.path = Path(path)
        self.meta = meta[self.nam]
        self.logger = self._setup_logger()

        self.reset = reset
        self.rate = rate
        self.qc = qc
        self.csv = csv_raw
        self.append = append_data & reset

        self.pkl_nam = self.path / f'_read_{self.nam.lower()}.pkl'
        self.csv_nam = self.path / f'_read_{self.nam.lower()}.csv'
        self.pkl_nam_raw = self.path / f'_read_{self.nam.lower()}_raw.pkl'
        self.csv_nam_raw = self.path / f'_read_{self.nam.lower()}_raw.csv'
        self.csv_out = self.path / f'output_{self.nam.lower()}.csv'

    # dependency injection function, customize each instrument
    @abstractmethod
    def _raw_reader(self, file):
        pass

    @abstractmethod
    def _QC(self, df: DataFrame):
        return df

    def __call__(self,
                 start: dtm | None = None,
                 end: dtm | None = None,
                 mean_freq: str = '1h',
                 csv_out: bool = True,
                 ) -> DataFrame | None:

        if start and end and end <= start:
            raise ValueError(f"Invalid time range: start {start} is after end {end}")

        data = self._run(start, end)

        if data is not None:
            if mean_freq:
                data = data.resample(mean_freq).mean()
            if csv_out:
                data.to_csv(self.csv_out)

        return data

    @staticmethod
    def basic_QC(df: DataFrame):
        df_ave, df_std = df.mean(), df.std()
        df_lowb, df_highb = df < (df_ave - df_std * 1.5), df > (df_ave + df_std * 1.5)

        return df.mask(df_lowb | df_highb).copy()

    # set each to true datetime(18:30:01 -> 18:30:00) and rindex data
    def _raw_process(self, _df):
        # get time from df and set time to whole time to create time index
        _st, _ed = _df.index.sort_values()[[0, -1]]
        _tm_index = date_range(_st.strftime('%Y%m%d %H00'), _ed.floor('h').strftime('%Y%m%d %H00'),
                               freq=self.meta['freq'])
        _tm_index.name = 'time'

        return _df.apply(to_numeric, errors='coerce').resample(self.meta['freq']).mean().reindex(_tm_index)

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger(self.nam)
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(self.path / f'{self.nam}.log')
        handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        logger.addHandler(handler)
        return logger

    # acquisition rate and yield rate
    def _rate_calculate(self, _fout_raw, _fout_qc, _st_raw, _ed_raw):
        if self.meta['deter_key'] is not None:
            _start, _end = _fout_qc.index[[0, -1]]

            _drop_how = 'any'
            _the_size = len(_fout_raw.resample('1h').mean().index)

            self.logger.info(f"{'=' * 60}")
            self.logger.info(
                f"Raw data time : {_st_raw.strftime('%Y-%m-%d %H:%M:%S')} to {_ed_raw.strftime('%Y-%m-%d %H:%M:%S')}")
            self.logger.info(
                f"Output   time : {_start.strftime('%Y-%m-%d %H:%M:%S')} to {_end.strftime('%Y-%m-%d %H:%M:%S')}")
            self.logger.info(f"{'-' * 60}")
            print(f"\n\n\t\tfrom {_start.strftime('%Y-%m-%d %H:%M:%S')} to {_end.strftime('%Y-%m-%d %H:%M:%S')}\n")

            for _nam, _key in self.meta['deter_key'].items():
                if _key == ['all']:
                    _key, _drop_how = _fout_qc.keys(), 'all'

                _real_size = len(_fout_raw[_key].resample('1h').mean().copy().dropna(how=_drop_how).index)
                _QC_size = len(_fout_qc[_key].resample('1h').mean().copy().dropna(how=_drop_how).index)

                try:
                    _acq_rate = round((_real_size / _the_size) * 100, 1)
                    _yid_rate = round((_QC_size / _real_size) * 100, 1)
                except ZeroDivisionError:
                    _acq_rate, _yid_rate = 0, 0

                self.logger.info(f'{_nam}:')
                self.logger.info(f"\tAcquisition rate: {_acq_rate}%")
                self.logger.info(f'\tYield       rate: {_yid_rate}%')
                self.logger.info(f"{'=' * 60}")

                print(f'\t\t{_nam} : ')
                print(f'\t\t\tacquisition rate : \033[91m{_acq_rate}%\033[0m')
                print(f'\t\t\tyield       rate : \033[91m{_yid_rate}%\033[0m')

    # process time index
    @staticmethod
    def _tmidx_process(_start, _end, _df):
        _st, _ed = _df.index.sort_values()[[0, -1]]
        _start, _end = to_datetime(_start) or _st, to_datetime(_end) or _ed
        _idx = date_range(_start, _end, freq=_df.index.freq.copy())
        _idx.name = 'time'

        return _df.reindex(_idx), _st, _ed

    # append new data to exist pkl
    @staticmethod
    def _apnd_prcs(_df_done, _df_apnd):

        if _df_apnd is not None:
            _df = concat([_df_apnd.dropna(how='all').copy(), _df_done.dropna(how='all').copy()])

            _idx = date_range(*_df.index.sort_values()[[0, -1]], freq=_df_done.index.freq.copy())
            _idx.name = 'time'

            return _df.loc[~_df.index.duplicated()].copy().reindex(_idx)

        return _df_done

    # remove outlier
    def _outlier_prcs(self, _df):

        if (self.path / 'outlier.json') not in self.path.glob('*.json'):
            return _df

        with (self.path / 'outlier.json').open('r', encoding='utf-8', errors='ignore') as f:
            self.outlier = jsn.load(f)

        for _st, _ed in self.outlier.values():
            _df.loc[_st:_ed] = np.nan

        return _df

    # save pickle file
    def _save_data(self, raw_data: DataFrame, qc_data: DataFrame) -> None:
        self._safe_pickle_dump(self.pkl_nam, qc_data)
        if self.csv:
            qc_data.to_csv(self.csv_nam)

        if self.meta['deter_key'] is not None:
            self._safe_pickle_dump(self.pkl_nam_raw, raw_data)
            if self.csv:
                raw_data.to_csv(self.csv_nam_raw)

    @staticmethod
    def _safe_pickle_dump(file_path: Path, data: Any) -> None:
        while True:
            try:
                with file_path.open('wb') as f:
                    pkl.dump(data, f, protocol=pkl.HIGHEST_PROTOCOL)
                break
            except PermissionError as err:
                print('\n', err)
                input('\t\t\33[41m Please close the file and press "Enter" \33[0m\n')

    # read pickle file
    def _read_pkl(self):
        with self.pkl_nam.open('rb') as qc_data, self.pkl_nam_raw.open('rb') as raw_data:
            return pkl.load(raw_data), pkl.load(qc_data)

    def _read_raw_files(self) -> tuple[DataFrame | None, DataFrame | None]:
        patterns = {self.meta['pattern'].lower(), self.meta['pattern'].upper(), self.meta['pattern']}
        files = [f for pattern in patterns for f in self.path.glob(pattern)
                 if f.name not in [self.csv_out.name, self.csv_nam.name, self.csv_nam_raw.name, f'{self.nam}.log']]

        if not files:
            raise FileNotFoundError(f"\t\t\033[31mNo files in '{self.path}' could be read."
                                    f"Please check the current path.\033[0m")

        df_list = []
        for file in files:
            print(f"\r\t\treading {file.name}", end='')

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

        raw_data = self._raw_process(concat(df_list))
        qc_data = self._QC(raw_data)

        return raw_data, qc_data

    # main flow
    def _run(self, _start, _end):
        _f_raw_done, _f_qc_done = None, None

        # read pickle if pickle file exists and 'reset=False' or process raw data or append new data
        if self.pkl_nam_raw.exists() and self.pkl_nam.exists() and (not self.reset or self.append):
            print(f"\n\t{dtm.now().strftime('%m/%d %X')} : Reading \033[96mPICKLE\033[0m file of {self.nam}")

            _f_raw_done, _f_qc_done = self._read_pkl()

            if not self.append:
                _f_raw_done, _start_raw, _end_raw = self._tmidx_process(_start, _end, _f_raw_done)
                _f_qc_done, _start_raw, _end_raw = self._tmidx_process(_start, _end, _f_qc_done)

                _f_qc_done = self._outlier_prcs(_f_qc_done)

                if self.rate:
                    self._rate_calculate(_f_raw_done, _f_qc_done, _start_raw, _end_raw)

                return _f_qc_done if self.qc else _f_raw_done

        # read raw data
        print(f"\n\t{dtm.now().strftime('%m/%d %X')} : Reading \033[96mRAW DATA\033[0m of {self.nam} and process it")

        _f_raw, _f_qc = self._read_raw_files()

        # append new data and pickle data
        if self.append and self.pkl_nam.exists():
            _f_raw = self._apnd_prcs(_f_raw_done, _f_raw)
            _f_qc = self._apnd_prcs(_f_qc_done, _f_qc)

        _f_qc = self._outlier_prcs(_f_qc)

        # save
        self._save_data(_f_raw, _f_qc)

        # process time index
        # if (_start is not None)|(_end is not None):
        _f_raw, _start_raw, _end_raw = self._tmidx_process(_start, _end, _f_raw)
        _f_qc, _start_raw, _end_raw = self._tmidx_process(_start, _end, _f_qc)

        self._rate_calculate(_f_raw, _f_qc, _start_raw, _end_raw)

        return _f_qc if self.qc else _f_raw
