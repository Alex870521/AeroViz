from pandas import to_datetime, read_csv

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
	nam = 'OCEC_RES'

	def _raw_reader(self, _file):
		with open(_file, 'r', encoding='utf-8', errors='ignore') as f:
			_df = read_csv(f, skiprows=3)

			_col = {'OCPk1-ug C': 'OC1',
					'OCPk2-ug C': 'OC2',
					'OCPk3-ug C': 'OC3',
					'OCPk4-ug C': 'OC4',
					'Pyrolized C ug': 'PC', }

			_tm_idx = to_datetime(_df['Start Date/Time'], errors='coerce')
			_df['time'] = _tm_idx

			_df = _df.dropna(subset='time').loc[~_tm_idx.duplicated()].set_index('time')

		return _df[_col.keys()].rename(columns=_col)

	## QC data
	def _QC(self, _df):
		return _df.where(_df > 0)
