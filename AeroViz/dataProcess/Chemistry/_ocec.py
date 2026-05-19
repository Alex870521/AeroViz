import numpy as np
from pandas import concat, DataFrame

from AeroViz.dataProcess.core import union_index

__all__ = [
    '_basic',
    'find_mrs_ratio',
    # '_ocec_ratio_cal',
]


def find_mrs_ratio(oc, ec, ratio_grid):
    """
    Minimum-R-Squared (MRS) primary OC/EC ratio finder.

    Scans ``ratio_grid`` and returns the ratio that minimizes the squared
    Pearson correlation between SOC = OC − ratio·EC and EC, so the
    secondary fraction is most independent of the EC tracer for primary
    organic aerosol (Lim & Turpin, 2002).

    Parameters
    ----------
    oc, ec : pandas.Series
        Aligned organic-carbon and elemental-carbon time series. Rows
        where either is NaN, or EC ≤ 0, are dropped before the search.
    ratio_grid : array-like
        Candidate primary OC/EC ratios to evaluate.

    Returns
    -------
    best_ratio : float
        Candidate from ``ratio_grid`` minimizing R²(SOC, EC).
    soc : pandas.Series
        SOC = OC − best_ratio·EC computed on the *original* index (without
        the validity mask), unclipped — callers that want physical
        bounds (SOC ≥ 0) should clip the result themselves.

    Notes
    -----
    Pearson r² and the R² of a simple linear regression are
    mathematically equal, so this implementation uses ``np.corrcoef``
    rather than ``scipy.optimize.curve_fit`` — same answer, far faster
    over a dense grid.
    """
    valid = oc.notna() & ec.notna() & (ec > 0)
    oc_v = oc[valid]
    ec_v = ec[valid]

    min_r2 = np.inf
    best_ratio = ratio_grid[0]
    for ratio in ratio_grid:
        soc_trial = oc_v - ratio * ec_v
        if soc_trial.std() == 0:
            continue
        corr = np.corrcoef(soc_trial, ec_v)[0, 1]
        r2 = corr ** 2
        if r2 < min_r2:
            min_r2 = r2
            best_ratio = ratio

    return float(best_ratio), oc - best_ratio * ec


def _min_Rsq(_oc, _ec, _rng):
    """Backward-compatible wrapper around ``find_mrs_ratio``."""
    return find_mrs_ratio(_oc, _ec, _rng)


def _ocec_ratio_cal(_nam, _lcres_splt, _hr_lim, _range_, _wisoc_range_):
    # parameter
    _out = DataFrame(index=_lcres_splt.index)
    (_, _oc), (_, _ec) = _lcres_splt.items()
    # _oc, _ec = _lcres_splt['Thermal_OC'], _lcres_splt['Thermal_EC']

    # real data OC/EC
    _ocec_ratio_real = (_oc / _ec).quantile(.5)

    _out[f'OC/EC_real_{_nam}'] = _ocec_ratio_real
    _out[f'POC_real_{_nam}'] = _ocec_ratio_real * _ec
    _out[f'SOC_real_{_nam}'] = _oc - _out[f'POC_real_{_nam}']

    # the least R2 method
    # estimated OC/EC
    if len(_lcres_splt) <= _hr_lim:
        print(f"\t\t{_lcres_splt.index[0].strftime('%Y-%m-%d %X')} to {_lcres_splt.index[-1].strftime('%Y-%m-%d %X')}")
        print('\t\tPlease Modify the Values of "hour_limit" or Input Sufficient Amount of Data !!')

        _out[[f'OC/EC_{_nam}', f'POC_{_nam}', f'SOC_{_nam}', f'WISOC/OC_{_nam}', f'WSOC_{_nam}',
              f'WISOC_{_nam}']] = np.nan

        return _out

    if len(_lcres_splt.dropna()) == 0:
        _out[[f'OC/EC_{_nam}', f'POC_{_nam}', f'SOC_{_nam}', f'WISOC/OC_{_nam}', f'WSOC_{_nam}',
              f'WISOC_{_nam}']] = np.nan

        return _out

    # OC/EC
    _ocec_ratio = False
    _st, _ed, _stp = _range_

    for _ in range(2):
        if _ocec_ratio:
            _ocec_rng = np.arange(_ocec_ratio - _stp / 2, _ocec_ratio + _stp / 2, .01).round(3)
        else:
            _ocec_rng = np.arange(_st, _ed + _stp, _stp).round(3)

        _ocec_ratio, _soc = _min_Rsq(_oc, _ec, _ocec_rng)

    # WISOC
    _st, _ed, _stp = _wisoc_range_
    _wisoc_rng = (np.arange(_st, _ed + _stp, _stp) * _ocec_ratio).round(5)
    _wisoc_ratio, _wsoc = _min_Rsq(_oc, _ec, _wisoc_rng)

    # out
    _out[f'OC/EC_{_nam}'] = _ocec_ratio
    _out[f'SOC_{_nam}'] = _soc
    _out[f'POC_{_nam}'] = _oc - _out[f'SOC_{_nam}']
    _out[f'WISOC/OC_{_nam}'] = _wisoc_ratio
    _out[f'WSOC_{_nam}'] = _wsoc
    _out[f'WISOC_{_nam}'] = _oc - _out[f'WSOC_{_nam}']

    return _out[[f'OC/EC_{_nam}', f'POC_{_nam}', f'SOC_{_nam}', f'WISOC/OC_{_nam}', f'WSOC_{_nam}', f'WISOC_{_nam}',
                 f'OC/EC_real_{_nam}', f'POC_real_{_nam}', f'SOC_real_{_nam}']]


