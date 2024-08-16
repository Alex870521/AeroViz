from pandas import read_csv

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
	nam = 'BC1054'

	def _raw_reader(self, _file):
		with open(_file, 'r', encoding='utf-8', errors='ignore') as f:
			_df = read_csv(f, parse_dates=['Time'], index_col='Time')

			_df = _df.rename(columns={
				'BC1(ng/m3)': 'BC1',
				'BC2(ng/m3)': 'BC2',
				'BC3(ng/m3)': 'BC3',
				'BC4(ng/m3)': 'BC4',
				'BC5(ng/m3)': 'BC5',
				'BC6(ng/m3)': 'BC6',
				'BC7(ng/m3)': 'BC7',
				'BC8(ng/m3)': 'BC8',
				'BC9(ng/m3)': 'BC9',
				'BC10(ng/m3)': 'BC10'
			})

			# remove data without Status=32 (Automatic Tape Advance), 65536 (Tape Move)
			# if not self._oth_set.get('ignore_err', False):
			#     _df = _df.where((_df['Status'] != 32) | (_df['Status'] != 65536)).copy()

			return _df[['BC1', 'BC2', 'BC3', 'BC4', 'BC5', 'BC6', 'BC7', 'BC8', 'BC9', 'BC10', 'Status']]

	# QC data
	def _QC(self, _df):
		# remove negative value
		_df = _df[['BC1', 'BC2', 'BC3', 'BC4', 'BC5', 'BC6', 'BC7', 'BC8', 'BC9', 'BC10']].mask((_df < 0).copy())

		# call by _QC function
		# QC data in 1 hr
		def _QC_func(_df_1hr):
			_df_ave = _df_1hr.mean()
			_df_std = _df_1hr.std()
			_df_lowb, _df_highb = _df_1hr < (_df_ave - _df_std * 1.5), _df_1hr > (_df_ave + _df_std * 1.5)

			return _df_1hr.mask(_df_lowb | _df_highb).copy()

		return _df.resample('1h', group_keys=False).apply(_QC_func).resample('5min').mean()
