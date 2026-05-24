"""Shared core math for the SMPS-APS merge algorithms (v1-v4).

These helpers were previously copy-pasted verbatim into individual version
files; they live here once so every version shares a single implementation:

* ``powerlaw_shift_fit`` — power-law fit of the SMPS overlap tail + the
  mobility-equivalent APS diameters it implies (used by all of v1-v4).
* ``_shift_residual_s2`` — per-shift-candidate S² kernel (v3/v4 grid search).
* ``_corr_fc`` / ``_corr_with_dNdSdV`` — dN/dS/dV correlation shift finder
  (v3/v4).
* ``merge_data`` — blend SMPS + shifted APS onto a 230-bin log grid (all
  versions); ``with_corr`` toggles the APS correction factor output.
* ``_overlap_fitting`` / ``_shift_data_process`` — data-derived shift finder +
  effective-density QC used by v1/v2.
* ``_powerlaw_fit_dN`` — fixed-grid (parallel) shift finder used by v3/v4.
"""
from datetime import datetime as dtm
from functools import partial
from multiprocessing import Pool, cpu_count

import numpy as np
from pandas import DataFrame, concat, DatetimeIndex
from scipy.interpolate import UnivariateSpline as unvpline, interp1d


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


def merge_data(_smps_ori, _aps_ori, _shift_ori, _smps_lb, _aps_hb, _shift_mode='mobility',
               _alg_type='', *, with_corr=True):
    """Blend SMPS + shifted APS into one dN/dlogDp on a 230-bin log grid.

    Shared by every merge version. ``_shift_mode`` chooses which instrument is
    moved onto the other's diameter basis (``'mobility'`` shifts APS,
    ``'aerodynamic'`` shifts SMPS). Rows are computed only for timestamps present
    in SMPS, APS *and* a valid (non-NaN) shift, then reindexed back to the SMPS
    time axis (so QC-rejected timestamps become NaN).

    Parameters
    ----------
    _smps_ori, _aps_ori : pandas.DataFrame
        Full SMPS / APS distributions (diameters in nm as columns).
    _shift_ori : pandas.DataFrame
        Per-timestamp shift factor (NaN where QC-rejected).
    _smps_lb, _aps_hb : float
        Overlap-fit bounds (nm).
    _shift_mode : {'mobility', 'aerodynamic'}
    _alg_type : str
        Label for the log line only (e.g. 'cor_dndsdv'); no effect on output.
    with_corr : bool, keyword-only, default True
        If True, also return the APS correction factor (needed by the
        iterative-correction versions v2/v3/v4); v1 passes ``False``.

    Returns
    -------
    tuple
        ``(merge, density, corr)`` — each reindexed to the SMPS time axis;
        ``density`` is ``shift²`` (g/cm³); ``corr`` is ``None`` when
        ``with_corr=False``.
    """
    _tag = _shift_mode + (f" and {_alg_type}" if _alg_type else "")
    print(f"\t\t{dtm.now().strftime('%m/%d %X')} : \033[92mcreate merge data : {_tag}\033[0m")

    _ori_idx = _smps_ori.index

    _corr_aps_cond = _aps_ori.keys() < 700
    _corr_aps_ky = _aps_ori.keys()[_corr_aps_cond]

    # 3-way merge index: timestamps present in SMPS, APS and a valid shift.
    _merge_idx = (_smps_ori.dropna(how='all').index
                  .intersection(_aps_ori.dropna(how='all').index)
                  .intersection(_shift_ori.dropna(how='all').index))

    _smps, _aps, _shift = _smps_ori.loc[_merge_idx], _aps_ori.loc[_merge_idx], _shift_ori.loc[_merge_idx].values

    _smps_key, _aps_key = _smps.keys()._data.astype(float), _aps.keys()._data.astype(float)

    _cntr = 1000
    _bin_lb = _smps_key[-1]

    _smps_bin = np.full(_smps.shape, _smps_key)
    _aps_bin = np.full(_aps.shape, _aps_key)

    _std_bin = np.geomspace(_smps_key[0], _aps_key[-1], 230)
    _std_bin_merge = _std_bin[(_std_bin < _cntr) & (_std_bin > _bin_lb)]
    _std_bin_inte1 = _std_bin[_std_bin <= _bin_lb]
    _std_bin_inte2 = _std_bin[_std_bin >= _cntr]

    if _shift_mode == 'mobility':
        _aps_bin /= _shift
    elif _shift_mode == 'aerodynamic':
        _smps_bin *= _shift

    _merge_lst, _corr_lst = [], []
    for _bin_smps, _bin_aps, _dt_smps, _dt_aps, _sh in zip(_smps_bin, _aps_bin, _smps.values, _aps.values, _shift):
        ## keep complete smps bins; drop aps bins below the last smps bin
        _condi = _bin_aps >= _bin_smps[-1]

        _merge_bin = np.hstack((_bin_smps, _bin_aps[_condi]))
        _merge_dt = np.hstack((_dt_smps, _dt_aps[_condi]))

        _merge_fit_loc = (_merge_bin < 1500) & (_merge_bin > _smps_lb)

        _unvpl_fc = unvpline(np.log(_merge_bin[_merge_fit_loc]), np.log(_merge_dt[_merge_fit_loc]), s=50)
        _inte_fc = interp1d(_merge_bin, _merge_dt, kind='linear', fill_value='extrapolate')

        _merge_dt_fit = np.hstack((_inte_fc(_std_bin_inte1), np.exp(_unvpl_fc(np.log(_std_bin_merge))),
                                   _inte_fc(_std_bin_inte2)))

        _merge_lst.append(_merge_dt_fit)
        if with_corr:
            _corr_lst.append(interp1d(_std_bin, _merge_dt_fit)(_bin_aps[_corr_aps_cond]))

    _df_merge = DataFrame(_merge_lst, columns=_std_bin, index=_merge_idx)
    _df_merge = _df_merge.mask(_df_merge < 0)

    def _out_df(*_df_arg, **_df_kwarg):
        _df = DataFrame(*_df_arg, **_df_kwarg).reindex(_ori_idx)
        _df.index.name = 'time'
        return _df

    if with_corr:
        _df_corr = DataFrame(_corr_lst, columns=_corr_aps_ky, index=_merge_idx) / _aps_ori.loc[_merge_idx, _corr_aps_ky]
        return _out_df(_df_merge), _out_df(_shift_ori ** 2), _out_df(_df_corr)

    return _out_df(_df_merge), _out_df(_shift_ori ** 2), None


