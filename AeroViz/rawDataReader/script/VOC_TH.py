# read meteorological data from google sheet


from pandas import read_csv

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
	nam = 'VOC_TH'

	def _raw_reader(self, _file):
		_keys = ['Isopentane', 'Hexane', '2-Methylhexane', '3-Methylhexane', '2-Methylheptane', '3-Methylheptane',
				 'Propene', '1.3-Butadiene', 'Isoprene', '1-Octene',
				 'Benzene', 'Toluene', 'Ethylbenzene', 'm.p-Xylene', 'o-Xylene', 'Iso-Propylbenzene', 'Styrene',
				 'n-Propylbenzene', '3.4-Ethyltoluene', '1.3.5-TMB', '2-Ethyltoluene', '1.2.4-TMB', '1.2.3-TMB',
				 'Acetaldehyde', 'Ethanol', 'Acetone', 'IPA', 'Ethyl Acetate', 'Butyl Acetate',
				 'VCM', 'TCE', 'PCE', '1.4-DCB', '1.2-DCB']

		with (_file).open('r', encoding='utf-8-sig', errors='ignore') as f:
			_df = read_csv(f, parse_dates=[0], index_col=[0], na_values=['-', 'N.D.'])

			_df.columns = _df.keys().str.strip(' ')
			_df.index.name = 'time'

			_df = _df[_keys].loc[_df.index.dropna()]
		return _df.loc[~_df.index.duplicated()]

	def _QC(self, _df):
		return _df
