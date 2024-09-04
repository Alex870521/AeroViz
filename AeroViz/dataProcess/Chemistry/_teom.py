def _basic(_teom, _check):
    import numpy as np
    _teom['Volatile_Fraction'] = (_teom['PM_Total'] - _teom['PM_NV']) / _teom['PM_Total']

    _teom.loc[(_teom['Volatile_Fraction'] < 0) | (_teom['Volatile_Fraction'] > 1)] = np.nan

    if _check is not None:
        _ratio = _teom['PM_NV'] / _check
        _teom['PM_Check'] = _check

        _teom.loc[_teom.dropna().index, 'status'] = 'Warning'
        _teom.loc[(_ratio > 0) & (_ratio < 1), 'status'] = 'Normal'

    return _teom
