from AeroViz.dataProcess.core import _union_index
from pandas import DataFrame


def _basic(df_abs, df_sca, df_ec, df_mass, df_no2):
	df_abs, df_sca, df_ec, df_mass, df_no2 = _union_index(df_abs, df_sca, df_ec, df_mass, df_no2)

	df_out = DataFrame()

	## abs and sca coe
	df_out['abs'] = df_abs.copy()
	df_out['sca'] = df_sca.copy()

	## extinction coe.
	df_out['ext'] = df_out['abs'] + df_out['sca']

	## SSA
	df_out['SSA'] = df_out['sca'] / df_out['ext']

	## MAE, MSE, MEE
	if df_mass is not None:
		df_out['MAE'] = df_out['abs'] / df_mass
		df_out['MSE'] = df_out['sca'] / df_mass
		df_out['MEE'] = df_out['MSE'] + df_out['MAE']

	## gas absorbtion
	if df_no2 is not None:
		df_out['abs_gas'] = df_no2 * .33
		df_out['sca_gas'] = 10
		df_out['ext_all'] = df_out['ext'] + df_out['abs_gas'] + df_out['sca_gas']

	## other
	if df_ec is not None:
		df_out['eBC'] = df_ec / 1e3

	return df_out
