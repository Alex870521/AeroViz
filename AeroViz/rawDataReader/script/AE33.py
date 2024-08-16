from pandas import read_table

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
	nam = 'AE33'

	def _raw_reader(self, _file):
		_df = read_table(_file, parse_dates={'time': [0, 1]}, index_col='time',
						 delimiter=r'\s+', skiprows=5, usecols=range(67))
		_df.columns = _df.columns.str.strip(';')

		# remove data without Status=0, 128 (Not much filter tape), 256 (Not much filter tape)
		if not self._oth_set.get('ignore_err', False):
			_df = _df.where((_df['Status'] != 0) | (_df['Status'] != 128) | (_df['Status'] != 256)).copy()

		return _df[['BC1', 'BC2', 'BC3', 'BC4', 'BC5', 'BC6', 'BC7', 'Status']]

	def _QC(self, _df):
		# remove negative value
		_df = _df[['BC1', 'BC2', 'BC3', 'BC4', 'BC5', 'BC6', 'BC7']].mask((_df < 0).copy())

		# QC data in 5 min
		def _QC_func(df):
			_df_ave, _df_std = df.mean(), df.std()
			_df_lowb, _df_highb = df < (_df_ave - _df_std * 1.5), df > (_df_ave + _df_std * 1.5)

			return df.mask(_df_lowb | _df_highb).copy()

		return _df.resample('5min').apply(_QC_func).resample('1h').mean()
