# read meteorological data from google sheet


from pandas import read_csv

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
	nam = 'VOC_ZM'

	def _raw_reader(self, _file):
		_keys = ['Ethane', 'Propane', 'Isobutane', 'n-Butane', 'Cyclopentane', 'Isopentane',
				 'n-Pentane', '2,2-Dimethylbutane', '2,3-Dimethylbutane', '2-Methylpentane',
				 '3-Methylpentane', 'n-Hexane', 'Methylcyclopentane', '2,4-Dimethylpentane',
				 'Cyclohexane', '2-Methylhexane', '2-Methylhexane', '3-Methylheptane',
				 '2,2,4-Trimethylpentane', 'n-Heptane', 'Methylcyclohexane',
				 '2,3,4-Trimethylpentane', '2-Methylheptane', '3-Methylhexane', 'n-Octane',
				 'n-Nonane', 'n-Decane', 'n-Undecane', 'Ethylene', 'Propylene', 't-2-Butene',
				 '1-Butene', 'cis-2-Butene', 't-2-Pentene', '1-Pentene', 'cis-2-Pentene',
				 'isoprene', 'Acetylene', 'Benzene', 'Toluene', 'Ethylbenzene', 'm,p-Xylene',
				 'Styrene', 'o-Xylene', 'Isopropylbenzene', 'n-Propylbenzene', 'm-Ethyltoluene',
				 'p-Ethyltoluene', '1,3,5-Trimethylbenzene', 'o-Ethyltoluene',
				 '1,2,4-Trimethylbenzene', '1,2,3-Trimethylbenzene', 'm-Diethylbenzene',
				 'p-Diethylbenzene']

		with (_file).open('r', encoding='utf-8-sig', errors='ignore') as f:
			_df = read_csv(f, parse_dates=[0], index_col=[0], na_values=['-'])

			_df.columns = _df.keys().str.strip(' ')
			_df.index.name = 'time'

			_df = _df[_keys].loc[_df.index.dropna()]
		return _df.loc[~_df.index.duplicated()]

	def _QC(self, _df):
		return _df
