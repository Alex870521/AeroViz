import json as jsn
import pickle as pkl
from abc import ABC, abstractmethod
from datetime import datetime as dtm, timedelta as dtmdt
from itertools import chain
from pathlib import Path

import numpy as np
from pandas import DataFrame, date_range, concat, to_numeric, to_datetime

from ..utils.config import meta

__all__ = ['AbstractReader']


class AbstractReader(ABC):
	nam = 'AbstractReader'

	# initial config
	# input : file path, reset switch

	# list the file in the path and read pickle file if it exists, else read raw data and dump the pickle file the
	# pickle file will be generated after read raw data first time, if you want to re-read the rawdata, please set
	# 'reset=True'

	def __init__(self, _path, QC=True, csv_raw=True, reset=False, rate=False, append_data=False, update_meta=None):
		# logging.info(f'\n{self.nam}')
		# print('='*65)
		# logger.info(f"Reading file and process data")

		# class parameter
		# self.index = lambda _freq: date_range(_sta, _fin, freq=_freq)
		self.path = Path(_path)
		self.meta = meta[self.nam]

		if update_meta is not None:
			self.meta.update(update_meta)

		self.reset = reset
		self.rate = rate
		self.qc = QC
		self.csv = csv_raw
		self.apnd = append_data & reset

		self.pkl_nam = f'_read_{self.nam.lower()}.pkl'
		self.csv_nam = f'_read_{self.nam.lower()}.csv'

		self.pkl_nam_raw = f'_read_{self.nam.lower()}_raw.pkl'
		self.csv_nam_raw = f'_read_{self.nam.lower()}_raw.csv'

		self.csv_out = f'output_{self.nam.lower()}.csv'

	# print(f" from {_sta.strftime('%Y-%m-%d %X')} to {_fin.strftime('%Y-%m-%d %X')}")
	# print('='*65)
	# print(f"{dtm.now().strftime('%m/%d %X')}")

	# get data
	def __call__(self,
				 start: dtm | None = None,
				 end: dtm | None = None,
				 mean_freq='1h',
				 csv_out=True,
				 **kwarg):

		self._oth_set = kwarg

		if start and end and end <= start:
			raise ValueError(
				f'\nPlease check out input time : \n\tstart : {start.strftime("%Y-%m-%d %X")}\n\tend   : {end.strftime("%Y-%m-%d %X")}')

		fout = self._run(start, end)

		if fout is not None:
			if mean_freq is not None:
				fout = fout.resample(mean_freq).mean()

			if csv_out:
				fout.to_csv(self.path / self.csv_out)

		return fout

	# dependency injection function
	@abstractmethod
	def _raw_reader(self, _file):
		# customize each instrument
		pass

	@abstractmethod
	def _QC(self, df: DataFrame):
		# customize each instrument
		return df

	# set each to true datetime(18:30:01 -> 18:30:00) and rindex data
	def _raw_process(self, _df):
		# get time from df and set time to whole time to create time index
		_st, _ed = _df.index.sort_values()[[0, -1]]
		_tm_index = date_range(_st.strftime('%Y%m%d %H00'),
							   (_ed + dtmdt(hours=1)).strftime('%Y%m%d %H00'),
							   freq=self.meta['freq'])
		_tm_index.name = 'time'

		return _df.apply(to_numeric, errors='coerce').resample(self.meta['freq']).mean().reindex(_tm_index)

	# acquisition rate and yield rate
	def _rate_calculate(self, _fout_raw, _fout_qc, _st_raw, _ed_raw):

		if self.meta['deter_key'] is not None:
			_start, _end = _fout_qc.index[[0, -1]]

			_drop_how = 'any'
			_the_size = len(_fout_raw.resample('1h').mean().index)

			_f_pth = (self.path / f'{self.nam}.log')
			_f = _f_pth.open('r+' if _f_pth.exists() else 'w+')

			_cont = _f.read()
			_f.seek(0)

			_f.write(f"\n{dtm.now().strftime('%Y/%m/%d %X')}\n")
			_f.write(f"{'-' * 60}\n")
			_f.write(f"rawdata time : \n\t{_st_raw.strftime('%Y-%m-%d %X')} ~ {_ed_raw.strftime('%Y-%m-%d %X')}\n")
			_f.write(f"output time : \n\t{_start.strftime('%Y-%m-%d %X')} ~ {_end.strftime('%Y-%m-%d %X')}\n")
			_f.write(f"{'-' * 60}\n")
			print(f"\n\t\tfrom {_start.strftime('%Y-%m-%d %X')} to {_end.strftime('%Y-%m-%d %X')}\n")

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

				_f.write(f'{_nam} : \n')
				_f.write(f"\tacquisition rate : {_acq_rate}%\n")
				_f.write(f'\tyield rate : {_yid_rate}%\n')

				print(f'\t\t{_nam} : ')
				print(f'\t\t\tacquisition rate : \033[91m{_acq_rate}%\033[0m')
				print(f'\t\t\tyield rate : \033[91m{_yid_rate}%\033[0m')

			_f.write(f"{'=' * 40}\n")
			_f.write(_cont)

			_f.close()

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
	def _save_dt(self, _save_raw, _save_qc):
		# dump pickle file
		_check = True
		while _check:
			try:
				with (self.path / self.pkl_nam).open('wb') as f:
					pkl.dump(_save_qc, f, protocol=pkl.HIGHEST_PROTOCOL)

				# dump csv file
				if self.csv:
					_save_qc.to_csv(self.path / self.csv_nam)

				# output raw data if qc file
				if self.meta['deter_key'] is not None:
					with (self.path / self.pkl_nam_raw).open('wb') as f:
						pkl.dump(_save_raw, f, protocol=pkl.HIGHEST_PROTOCOL)

					if self.csv:
						_save_raw.to_csv(self.path / self.csv_nam_raw)

				_check = False

			except PermissionError as _err:
				print('\n', _err)
				input('\t\t\33[41m Please Close The File And Press "Enter" \33[0m\n')

	# read pickle file
	def _read_pkl(self, ):
		with (self.path / self.pkl_nam).open('rb') as f:
			_fout_qc = pkl.load(f)

		if (self.path / self.pkl_nam_raw).exists():
			with (self.path / self.pkl_nam_raw).open('rb') as f:
				_fout_raw = pkl.load(f)
		else:
			_fout_raw = _fout_qc

		return _fout_raw, _fout_qc

	# read raw data
	def _read_raw(self, ):
		pattern = self.meta['pattern']
		patterns = {pattern, pattern.lower(), pattern.upper()}
		_df_con, _f_list = None, list(chain.from_iterable(self.path.glob(p) for p in patterns))

		for file in _f_list:
			if file.name in [self.csv_out, self.csv_nam, self.csv_nam_raw, f'{self.nam}.log']:
				continue

			print(f"\r\t\treading {file.name}", end='')

			_df = self._raw_reader(file)

			# concat the concated list
			if _df is not None:
				_df_con = concat([_df_con, _df]) if _df_con is not None else _df

		if _df_con is None:
			print(f"\t\t\033[31mNo File in '{self.path}' Could Read, Please Check Out the Current Path\033[0m")
			return None, None

		# QC
		_fout_raw = self._raw_process(_df_con)
		_fout_qc = self._QC(_fout_raw)

		return _fout_raw, _fout_qc

	# main flow
	def _run(self, _start, _end):

		_f_raw_done, _f_qc_done = None, None

		# read pickle if pickle file exists and 'reset=False' or process raw data or append new data
		_pkl_exist = self.path / self.pkl_nam in list(self.path.glob('*.pkl'))
		if _pkl_exist & ((~self.reset) | self.apnd):
			print(f"\n\t{dtm.now().strftime('%m/%d %X')} : Reading \033[96mPICKLE\033[0m file of {self.nam}")

			_f_raw_done, _f_qc_done = self._read_pkl()

			if not self.apnd:
				_f_raw_done, _start_raw, _end_raw = self._tmidx_process(_start, _end, _f_raw_done)
				_f_qc_done, _start_raw, _end_raw = self._tmidx_process(_start, _end, _f_qc_done)

				_f_qc_done = self._outlier_prcs(_f_qc_done)

				if self.rate:
					self._rate_calculate(_f_raw_done, _f_qc_done, _start_raw, _end_raw)

				return _f_qc_done if self.qc else _f_raw_done

		# read raw data
		print(f"\n\t{dtm.now().strftime('%m/%d %X')} : Reading \033[96mRAW DATA\033[0m of {self.nam} and process it")

		_f_raw, _f_qc = self._read_raw()
		if _f_raw is None:
			return None

		# append new data and pickle data
		if self.apnd & _pkl_exist:
			_f_raw = self._apnd_prcs(_f_raw_done, _f_raw)
			_f_qc = self._apnd_prcs(_f_qc_done, _f_qc)

		_f_qc = self._outlier_prcs(_f_qc)

		# save
		self._save_dt(_f_raw, _f_qc)

		# process time index
		# if (_start is not None)|(_end is not None):
		_f_raw, _start_raw, _end_raw = self._tmidx_process(_start, _end, _f_raw)
		_f_qc, _start_raw, _end_raw = self._tmidx_process(_start, _end, _f_qc)

		self._rate_calculate(_f_raw, _f_qc, _start_raw, _end_raw)

		return _f_qc if self.qc else _f_raw

	# -------------------------------------------------------------------------------------
	# old flow
	# def __run(self, _start, _end):
	#
	#     ## read pickle if pickle file exists and 'reset=False' or process raw data
	#     if (self.path / self.pkl_nam in list(self.path.glob('*.pkl'))) & (~self.reset):
	#         print(f"\n\t{dtm.now().strftime('%m/%d %X')} : Reading \033[96mPICKLE\033[0m file of {self.nam}")
	#
	#         with (self.path / self.pkl_nam).open('rb') as f:
	#             _fout_qc = pkl.load(f)
	#
	#         _exist = (self.path / self.pkl_nam_raw).exists()
	#         if _exist:
	#             with (self.path / self.pkl_nam_raw).open('rb') as f:
	#                 _fout_raw = pkl.load(f)
	#         else:
	#             _fout_raw = _fout_qc
	#
	#         _start, _end = to_datetime(_start) or _fout_qc.index[0], to_datetime(_end) or _fout_qc.index[-1]
	#         _idx = date_range(_start, _end, freq=_fout_qc.index.freq.copy())
	#         _idx.name = 'time'
	#
	#         _fout_raw, _fout_qc = _fout_raw.reindex(_idx), _fout_qc.reindex(_idx)
	#         if (self.rate) & (_exist):
	#             self._rate_calculate(_fout_raw, _fout_qc)
	#
	#         return _fout_qc if self.qc else _fout_raw
	#     else:
	#         print(
	#             f"\n\t{dtm.now().strftime('%m/%d %X')} : Reading \033[96mRAW DATA\033[0m of {self.nam} and process it")
	#
	#     ##=================================================================================================================
	#     ## read raw data
	#     _df_con, _f_list = None, list(self.path.glob(self.meta['pattern']))
	#
	#     if len(_f_list) == 0:
	#         print(f"\t\t\033[31mNo File in '{self.path}' Could Read, Please Check Out the Current Path\033[0m")
	#         return None
	#
	#     for file in _f_list:
	#         if file.name in [self.csv_out, self.csv_nam, self.csv_nam_raw, f'{self.nam}.log']: continue
	#
	#         print(f"\r\t\treading {file.name}", end='')
	#
	#         _df = self._raw_reader(file)
	#
	#         ## concat the concated list
	#         if _df is not None:
	#             _df_con = concat([_df_con, _df]) if _df_con is not None else _df
	#     print()
	#
	#     ## QC
	#     _save_raw = self._raw_process(_df_con)
	#     _save_qc = self._QC(_save_raw)
	#
	#     _start, _end = to_datetime(_start) or _save_raw.index[0], to_datetime(_end) or _save_raw.index[-1]
	#     _idx = date_range(_start, _end, freq=_save_raw.index.freq.copy())
	#     _idx.name = 'time'
	#
	#     _fout_raw, _fout_qc = _save_raw.reindex(_idx).copy(), _save_qc.reindex(_idx).copy()
	#
	#     self._rate_calculate(_fout_raw, _fout_qc)
	#
	#     ##=================================================================================================================
	#     ## dump pickle file
	#     _check = True
	#     while _check:
	#
	#         try:
	#             with (self.path / self.pkl_nam).open('wb') as f:
	#                 pkl.dump(_save_qc, f, protocol=pkl.HIGHEST_PROTOCOL)
	#
	#             ## dump csv file
	#             if self.csv:
	#                 _save_qc.to_csv(self.path / self.csv_nam)
	#
	#             ## output raw data if qc file
	#             if self.meta['deter_key'] is not None:
	#                 with (self.path / self.pkl_nam_raw).open('wb') as f:
	#                     pkl.dump(_save_raw, f, protocol=pkl.HIGHEST_PROTOCOL)
	#
	#                 if self.csv:
	#                     _save_raw.to_csv(self.path / self.csv_nam_raw)
	#
	#                 return _fout_qc if self.qc else _fout_raw
	#
	#             _check = False
	#
	#         except PermissionError as _err:
	#             print('\n', _err)
	#             input('\t\t\33[41m Please Close The File And Press "Enter" \33[0m\n')
	#
	#     return _fout_qc