def _basic(_lcres, _mass, _ocec_ratio, _ocec_ratio_month, _hr_lim, _range, _wisoc_range):
    _lcres, _mass = union_index(_lcres, _mass)

    _out = {}

    # OC1, OC2, OC3, OC4, PC
    _df_bsc = _lcres[['OC1', 'OC2', 'OC3', 'OC4', 'PC']].copy()

    # SOC, POC, OC/EC
    if _ocec_ratio is not None:
        try:
            iter(_ocec_ratio)
        except TypeError:
            raise TypeError('"ocec_ratio" Only Accept a Single Value !!')

        _prcs_df = DataFrame(index=_df_bsc.index)
        _prcs_df['OC/EC'] = _ocec_ratio
        _prcs_df['POC'] = _ocec_ratio * _lcres['Thermal_EC']
        _prcs_df['SOC'] = _lcres['Thermal_OC'] - _prcs_df['POC']

    else:
        _df_lst = []
        for _, _df in _lcres.resample(f'{_ocec_ratio_month}MS', closed='left'):
            _thm_cal = _ocec_ratio_cal('thm', _df[['Thermal_OC', 'Thermal_EC']], _hr_lim, _range, _wisoc_range)
            _opt_cal = _ocec_ratio_cal('opt', _df[['Optical_OC', 'Optical_EC']], _hr_lim, _range, _wisoc_range)
            _df_lst.append(concat([_thm_cal, _opt_cal], axis=1))

        _prcs_df = concat(_df_lst)

    _df_bsc = concat((_df_bsc.copy(), _prcs_df), axis=1)

    # ratio
    _df_ratio = DataFrame(index=_df_bsc.index)

    for _ky, _val in _df_bsc.items():
        if 'OC/EC' in _ky:
            continue
        _df_ratio[f'{_ky}/Thermal_OC'] = _val / _lcres['Thermal_OC']
        _df_ratio[f'{_ky}/Optical_OC'] = _val / _lcres['Optical_OC']

    if _mass is not None:
        for _ky, _val in _df_bsc.items():
            _df_ratio[f'{_ky}/PM'] = _val / _mass

        _df_ratio[f'Thermal_OC/PM'] = _lcres['Thermal_OC'] / _mass
        _df_ratio[f'Thermal_EC/PM'] = _lcres['Thermal_EC'] / _mass

        _df_ratio[f'Optical_OC/PM'] = _lcres['Optical_OC'] / _mass
        _df_ratio[f'Optical_EC/PM'] = _lcres['Optical_EC'] / _mass

    # ratio status
    _df_bsc = concat((_lcres.loc[:, :'Sample_Volume'], _df_bsc.copy()), axis=1)

    for _ky, _df in _df_ratio.items():
        _df_bsc[f'{_ky}_status'] = 'Normal'
        _df_bsc[f'{_ky}_status'] = _df_bsc[f'{_ky}_status'].mask(_df > 1, 'Warning')

    # out
    _out['basic'] = _df_bsc
    _out['ratio'] = _df_ratio

    return _out