def _overlap_fitting(_smps_ori, _aps_ori, _smps_lb, _aps_hb):
    """Data-derived shift finder used by v1/v2 (family A).

    Power-law fits the SMPS tail, derives per-bin candidate shift factors from
    the data, and picks the one minimising S² against APS. (v3/v4 instead search
    a fixed shift grid via ``_powerlaw_fit_dN``.)

    Returns ``(shift_factor, (coeA, coeB))`` aligned to the SMPS time axis.
    """
    print(f"\t\t{dtm.now().strftime('%m/%d %X')} : \033[92moverlap range fitting\033[0m")

    _dt_indx = _smps_ori.index

    ## overlap diameter data
    _aps = _aps_ori[_aps_ori.keys()[_aps_ori.keys() < _aps_hb]].copy()
    _smps = _smps_ori[_smps_ori.keys()[_smps_ori.keys() > _smps_lb]].copy()

    ## power-law fit (A, B) + implied mobility-equivalent APS diameters
    _coeA, _coeB, _aps_shift_x = powerlaw_shift_fit(_smps, _aps)

    ## candidate shift factors derived per-bin from the data (vs v3/v4's grid)
    _shift_factor = (_aps_shift_x.keys()._data.astype(float) / _aps_shift_x)
    _shift_factor.columns = range(len(_aps_shift_x.keys()))

    _dropna_idx = _shift_factor.dropna(how='all').index.copy()

    ## S² per candidate (shared kernel); pick the argmin
    _S2 = concat([_shift_residual_s2(_coeA, _coeB, _aps, _idx, _factor.to_frame().values)
                  for _idx, _factor in _shift_factor.items()], axis=1)

    _least_squ_idx = _S2.idxmin(axis=1).loc[_dropna_idx]

    _shift_factor_out = DataFrame(_shift_factor.loc[_dropna_idx].values[range(len(_dropna_idx)), _least_squ_idx.values],
                                  index=_dropna_idx).reindex(_dt_indx)

    return _shift_factor_out, (DataFrame(_coeA, index=_dt_indx), DataFrame(_coeB, index=_dt_indx))


def _shift_data_process(_shift, density_range=(0.6, 2.6)):
    """Quality-control the shift factor by plausible effective density (v1/v2).

    ``shift² == effective density (g/cm³)``; timestamps whose density falls
    outside ``density_range`` (or are non-finite) are masked to NaN. Wider range
    = looser QC.
    """
    print(f"\t\t{dtm.now().strftime('%m/%d %X')} : \033[92mshift-data quality control\033[0m")

    _rho = _shift ** 2
    _rho_min, _rho_max = density_range
    _shift = _shift.mask((~np.isfinite(_shift)) | (_rho < _rho_min) | (_rho > _rho_max))

    return _shift


def _powerlaw_fit_dN(_smps, _aps, _alg_type, density_range=(0.6, 2.6)):
    """Grid-search shift finder used by v3/v4 (family B).

    Same power-law fit + S² objective as :func:`_overlap_fitting` (family A), but
    searches a FIXED density grid (0.3-3.0 g/cm³) in parallel instead of
    data-derived per-bin candidates, and applies the density-range QC inline.

    Returns the per-timestamp shift factor (NaN where QC-rejected).
    """
    print(f"\t\t{dtm.now().strftime('%m/%d %X')} : \033[92moverlap range fitting : {_alg_type}\033[0m")

    _dt_indx = _smps.index

    _coeA, _coeB, _aps_shift_x = powerlaw_shift_fit(_smps, _aps)

    ## fixed density grid of candidate shift factors (vs family A's data-derived)
    _shift_val = np.arange(0.3, 3.05, .05) ** .5

    _shift_factor = DataFrame(columns=range(_shift_val.size), index=_aps_shift_x.index)
    _shift_factor.loc[:, :] = _shift_val

    _dropna_idx = _aps_shift_x.dropna(how='all').index.copy()

    ## S² per candidate, evaluated in parallel
    pool = Pool(cpu_count())
    _S2 = pool.starmap(partial(_shift_residual_s2, _coeA, _coeB, _aps), list(enumerate(_shift_val)))
    pool.close()
    pool.join()

    S2 = concat(_S2, axis=1)[np.arange(_shift_val.size)]

    shift_factor_dN = DataFrame(
        _shift_factor.loc[_dropna_idx].values[range(len(_dropna_idx)), S2.loc[_dropna_idx].idxmin(axis=1).values],
        index=_dropna_idx).reindex(_dt_indx).astype(float)

    # shift² == estimated effective density (g/cm³); drop out-of-range timestamps
    _rho_min, _rho_max = density_range
    shift_factor_dN = shift_factor_dN.mask((shift_factor_dN ** 2 < _rho_min) | (shift_factor_dN ** 2 > _rho_max))

    return shift_factor_dN
