# read meteorological data from google sheet


import numpy as np
from pandas import read_csv, concat, to_numeric

from AeroViz.rawDataReader.core import AbstractReader


class Reader(AbstractReader):
	nam = 'IGAC_ZM'

	def _raw_reader(self, _file):

		with (_file).open('r', encoding='utf-8-sig', errors='ignore') as f:
			_df = read_csv(f, parse_dates=[0], index_col=[0], na_values=['-']).apply(to_numeric, errors='coerce')

			_df.columns = _df.keys().str.strip(' ')
			_df.index.name = 'time'

		return _df.loc[_df.index.dropna()].loc[~_df.index.duplicated()]

	## QC data
	def _QC(self, _df):

		## QC parameter, function (MDL SE LE)
		_mdl = {
			'Na+': 0.06,
			'NH4+': 0.05,
			'K+': 0.05,
			'Mg2+': 0.12,
			'Ca2+': 0.07,
			'Cl-': 0.07,
			'NO2-': 0.05,
			'NO3-': 0.11,
			'SO42-': 0.08,
		}
		_mdl.update(self._oth_set.get('mdl', {}))

		def _se_le(_df_, _log=False):
			_df_ = np.log10(_df_) if _log else _df_

			_df_qua = _df_.quantile([.25, .75])
			_df_q1, _df_q3 = _df_qua.loc[.25].copy(), _df_qua.loc[.75].copy()
			_df_iqr = _df_q3 - _df_q1

			_se = concat([_df_q1 - 1.5 * _df_iqr] * len(_df_), axis=1).T.set_index(_df_.index)
			_le = concat([_df_q3 + 1.5 * _df_iqr] * len(_df_), axis=1).T.set_index(_df_.index)

			if _log:
				return 10 ** _se, 10 ** _le
			return _se, _le

		_cation, _anion, _main = ['Na+', 'NH4+', 'K+', 'Mg2+', 'Ca2+'], ['Cl-', 'NO2-', 'NO3-', 'SO42-', ], ['SO42-',
																											 'NO3-',
																											 'NH4+']

		_df_salt = _df[_mdl.keys()].copy()
		_df_pm = _df['PM2.5'].copy()

		## lower than PM2.5
		## conc. of main salt should be present at the same time (NH4+, SO42-, NO3-)
		_df_salt = _df_salt.mask(_df_salt.sum(axis=1, min_count=1) > _df_pm).dropna(subset=_main).copy()

		## mdl
		for (_key, _df_col), _mdl_val in zip(_df_salt.items(), _mdl.values()):
			_df_salt[_key] = _df_col.mask(_df_col < _mdl_val, _mdl_val / 2)

		## calculate SE LE
		## salt < LE
		_se, _le = _se_le(_df_salt, _log=True)
		_df_salt = _df_salt.mask(_df_salt > _le).copy()

		## C/A, A/C
		_rat_CA = (_df_salt[_cation].sum(axis=1) / _df_salt[_anion].sum(axis=1)).to_frame()
		_rat_AC = (1 / _rat_CA).copy()

		_se, _le = _se_le(_rat_CA, )
		_cond_CA = (_rat_CA < _le) & (_rat_CA > 0)

		_se, _le = _se_le(_rat_AC, )
		_cond_AC = (_rat_AC < _le) & (_rat_AC > 0)

		_df_salt = _df_salt.where((_cond_CA * _cond_AC)[0]).copy()

		## conc. of main salt > SE
		_se, _le = _se_le(_df_salt[_main], _log=True)
		_df_salt[_main] = _df_salt[_main].mask(_df_salt[_main] < _se).copy()

		return _df_salt.reindex(_df.index)
