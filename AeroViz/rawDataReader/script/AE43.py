from pandas import read_csv

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
	nam = 'AE43'

	def _raw_reader(self, _file):
		_df = read_csv(_file, parse_dates={'time': ['StartTime']}, index_col='time')
		_df_id = _df['SetupID'].iloc[-1]

		# get last SetupID data
		_df = _df.groupby('SetupID').get_group(_df_id)[
			['BC1', 'BC2', 'BC3', 'BC4', 'BC5', 'BC6', 'BC7', 'Status']].copy()

		# remove data without Status=0
		_df = _df.where(_df['Status'] == 0).copy()

		return _df[['BC1', 'BC2', 'BC3', 'BC4', 'BC5', 'BC6', 'BC7']]

	# QC data
	def _QC(self, _df):
		# remove negative value
		_df = _df.mask((_df < 0).copy())

		# QC data in 5 min
		def _QC_func(df):
			_df_ave, _df_std = df.mean(), df.std()
			_df_lowb, _df_highb = df < (_df_ave - _df_std * 1.5), df > (_df_ave + _df_std * 1.5)

			return df.mask(_df_lowb | _df_highb).copy()

		return _df.resample('5min').apply(_QC_func).resample('1h').mean()
