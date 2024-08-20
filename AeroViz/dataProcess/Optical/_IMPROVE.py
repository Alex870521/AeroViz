from pathlib import Path

import numpy as np
from pandas import DataFrame, read_pickle

from AeroViz.dataProcess.core import union_index


def _revised(_df_mass, _df_RH):
    _df_mass, _df_RH = union_index(_df_mass, _df_RH)

    # fRH
    with (Path(__file__).parent / 'fRH.pkl').open('rb') as f:
        _fRH = read_pickle(f)
        _fRH.loc[np.nan] = np.nan

    def fRH(_RH):
        if _RH is not None:
            _RH = _RH.mask(_RH > 95, 95).round(0)
            return _fRH.loc[_RH].values.T

        return 1, 1, 1, 1

    # different mode
    # mass < 20 :
    # 				large = mass**2/20
    # 				small = mass-large
    # mass >= 20 :
    # 				large = mass
    # 				small = 0
    _df_mode = _df_mass[['AS', 'AN', 'OM']].copy()

    _df_mass[['L_AS', 'L_AN', 'L_OM']] = _df_mode.mask(_df_mode < 20, _df_mode ** 2 / 20)
    _df_mass[['S_AS', 'S_AN', 'S_OM']] = _df_mode.values - _df_mass[['L_AS', 'L_AN', 'L_OM']]

    # apply IMPROVE ccoe.
    def _ext_cal(_RH=None):

        _frh, _frhss, _frhs, _frhl = fRH(_RH)
        _df = DataFrame(index=_df_mass.index)

        _df['AS'] = 2.2 * _frhs * _df_mass['S_AS'] + 4.8 * _frhl * _df_mass['L_AS']
        _df['AN'] = 2.4 * _frhs * _df_mass['S_AN'] + 5.1 * _frhl * _df_mass['L_AN']
        _df['OM'] = 2.8 * _df_mass['S_OM'] + 6.1 * _frhl * _df_mass['L_OM']
        _df['Soil'] = _df_mass['Soil']
        _df['SS'] = 1.7 * _frhss * _df_mass['SS']
        _df['EC'] = 10 * _df_mass['EC']

        _df['total'] = _df.sum(axis=1)

        return _df.dropna().reindex(_df_mass.index)

    # calculate
    _out = {'dry': _ext_cal()}

    if _df_RH is not None:
        _out['wet'] = _ext_cal(_df_RH)

    return _out
