from pandas import to_datetime, read_csv

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
	nam = 'Aurora'

	def _raw_reader(self, _file):
		with (_file).open('r', encoding='utf-8-sig', errors='ignore') as f:
			_df = read_csv(f, low_memory=False, index_col=0)

			_df.index = to_datetime(_df.index, errors='coerce', format=self._oth_set.get('date_format') or 'mixed')
			_df.index.name = 'time'

			_df.columns = _df.keys().str.strip(' ')

			_df = _df.loc[
				_df.index.dropna(), ['0°σspB', '0°σspG', '0°σspR', '90°σspB', '90°σspG', '90°σspR', 'RH']].copy()
			_df.columns = ['B', 'G', 'R', 'BB', 'BG', 'BR', 'RH']

		return _df

	## QC data
	def _QC(self, _df):
		## remove negative value
		_df = _df.mask((_df <= 0).copy())

		## call by _QC function
		## QC data in 1 hr
		def _QC_func(_df_1hr):
			_df_ave = _df_1hr.mean()
			_df_std = _df_1hr.std()
			_df_lowb, _df_highb = _df_1hr < (_df_ave - _df_std * 1.5), _df_1hr > (_df_ave + _df_std * 1.5)

			return _df_1hr.mask(_df_lowb | _df_highb).copy()

		return _df.resample('1h', group_keys=False).apply(_QC_func)
