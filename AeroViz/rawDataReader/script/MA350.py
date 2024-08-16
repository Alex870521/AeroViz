from pandas import read_csv

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
	nam = 'MA350'

	def _raw_reader(self, _file):
		_df = read_csv(_file, parse_dates=['Date / time local'], index_col='Date / time local').rename_axis("Time")

		_df = _df.rename(columns={
			'UV BCc': 'BC1',
			'Blue BCc': 'BC2',
			'Green BCc': 'BC3',
			'Red BCc': 'BC4',
			'IR BCc': 'BC5',
			'Biomass BCc  (ng/m^3)': 'BB mass',
			'Fossil fuel BCc  (ng/m^3)': 'FF mass',
			'Delta-C  (ng/m^3)': 'Delta-C',
			'AAE': 'AAE',
			'BB (%)': 'BB',
		})

		# remove data without Status=32 (Automatic Tape Advance), 65536 (Tape Move)
		# if not self._oth_set.get('ignore_err', False):
		#     _df = _df.where((_df['Status'] != 32) | (_df['Status'] != 65536)).copy()

		return _df[['BC1', 'BC2', 'BC3', 'BC4', 'BC5', 'BB mass', 'FF mass', 'Delta-C', 'AAE', 'BB']]

	# QC data
	def _QC(self, _df):
		# remove negative value
		_df = _df[['BC1', 'BC2', 'BC3', 'BC4', 'BC5', 'BB mass', 'FF mass', 'AAE', 'BB']].mask((_df < 0).copy())

		# call by _QC function
		# QC data in 1 hr
		def _QC_func(_df_1hr):
			_df_ave = _df_1hr.mean()
			_df_std = _df_1hr.std()
			_df_lowb, _df_highb = _df_1hr < (_df_ave - _df_std * 1.5), _df_1hr > (_df_ave + _df_std * 1.5)

			return _df_1hr.mask(_df_lowb | _df_highb).copy()

		return _df.resample('1h', group_keys=False).apply(_QC_func).resample('5min').mean()
