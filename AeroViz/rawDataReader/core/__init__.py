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
from AeroViz.rawDataReader.core.qc import QualityControl

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
                 reset: bool | str = False,
                 qc: bool | str = True,
                 **kwargs):

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

        self.pkl_nam = output_folder / f'_read_{self.nam.lower()}.pkl'
        self.csv_nam = output_folder / f'_read_{self.nam.lower()}.csv'
        self.pkl_nam_raw = output_folder / f'_read_{self.nam.lower()}_raw.pkl'
        self.csv_nam_raw = output_folder / f'_read_{self.nam.lower()}_raw.csv'
        self.csv_out = output_folder / f'output_{self.nam.lower()}.csv'
        self.report_out = output_folder / 'report.json'

    def __call__(self,
                 start: datetime,
                 end: datetime,
                 mean_freq: str = '1h',
                 ) -> pd.DataFrame:

        data = self._run(start, end)

        if data is not None:
            data = data.resample(mean_freq).mean()

        data.to_csv(self.csv_out)

        return data

    @abstractmethod
    def _raw_reader(self, file):
        pass

    @abstractmethod
    def _QC(self, df: pd.DataFrame) -> pd.DataFrame:
        return df

    def __calculate_rates(self, raw_data, qc_data, all_keys=False, with_log=False):
        """計算獲取率、良率和總比率

        Args:
            raw_data: 原始數據
            qc_data: QC後的數據
            all_keys: 是否計算所有 deter_key
            with_log: 是否輸出計算日誌
        """
        if raw_data.empty or qc_data.empty:
            return {'acquisition_rate': 0, 'yield_rate': 0, 'total_rate': 0}

        def _calculate_single_key(key_name, key_columns):
            columns, drop_how = (qc_data.keys(), 'all') if key_columns == ['all'] else (key_columns, 'any')

            # 重採樣並計算有效數據量
            period_size = len(raw_data.resample('1h').mean().index)
            sample_size = len(raw_data[columns].resample('1h').mean().dropna(how=drop_how).index)
            qc_size = len(qc_data[columns].resample('1h').mean().dropna(how=drop_how).index)

            # 驗證計算
            if any([
                period_size == 0 or sample_size == 0 or qc_size == 0,
                period_size < sample_size,
                sample_size < qc_size
            ]):
                if with_log:
                    self.logger.warning(f'\t\t No data for this period... skip')
                return None

            # 計算比率
            sample_rate = round((sample_size / period_size) * 100, 1)
            valid_rate = round((qc_size / sample_size) * 100, 1)
            total_rate = round((qc_size / period_size) * 100, 1)

            if with_log:
                self.logger.info(f"\t\t> {key_name}")
                self.logger.info(
                    f"\t\t\t> {'Sample Rate':13}: {self.logger.BLUE}{sample_rate:>6.1f}%{self.logger.RESET}")
                self.logger.info(
                    f"\t\t\t> {'Valid  Rate':13}: {self.logger.BLUE}{valid_rate:>6.1f}%{self.logger.RESET}")
                self.logger.info(
                    f"\t\t\t> {'Total  Rate':13}: {self.logger.BLUE}{total_rate:>6.1f}%{self.logger.RESET}")

            return {
                'acquisition_rate': sample_rate,
                'yield_rate': valid_rate,
                'total_rate': total_rate
            }

        if all_keys:
            # 計算所有 key 並回傳所有結果（用於日誌輸出）
            all_results = []
            for name, columns in self.meta['deter_key'].items():
                result = _calculate_single_key(name, columns)
                if result:
                    all_results.append(result)

            if not all_results:
                return {'acquisition_rate': 0, 'yield_rate': 0, 'total_rate': 0}

            # 回傳所有結果中比率最低的
            return {
                'acquisition_rate': min(r['acquisition_rate'] for r in all_results),
                'yield_rate': min(r['yield_rate'] for r in all_results),
                'total_rate': min(r['total_rate'] for r in all_results)
            }
        else:
            # 計算所有 key 但只回傳最低的比率
            min_rates = {'acquisition_rate': 200, 'yield_rate': 200, 'total_rate': 200}

            for name, columns in self.meta['deter_key'].items():
                result = _calculate_single_key(name, columns)
                if result:
                    min_rates['acquisition_rate'] = min(min_rates['acquisition_rate'], result['acquisition_rate'])
                    min_rates['yield_rate'] = min(min_rates['yield_rate'], result['yield_rate'])
                    min_rates['total_rate'] = min(min_rates['total_rate'], result['total_rate'])

            # 如果沒有任何有效結果，回傳 0
            if min_rates['acquisition_rate'] == 200 and min_rates['yield_rate'] == 200:
                return {'acquisition_rate': 0, 'yield_rate': 0, 'total_rate': 0}

            return min_rates

    def _rate_calculate(self, raw_data, qc_data) -> None:
        if self.meta['deter_key'] is not None:
            if self.qc_freq is not None:
                raw_data_grouped = raw_data.groupby(pd.Grouper(freq=self.qc_freq))
                qc_data_grouped = qc_data.groupby(pd.Grouper(freq=self.qc_freq))

                for (month, _sub_raw_data), (_, _sub_qc_data) in zip(raw_data_grouped, qc_data_grouped):
                    self.logger.info(
                        f"\t{self.logger.BLUE}> Processing: {_sub_raw_data.index[0].strftime('%F')}"
                        f" to {_sub_raw_data.index[-1].strftime('%F')}{self.logger.RESET}")

                    self.__calculate_rates(_sub_raw_data, _sub_qc_data, all_keys=True, with_log=True)
            else:
                self.__calculate_rates(raw_data, qc_data, all_keys=True, with_log=True)

            # 使用 Grouper 對數據按週和月進行分組
            current_time = datetime.now()

            # 按週分組 (使用星期一作為每週的開始)
            weekly_raw_groups = raw_data.groupby(pd.Grouper(freq='W-MON'))
            weekly_qc_groups = qc_data.groupby(pd.Grouper(freq='W-MON'))

            # 按月分組 (使用月初作為每月的開始)
            monthly_raw_groups = raw_data.groupby(pd.Grouper(freq='MS'))
            monthly_qc_groups = qc_data.groupby(pd.Grouper(freq='MS'))

            # 生成報告
            self.__generate_grouped_report(
                current_time,
                weekly_raw_groups, weekly_qc_groups,
                monthly_raw_groups, monthly_qc_groups
            )

    def __generate_grouped_report(self, current_time, weekly_raw_groups, weekly_qc_groups,
                                  monthly_raw_groups, monthly_qc_groups):
        """生成基於分組數據的獲取率和良率報告"""
        report = {
            "report_time": current_time.strftime('%Y-%m-%d %H:%M:%S'),
            "instrument_info": {
                "station": self.path.name[:2],
                "instrument": self.nam
            },
            "rates": {
                "weekly": {},
                "monthly": {}
            }
        }

        # 處理週數據 - 使用標準週時間範圍
        for week_start, week_raw_data in weekly_raw_groups:
            # 獲取對應的QC數據
            week_qc_data = weekly_qc_groups.get_group(
                week_start) if week_start in weekly_qc_groups.groups else pd.DataFrame()

            if not week_raw_data.empty:
                # 計算標準週結束時間（週日23:59:59）
                week_end = week_start + pd.Timedelta(days=6, hours=23, minutes=59, seconds=59)

                # 使用週的開始日期作為鍵
                period_key = week_start.strftime('%Y-%m-%d')

                report["rates"]["weekly"][period_key] = {
                    "start_time": week_start.strftime('%Y-%m-%d %H:%M:%S'),
                    "end_time": week_end.strftime('%Y-%m-%d %H:%M:%S'),
                    "rates": self.__calculate_rates(week_raw_data, week_qc_data)
                }

        # 處理月數據 - 使用標準月時間範圍
        for month_start, month_raw_data in monthly_raw_groups:
            # 獲取對應的QC數據
            month_qc_data = monthly_qc_groups.get_group(
                month_start) if month_start in monthly_qc_groups.groups else pd.DataFrame()

            if not month_raw_data.empty:
                # 計算標準月結束時間（月末23:59:59）
                next_month_start = (month_start + pd.Timedelta(days=32)).replace(day=1)
                month_end = next_month_start - pd.Timedelta(seconds=1)

                # 使用月份作為鍵
                period_key = month_start.strftime('%Y-%m')

                report["rates"]["monthly"][period_key] = {
                    "start_time": month_start.strftime('%Y-%m-%d %H:%M:%S'),
                    "end_time": month_end.strftime('%Y-%m-%d %H:%M:%S'),
                    "rates": self.__calculate_rates(month_raw_data, month_qc_data)
                }

        # 寫入報告
        with open(self.report_out, 'w') as f:
            json.dump(report, f, indent=4)

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
            # 對於分鐘級數據，使用較小的tolerance，例如30秒
            return _df.reindex(new_index, method='nearest', tolerance='30s')
        elif freq in ['1h', 'h', 'H']:
            # 對於小時級數據，使用30分鐘作為tolerance
            # 這樣08:20會匹配到08:00，但不會匹配到09:00
            return _df.reindex(new_index, method='nearest', tolerance='30min')
        else:
            # 對於其他頻率，tolerance設置為頻率的一半
            if isinstance(freq, str) and freq[-1].isalpha():
                # 如果freq格式為'數字+單位'，例如'2h'，'3min'
                try:
                    num = int(freq[:-1])
                    unit = freq[-1]
                    half_freq = f"{num // 2}{unit}" if num > 1 else f"30{'min' if unit == 'h' else 's'}"
                    return _df.reindex(new_index, method='nearest', tolerance=half_freq)
                except ValueError:
                    # 無法解析freq，使用默認值
                    return _df.reindex(new_index, method='nearest', tolerance=freq)
            else:
                return _df.reindex(new_index, method='nearest', tolerance=freq)

    def _outlier_process(self, _df):
        outlier_file = self.path / 'outlier.json'

        if not outlier_file.exists():
            return _df

        with outlier_file.open('r', encoding='utf-8', errors='ignore') as f:
            outliers = json.load(f)

        for _st, _ed in outliers.values():
            _df.loc[_st:_ed] = np.nan

        return _df

    def _save_data(self, raw_data: pd.DataFrame, qc_data: pd.DataFrame) -> None:
        try:
            raw_data.to_pickle(self.pkl_nam_raw)
            raw_data.to_csv(self.csv_nam_raw)

            if self.meta['deter_key'] is not None:
                qc_data.to_pickle(self.pkl_nam)
                qc_data.to_csv(self.csv_nam)

        except Exception as e:
            raise IOError(f"Error saving data. {e}")

    @contextmanager
    def progress_reading(self, files: list) -> Generator:
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
                        self.logger.debug(f"\tFile {file.name} produced an empty DataFrame or None.")

                except Exception as e:
                    self.logger.error(f"Error reading {file.name}: {e}")

        if not df_list:
            raise ValueError(f"\033[41m\033[97mAll files were either empty or failed to read.\033[0m")

        raw_data = pd.concat(df_list, axis=0).groupby(level=0).first()

        if self.nam in ['SMPS', 'APS', 'GRIMM']:
            raw_data = raw_data.sort_index(axis=1, key=lambda x: x.astype(float))

        raw_data = self._timeIndex_process(raw_data)

        raw_data = raw_data.apply(pd.to_numeric, errors='coerce').copy(deep=True)
        qc_data = self._QC(raw_data).apply(pd.to_numeric, errors='coerce').copy(deep=True)

        return raw_data, qc_data

    def _run(self, user_start, user_end):
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

                return _f_qc if self.qc else _f_raw

        else:
            self.logger.info_box(f"Reading {self.nam} RAW DATA from {user_start} to {user_end}")

            _f_raw, _f_qc = self._read_raw_files()

        # process time index
        _f_raw = self._timeIndex_process(_f_raw, user_start, user_end)
        _f_qc = self._timeIndex_process(_f_qc, user_start, user_end)
        _f_qc = self._outlier_process(_f_qc)

        # save
        self._save_data(_f_raw, _f_qc)

        if self.qc:
            self._rate_calculate(_f_raw.apply(pd.to_numeric, errors='coerce'),
                                 _f_qc.apply(pd.to_numeric, errors='coerce'))

        return _f_qc if self.qc else _f_raw

    @staticmethod
    def reorder_dataframe_columns(df, order_lists: list[list], keep_others: bool = False):
        new_order = []

        for order in order_lists:
            # Only add column that exist in the DataFrame and do not add them repeatedly
            new_order.extend([col for col in order if col in df.columns and col not in new_order])

        if keep_others:
            # Add all original fields not in the new order list, keeping their original order
            new_order.extend([col for col in df.columns if col not in new_order])

        return df[new_order]

    @staticmethod
    def time_aware_IQR_QC(df: pd.DataFrame, time_window='1D', log_dist=False) -> pd.DataFrame:
        return QualityControl().time_aware_iqr(df, time_window=time_window, log_dist=log_dist)
