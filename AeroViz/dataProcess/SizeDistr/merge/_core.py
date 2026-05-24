"""Shared core math for the SMPS-APS merge algorithms (v1-v4).

These helpers were previously copy-pasted verbatim into individual version
files; they live here once so every version shares a single implementation:

* ``powerlaw_shift_fit`` — power-law fit of the SMPS overlap tail + the
  mobility-equivalent APS diameters it implies (used by all of v1-v4).
* ``_shift_residual_s2`` — per-shift-candidate S² kernel (v3/v4 grid search).
* ``_corr_fc`` / ``_corr_with_dNdSdV`` — dN/dS/dV correlation shift finder
  (v3/v4).
"""
from datetime import datetime as dtm
from functools import partial
from multiprocessing import Pool, cpu_count

import numpy as np
from pandas import DataFrame, concat, DatetimeIndex
from scipy.interpolate import UnivariateSpline as unvpline


def powerlaw_shift_fit(_smps, _aps):
    """Least-squares power-law fit of the SMPS overlap tail + implied APS shift.

    Both inputs must already be restricted to the overlap region (the caller
    decides the exact SMPS/APS diameter windows, which differ between versions).

    Fits ``y = A·x^B`` (dN/dlogDp vs Dp) per timestamp in log-log space, then
    maps each APS diameter to its mobility-equivalent via ``x = (y/A)^(1/B)``.

    Parameters
    ----------
    _smps, _aps : pandas.DataFrame
        Overlap-region SMPS and APS distributions (diameters as columns).

    Returns
    -------
    tuple
        ``(coeA, coeB, aps_shift_x)`` — ``coeA``/``coeB`` are per-timestamp
        column vectors ``(n_times, 1)``; ``aps_shift_x`` is the mobility-
        equivalent APS diameter frame (non-finite values masked to NaN).
    """
    _smps_qc_cond = ((_smps != 0) & np.isfinite(_smps))
    _smps_qc = _smps.where(_smps_qc_cond)

    _size = _smps_qc_cond.sum(axis=1)
    _size = _size.where(_size != 0.).copy()

    _logx, _logy = np.log(_smps_qc.keys()._data.astype(float)), np.log(_smps_qc)
    _x, _y, _xy, _xx = _logx.sum(), _logy.sum(axis=1), (_logx * _logy).sum(axis=1), (_logx ** 2).sum()

    _coeB = ((_size * _xy - _x * _y) / (_size * _xx - _x ** 2.))
    _coeA = np.exp((_y - _coeB * _x) / _size).values.reshape(-1, 1)
    _coeB = _coeB.values.reshape(-1, 1)

    _aps_shift_x = (_aps / _coeA) ** (1 / _coeB)
    _aps_shift_x = _aps_shift_x.where(np.isfinite(_aps_shift_x))

    return _coeA, _coeB, _aps_shift_x


def _shift_residual_s2(_coeA, _coeB, _aps, _idx, _factor):
    """S² between the power-law SMPS fit and APS for one shift candidate.

    Module-level so it stays picklable for the v3/v4 multiprocessing grid search.
    """
    _smps_fit_df = _coeA * (_aps.keys().values / _factor) ** _coeB
    return DataFrame(((_smps_fit_df.copy() - _aps.copy()) ** 2).sum(axis=1), columns=[_idx])


def _corr_fc(_aps_dia, _smps_dia, _smps_dn, _aps_dn, _smooth, _idx, _sh):
    """dN/dS/dV correlation score for one shift candidate (v3/v4)."""
    ds_fc = lambda _dt: _dt * _dt.index ** 2 * np.pi
    dv_fc = lambda _dt: _dt * _dt.index ** 3 * np.pi / 6

    _aps_sh = _aps_dia / _sh
    _aps_sh_inp = _aps_sh.where((_aps_sh >= 500) & (_aps_sh <= 1500.)).copy()
    _aps_sh_corr = _aps_sh.where((_aps_sh >= _smps_dia[-1]) & (_aps_sh <= 1500.)).copy()

    corr_x = np.append(_smps_dia, _aps_sh_corr.dropna())

    input_x = np.append(_smps_dia, _aps_sh_inp.dropna())
    input_y = concat([_smps_dn, _aps_dn.iloc[:, ~np.isnan(_aps_sh_inp)]], axis=1)
    input_y.columns = input_x

    input_x.sort()
    input_y = input_y[input_x]
    corr_y = input_y[corr_x]

    S2_lst = []
    for (_tm, _inp_y_dn), (_tm, _cor_y_dn) in zip(input_y.dropna(how='all').iterrows(),
                                                  corr_y.dropna(how='all').iterrows()):
        ## corr(spec_data, spec_spline)
        _spl_dt = [unvpline(input_x, _inp_y, s=_smooth)(corr_x) for _inp_y in
                   [_inp_y_dn, ds_fc(_inp_y_dn), dv_fc(_inp_y_dn)]]
        _cor_dt = [_cor_y_dn, ds_fc(_cor_y_dn), dv_fc(_cor_y_dn)]

        _cor_all = sum([np.corrcoef(_cor, _spl)[0, 1] for _cor, _spl in zip(_cor_dt, _spl_dt)])

        S2_lst.append((3 - _cor_all) / 3)

    return DataFrame(S2_lst, columns=[_idx])


def _corr_with_dNdSdV(_smps, _aps, _alg_type):
    """Find the per-timestamp shift maximising dN/dS/dV correlation (v3/v4)."""
    print(f"\t\t{dtm.now().strftime('%m/%d %X')} : \033[92moverlap range correlation : {_alg_type}\033[0m")

    _smps_dia = _smps.keys().astype(float)
    _aps_dia = _aps.keys().astype(float)

    all_index = _smps.index.copy()
    qc_index = DatetimeIndex(set(_smps.dropna(how='all').index) & set(_aps.dropna(how='all').index)).sort_values()

    _smps_dn = _smps.loc[qc_index].copy()
    _aps_dn = _aps.loc[qc_index].copy()

    ds_fc = lambda _dt: _dt * _dt.index ** 2 * np.pi
    dv_fc = lambda _dt: _dt * _dt.index ** 3 * np.pi / 6

    _std_bin = np.geomspace(11.8, 19810, 230)
    _merge_bin = _std_bin[(_std_bin >= _smps_dia[-1]) & (_std_bin < 1500)].copy()

    _smooth = 50

    _shift_val = np.arange(0.9, 2.65, .05) ** .5

    ## spline fitting with shift aps and smps
    pool = Pool(cpu_count())

    S2_lst = pool.starmap(partial(_corr_fc, _aps_dia, _smps_dia, _smps_dn, _aps_dn, _smooth),
                          list(enumerate(_shift_val)))

    pool.close()
    pool.join()

    S2_table = concat(S2_lst, axis=1).set_index(qc_index)[np.arange(_shift_val.size)].astype(float).dropna()
    min_shft = S2_table.idxmin(axis=1).values

    return DataFrame(_shift_val[min_shft.astype(int)], index=S2_table.index).astype(float).reindex(_smps.index)
