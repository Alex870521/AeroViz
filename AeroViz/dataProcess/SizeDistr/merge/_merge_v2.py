from datetime import datetime as dtm

import numpy as np
from pandas import DataFrame, to_datetime, concat
# from scipy.interpolate import interp1d
from scipy.interpolate import UnivariateSpline as unvpline, interp1d

from AeroViz.dataProcess.core import union_index
from ._core import powerlaw_shift_fit, _shift_residual_s2
from ._debug_plot import plot_overlap, plot_nsv  # noqa: F401 -- optional debug plots, callable from any version

__all__ = ['merge_SMPS_APS']


## Overlap fitting
## Create a fitting func. by smps data
## return : shift factor
def _overlap_fitting(_smps_ori, _aps_ori, _smps_lb, _aps_hb):
    print(f"\t\t{dtm.now().strftime('%m/%d %X')} : \033[92moverlap range fitting\033[0m")

    ## overlap fitting
    ## parmeter
    _dt_indx = _smps_ori.index

    ## overlap diameter data
    _aps = _aps_ori[_aps_ori.keys()[_aps_ori.keys() < _aps_hb]].copy()
    _smps = _smps_ori[_smps_ori.keys()[_smps_ori.keys() > _smps_lb]].copy()

    ## use SMPS data apply power law fitting
    ## y = Ax^B, A = e**coefa, B = coefb, x = logx, y = logy
    ## ref : http://mathworld.wolfram.com/LeastSquaresFittingPowerLaw.html
    ## power law fit to SMPS num conc at upper bins to log curve

    ## power-law fit (A, B) + implied mobility-equivalent APS diameters (shared core)
    _coeA, _coeB, _aps_shift_x = powerlaw_shift_fit(_smps, _aps)

    ## the least squares of diameter
    ## the shift factor which the cklosest to 1
    _shift_factor = (_aps_shift_x.keys()._data.astype(float) / _aps_shift_x)
    _shift_factor.columns = range(len(_aps_shift_x.keys()))

    _dropna_idx = _shift_factor.dropna(how='all').index.copy()

    ## use the target function to get the similar aps and smps bin
    ## S2 = sum( (smps_fit_line(dia) - aps(dia*shift_factor) )**2 )  (shared core kernel)
    ## assumption : the same diameter between smps and aps should get the same conc.
    ## here each candidate factor is per-timestamp (data-derived); v3/v4 use a fixed grid.
    _S2 = concat([_shift_residual_s2(_coeA, _coeB, _aps, _idx, _factor.to_frame().values)
                  for _idx, _factor in _shift_factor.items()], axis=1)

    _least_squ_idx = _S2.idxmin(axis=1).loc[_dropna_idx]

    _shift_factor_out = DataFrame(_shift_factor.loc[_dropna_idx].values[range(len(_dropna_idx)), _least_squ_idx.values],
                                  index=_dropna_idx).reindex(_dt_indx)

    return _shift_factor_out, (DataFrame(_coeA, index=_dt_indx), DataFrame(_coeB, index=_dt_indx))


## Remove big shift data ()
## Return : aps, smps, shift (without big shift data)
def _shift_data_process(_shift, density_range=(0.6, 2.6)):
    print(f"\t\t{dtm.now().strftime('%m/%d %X')} : \033[92mshift-data quality control\033[0m")

    # shift² == estimated effective density (g/cm³). Drop timestamps whose
    # density falls outside the plausible range — wider range = looser QC.
    _rho = _shift ** 2
    _rho_min, _rho_max = density_range
    _shift = _shift.mask((~np.isfinite(_shift)) | (_rho < _rho_min) | (_rho > _rho_max))

    return _shift


# return _smps.loc[~_big_shift], _aps.loc[~_big_shift], _shift[~_big_shift].reshape(-1,1)


