# read meteorological data from google sheet


from pandas import read_csv, to_datetime

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
	nam = 'Table'

	def _raw_reader(self, _file):
		self.meta['freq'] = self._oth_set.get('data_freq') or self.meta['freq']

		with (_file).open('r', encoding='utf-8-sig', errors='ignore') as f:
			_df = read_csv(f, low_memory=False, index_col=0)

			_df.index = to_datetime(_df.index, errors='coerce', format=self._oth_set.get('date_format') or 'mixed')
			_df.index.name = 'time'

			_df.columns = _df.keys().str.strip(' ')

			_df = _df.loc[_df.index.dropna()].copy()

		return _df.loc[~_df.index.duplicated()]

	def _QC(self, _df):
		return _df
