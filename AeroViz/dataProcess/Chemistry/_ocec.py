import warnings

import numpy as np
from pandas import concat, DataFrame
from scipy.optimize import curve_fit, least_squares, OptimizeWarning

from AeroViz.dataProcess.core import union_index

__all__ = [
    '_basic',
    # '_ocec_ratio_cal',
]


def _min_Rsq(_oc, _ec, _rng):
    _val_mesh, _oc_mesh = np.meshgrid(_rng, _oc)
    _val_mesh, _ec_mesh = np.meshgrid(_rng, _ec)

    _out_table = DataFrame(_oc_mesh - _val_mesh * _ec_mesh, index=_oc.index, columns=_rng)

    # calculate R2
    _r2_dic = {}
    _func = lambda _x, _sl, _inte: _sl * _x + _inte
    for _ocec, _out in _out_table.items():
        _df = DataFrame([_out.values, _ec.values]).T.dropna()

        _x, _y = _df[0].values, _df[1].values

        # 初始參數估計
        slope_guess = (_y[-1] - _y[0]) / (_x[-1] - _x[0])
        intercept_guess = _y[0] - slope_guess * _x[0]

        try:
            with warnings.catch_warnings():
                warnings.filterwarnings('error')
                _opt, _ = curve_fit(_func, _x, _y, p0=[slope_guess, intercept_guess], maxfev=5000)
        except (RuntimeWarning, OptimizeWarning):
            # 如果 curve_fit 失敗，嘗試使用 least_squares
            residuals = lambda p: _func(_x, *p) - _y
            _opt = least_squares(residuals, [slope_guess, intercept_guess]).x

        _tss = np.sum((_y - np.mean(_y)) ** 2)
        _rss = np.sum((_y - _func(_x, *_opt)) ** 2)

        _r2_dic[round(_ocec, 3)] = 1 - _rss / _tss

    _ratio = DataFrame(_r2_dic, index=[0]).idxmin(axis=1).values[0]

    return _ratio, _out_table[_ratio]


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
    _df_bsc = _lcres[['OC1_raw', 'OC2_raw', 'OC3_raw', 'OC4_raw']] / _lcres['Sample_Volume'].to_frame().values.copy()
    _df_bsc.rename(columns={'OC1_raw': 'OC1', 'OC2_raw': 'OC2', 'OC3_raw': 'OC3', 'OC4_raw': 'OC4'}, inplace=True)

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
        if 'OC/EC' in _ky: continue
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
    _df_bsc = concat((_lcres, _df_bsc.copy()), axis=1)

    for _ky, _df in _df_ratio.items():
        _df_bsc[f'{_ky}_status'] = 'Normal'
        _df_bsc[f'{_ky}_status'] = _df_bsc[f'{_ky}_status'].mask(_df > 1, 'Warning')

    # out
    _out['ratio'] = _df_ratio
    _out['basic'] = _df_bsc

    return _out