## Create merge data
##  shift all smps bin and remove the aps bin which smaller than the latest old smps bin
## Return : merge bins, merge data, density
def _merge_data(_smps_ori, _aps_ori, _shift_ori, _smps_lb, _aps_hb, _coe, _shift_mode):
    print(f"\t\t{dtm.now().strftime('%m/%d %X')} : \033[92mcreate merge data : {_shift_mode}\033[0m")

    _ori_idx = _smps_ori.index
    _merge_idx = _smps_ori.loc[_aps_ori.dropna(how='all').index].dropna(how='all').index

    _corr_aps_cond = _aps_ori.keys() < 700
    _corr_aps_ky = _aps_ori.keys()[_corr_aps_cond]

    _uni_idx, _count = np.unique(np.hstack((_smps_ori.dropna(how='all').index, _aps_ori.dropna(how='all').index,
                                            _shift_ori.dropna(how='all').index)), return_counts=True)

    _merge_idx = to_datetime(np.unique(_uni_idx[_count == 3]))

    _smps, _aps, _shift = _smps_ori.loc[_merge_idx], _aps_ori.loc[_merge_idx], _shift_ori.loc[_merge_idx].values

    ## parameter
    _coeA, _coeB = _coe[0].loc[_merge_idx], _coe[1].loc[_merge_idx]
    _smps_key, _aps_key = _smps.keys()._data.astype(float), _aps.keys()._data.astype(float)

    _cntr = 1000
    _bin_lb = _smps_key[-1]

    ## make shift bins
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

    ## merge
    _merge_lst, _corr_lst = [], []
    for _bin_smps, _bin_aps, _dt_smps, _dt_aps, _sh in zip(_smps_bin, _aps_bin, _smps.values, _aps.values, _shift):
        ## keep complete smps bins and data
        ## remove the aps bin data lower than smps bin
        _condi = _bin_aps >= _bin_smps[-1]

        _merge_bin = np.hstack((_bin_smps, _bin_aps[_condi]))
        _merge_dt = np.hstack((_dt_smps, _dt_aps[_condi]))

        _merge_fit_loc = (_merge_bin < 1500) & (_merge_bin > _smps_lb)

        ## coeA and coeB
        _unvpl_fc = unvpline(np.log(_merge_bin[_merge_fit_loc]), np.log(_merge_dt[_merge_fit_loc]), s=50)
        _inte_fc = interp1d(_merge_bin, _merge_dt, kind='linear', fill_value='extrapolate')

        _merge_dt_fit = np.hstack((_inte_fc(_std_bin_inte1), np.exp(_unvpl_fc(np.log(_std_bin_merge))),
                                   _inte_fc(_std_bin_inte2)))

        _merge_lst.append(_merge_dt_fit)
        _corr_lst.append(interp1d(_std_bin, _merge_dt_fit)(_bin_aps[_corr_aps_cond]))

    _df_merge = DataFrame(_merge_lst, columns=_std_bin, index=_merge_idx)
    _df_merge = _df_merge.mask(_df_merge < 0)

    _df_corr = DataFrame(_corr_lst, columns=_corr_aps_ky, index=_merge_idx) / _aps_ori.loc[_merge_idx, _corr_aps_ky]

    ## process output df
    ## average, align with index
    def _out_df(*_df_arg, **_df_kwarg):
        _df = DataFrame(*_df_arg, **_df_kwarg).reindex(_ori_idx)
        _df.index.name = 'time'
        return _df

    return _out_df(_df_merge), _out_df(_shift_ori ** 2), _out_df(_df_corr)


def merge_SMPS_APS(df_smps, df_aps, aps_unit='um', smps_overlap_lowbound=500, aps_fit_highbound=1000,
                   density_range=(0.6, 2.6)):
    df_smps, df_aps = union_index(df_smps, df_aps)

    ## set to the same units
    smps, aps_ori = df_smps.copy(), df_aps.copy()
    smps.columns = smps.keys().to_numpy(float)
    aps_ori.columns = aps_ori.keys().to_numpy(float)

    if aps_unit == 'um':
        aps_ori.columns = aps_ori.keys() * 1e3

    den_lst, mer_lst = [], []
    aps_input = aps_ori.loc[:, aps_ori.keys() > 700].copy()

    for _count in range(2):

        ## shift infomation, calculate by powerlaw fitting
        shift, coe = _overlap_fitting(smps, aps_input, smps_overlap_lowbound, aps_fit_highbound)

        ## process data by shift infomation, and average data
        shift = _shift_data_process(shift, density_range)

        ## merge aps and smps
        merge_arg = (smps, aps_ori, shift, smps_overlap_lowbound, aps_fit_highbound, coe)
        merge_data_mob, density, _corr = _merge_data(*merge_arg, 'mobility')
        merge_data_aer, density, _ = _merge_data(*merge_arg, 'aerodynamic')
        density.columns = ['density']

        if _count == 0:
            corr = _corr.resample('1d').mean().reindex(smps.index).ffill()
            corr = corr.mask(corr < 1, 1)
            aps_ori.loc[:, corr.keys()] *= corr

            aps_input = aps_ori.copy()

    ## out — unified keys: 'data' (mobility) + 'data_aero' + 'density'
    out_dic = {
        'data': merge_data_mob,
        'data_aero': merge_data_aer,
        'density': density,
    }

    ## process data
    for _nam, _df in out_dic.items():
        out_dic[_nam] = _df.reindex(smps.index).copy()

    return out_dic
