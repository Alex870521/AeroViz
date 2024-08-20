from pandas import concat

# parameter
_mol_wg = {
    'SO42-': 96.06,
    'NO3-': 62.00,
    'Cl-': 35.4,

    'Ca2+': 40.078,
    'K+': 39.098,
    'Mg2+': 24.305,
    'Na+': 22.99,
    'NH4+': 18.04,
}


# ug -> umol
def _ug2umol(_df):
    _pt_ky = list(set(_df.keys()) & set(_mol_wg.keys()))
    _gas_ky = list(set(_df.keys()) - set(_mol_wg.keys()) - set(['temp', 'RH']))

    _par = (_df['temp'].to_frame() + 273.15) * .082

    _df_pt = concat([(_df[_ky] / _mol_wg[_ky]).copy() for _ky in _pt_ky], axis=1)
    _df_gas = _df[_gas_ky] / _par.values

    return concat([_df_pt, _df_gas], axis=1)
