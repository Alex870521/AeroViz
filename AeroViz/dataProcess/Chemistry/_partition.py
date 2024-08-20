from pandas import concat, DataFrame

from ._calculate import _ug2umol


def _basic(df_che, nam_lst):
    # parameter
    df_all = concat(df_che, axis=1)
    index = df_all.index.copy()
    df_all.columns = nam_lst

    df_umol = _ug2umol(df_all)

    # calculate
    df_out = DataFrame(index=df_umol.index)

    # df_out['NTR'] = df_umol['NH4+'] / (df_umol['NH4+'] + df_all['NH3'] / 22.4)
    df_out['NTR+'] = df_umol['NH4+'] / (df_umol['NH4+'] + df_umol['NH3'])

    df_out['NOR'] = df_umol['NO3-'] / (df_umol['NO3-'] + df_umol['NO2'])
    df_out['NOR_2'] = (df_umol['NO3-'] + df_umol['HNO3']) / (df_umol['NO3-'] + df_umol['NO2'] + df_umol['HNO3'])

    df_out['SOR'] = df_umol['SO42-'] / (df_umol['SO42-'] + df_umol['SO2'])

    df_out['epls_NO3-'] = df_umol['NO3-'] / (df_umol['NO3-'] + df_umol['HNO3'])
    df_out['epls_NH4+'] = df_umol['NH4+'] / (df_umol['NH4+'] + df_umol['NH3'])
    df_out['epls_SO42-'] = df_out['SOR']
    df_out['epls_Cl-'] = df_umol['Cl-'] / (df_umol['Cl-'] + df_umol['HCl'])

    return df_out
