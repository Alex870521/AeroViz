from pandas import DataFrame

from AeroViz.dataProcess.core import union_index


def _basic(df_sca, df_abs, df_mass, df_no2, df_temp):
    df_sca, df_abs, df_mass, df_no2, df_temp = union_index(df_sca, df_abs, df_mass, df_no2, df_temp)

    df_out = DataFrame()

    # abs and sca coe
    df_out['abs'] = df_abs['abs_550'].copy()
    df_out['sca'] = df_sca['sca_550'].copy()

    # extinction coe.
    df_out['ext'] = df_out['abs'] + df_out['sca']

    # SSA
    df_out['SSA'] = df_out['sca'] / df_out['ext']

    # SAE, AAE, eBC
    df_out['SAE'] = df_sca['SAE'].copy()
    df_out['AAE'] = df_abs['AAE'].copy()
    df_out['eBC'] = df_abs['eBC'].copy() / 1e3

    # MAE, MSE, MEE
    if df_mass is not None:
        df_out['MAE'] = df_out['abs'] / df_mass
        df_out['MSE'] = df_out['sca'] / df_mass
        df_out['MEE'] = df_out['MSE'] + df_out['MAE']

    # gas absorbtion
    if df_no2 is not None:
        df_out['abs_gas'] = df_no2 * .33

    if df_temp is not None:
        df_out['sca_gas'] = (11.4 * 293 / (273 + df_temp))

    if df_no2 is not None and df_temp is not None:
        df_out['ext_all'] = df_out['ext'] + df_out['abs_gas'] + df_out['sca_gas']

    return df_out
