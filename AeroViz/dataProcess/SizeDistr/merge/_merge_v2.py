from datetime import datetime as dtm

import numpy as np
from pandas import DataFrame, concat

from AeroViz.dataProcess.core import union_index
from ._core import powerlaw_shift_fit, _shift_residual_s2, merge_data as _merge_data
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


# _merge_data (SMPS + shifted-APS blend) moved to _core.py


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
        merge_arg = (smps, aps_ori, shift, smps_overlap_lowbound, aps_fit_highbound)
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
        out_dic[_nam] = _df.reindex(smps.index).rename_axis('time').copy()

    return out_dic
