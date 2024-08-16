import numpy as np
from scipy.optimize import curve_fit

__all__ = [
	'_SAE',
]


def _SAE(df):
	def _SAEcalc(_df):
		## parameter
		band = np.array([450, 550, 700]) * 1e-3

		## 3 pts fitting
		## function
		def _get_slope(__df):
			func = lambda _x, _sl, _int: _sl * _x + _int
			popt, pcov = curve_fit(func, np.log(band), np.log(__df))

			return popt

		## calculate
		_SAE = _df.apply(_get_slope, axis=1, result_type='expand')
		_SAE.columns = ['slope', 'intercept']

		return _SAE

	df_out = _SAEcalc(df[['B', 'G', 'R']].dropna())

	return df_out.reindex(df.index)
