from pandas import to_datetime, read_csv

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
	nam = 'GRIMM'

	def _raw_reader(self, _file):

		_df = read_csv(_file, header=233, delimiter='\t', index_col=0, parse_dates=[0], encoding='ISO-8859-1',
					   dayfirst=True).rename_axis("Time")
		_df.index = to_datetime(_df.index, format="%d/%m/%Y %H:%M:%S", dayfirst=True)

		if _file.name.startswith("A407ST"):
			_df.drop(_df.columns[0:11].tolist() + _df.columns[128:].tolist(), axis=1, inplace=True)
		else:
			_df.drop(_df.columns[0:11].tolist() + _df.columns[-5:].tolist(), axis=1, inplace=True)

		if _df.empty:
			print(_file, "is empty")
			return None

		return _df / 0.035

	def _QC(self, _df):
		# QC data in 1 hr
		def _QC_func(_df_1hr):
			_df_ave = _df_1hr.mean()
			_df_std = _df_1hr.std()
			_df_lowb, _df_highb = _df_1hr < (_df_ave - _df_std * 1.5), _df_1hr > (_df_ave + _df_std * 1.5)

			return _df_1hr.mask(_df_lowb | _df_highb).copy()

		return _df.resample('5min').apply(_QC_func).resample('1h').mean()
