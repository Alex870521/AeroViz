from datetime import datetime as dtm

import numpy as np
from pandas import DataFrame, to_datetime
# from scipy.interpolate import interp1d
from scipy.interpolate import UnivariateSpline as unvpline, interp1d

from AeroViz.dataProcess.core import union_index

__all__ = ['_merge_SMPS_APS']


def __test_plot(smpsx, smps, apsx, aps, mergex, merge, mergeox, mergeo, _sh):
    from matplotlib.pyplot import subplots, close, show

    ## parameter
    # '''
    ## plot
    fig, ax = subplots()

    ax.plot(smpsx, smps, c='#ff794c', label='smps', marker='o', lw=2)
    ax.plot(apsx, aps, c='#4c79ff', label='aps', marker='o', lw=2)
    ax.plot(mergex, merge, c='#79796a', label='merge')
    # ax.plot(mergeox,mergeo,c='#111111',label='mergeo',marker='o',lw=.75)

    ax.set(xscale='log', yscale='log', )

    ax.legend(framealpha=0, )
    ax.set_title((_sh ** 2)[0], fontsize=13)

    show()
    close()


# '''


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

    ## coefficient A, B
    _smps_qc_cond = ((_smps != 0) & np.isfinite(_smps))
    _smps_qc = _smps.where(_smps_qc_cond)

    _size = _smps_qc_cond.sum(axis=1)
    _size = _size.where(_size != 0.).copy()

    _logx, _logy = np.log(_smps_qc.keys()._data.astype(float)), np.log(_smps_qc)
    _x, _y, _xy, _xx = _logx.sum(), _logy.sum(axis=1), (_logx * _logy).sum(axis=1), (_logx ** 2).sum()

    _coeB = ((_size * _xy - _x * _y) / (_size * _xx - _x ** 2.))
    _coeA = np.exp((_y - _coeB * _x) / _size).values.reshape(-1, 1)
    _coeB = _coeB.values.reshape(-1, 1)

    ## rebuild shift smps data by coe. A, B
    ## x_shift = (y_ori/A)**(1/B)
    _aps_shift_x = (_aps / _coeA) ** (1 / _coeB)
    _aps_shift_x = _aps_shift_x.where(np.isfinite(_aps_shift_x))

    ## the least squares of diameter
    ## the shift factor which the cklosest to 1
    _shift_factor = (_aps_shift_x.keys()._data.astype(float) / _aps_shift_x)
    _shift_factor.columns = range(len(_aps_shift_x.keys()))

    _dropna_idx = _shift_factor.dropna(how='all').index.copy()

    ## use the target function to get the similar aps and smps bin
    ## S2 = sum( (smps_fit_line(dia) - aps(dia*shift_factor) )**2 )
    ## assumption : the same diameter between smps and aps should get the same conc.

    ## be sure they art in log value
    _S2 = DataFrame(index=_aps_shift_x.index)
    _dia_table = DataFrame(np.full(_aps_shift_x.shape, _aps_shift_x.keys()),
                           columns=_aps_shift_x.keys(), index=_aps_shift_x.index)
    for _idx, _factor in _shift_factor.items():
        _smps_fit_df = _coeA * (_dia_table / _factor.to_frame().values) ** _coeB
        _S2[_idx] = ((_smps_fit_df - _aps) ** 2).sum(axis=1)

    _least_squ_idx = _S2.idxmin(axis=1).loc[_dropna_idx]

    _shift_factor_out = DataFrame(_shift_factor.loc[_dropna_idx].values[range(len(_dropna_idx)), _least_squ_idx.values],
                                  index=_dropna_idx).reindex(_dt_indx)

    return _shift_factor_out, (DataFrame(_coeA, index=_dt_indx), DataFrame(_coeB, index=_dt_indx))


## Remove big shift data ()
## Return : aps, smps, shift (without big shift data)
def _shift_data_process(_shift):
    print(f"\t\t{dtm.now().strftime('%m/%d %X')} : \033[92mshift-data quality control\033[0m")

    _rho = _shift ** 2
    _shift = _shift.mask((~np.isfinite(_shift)) | (_rho > 2.6) | (_rho < 0.3))

    _qc_index = _shift.mask((_rho < 0.6) | (_shift.isna())).dropna().index

    return _qc_index, _shift


# return _smps.loc[~_big_shift], _aps.loc[~_big_shift], _shift[~_big_shift].reshape(-1,1)


## Create merge data
##  shift all smps bin and remove the aps bin which smaller than the latest old smps bin
## Return : merge bins, merge data, density
def _merge_data(_smps_ori, _aps_ori, _shift_ori, _shift_mode, _smps_lb, _aps_hb, _coe):
    print(f"\t\t{dtm.now().strftime('%m/%d %X')} : \033[92mcreate merge data\033[0m")

    _ori_idx = _smps_ori.index
    _merge_idx = _smps_ori.loc[_aps_ori.dropna(how='all').index].dropna(how='all').index

    _uni_idx, _count = np.unique(np.hstack((_smps_ori.dropna(how='all').index, _aps_ori.dropna(how='all').index,
                                            _shift_ori.dropna(how='all').index)), return_counts=True)

    _merge_idx = to_datetime(np.unique(_uni_idx[_count == 3]))

    _smps, _aps, _shift = _smps_ori.loc[_merge_idx], _aps_ori.loc[_merge_idx], _shift_ori.loc[_merge_idx].values

    ## parameter
    _coeA, _coeB = _coe[0].loc[_merge_idx], _coe[1].loc[_merge_idx]
    _smps_key, _aps_key = _smps.keys()._data.astype(float), _aps.keys()._data.astype(float)

    _test = 1000

    # _cntr = (_smps_lb+_aps_hb)/2
    _cntr = _test
    _bin_lb = _smps_key[-1]

    ## make shift bins
    _smps_bin = np.full(_smps.shape, _smps_key)
    _aps_bin = np.full(_aps.shape, _aps_key)
    # _std_bin  = _smps_key.tolist()+_aps_key[_aps_key>_smps_key[-1]].tolist()
    _std_bin = np.geomspace(_smps_key[0], _aps_key[-1], 230)
    _std_bin_merge = _std_bin[(_std_bin < _cntr) & (_std_bin > _bin_lb)]
    _std_bin_inte1 = _std_bin[_std_bin <= _bin_lb]
    _std_bin_inte2 = _std_bin[_std_bin >= _cntr]

    if _shift_mode == 'mobility':
        _aps_bin /= _shift

    elif _shift_mode == 'aerodynamic':
        _smps_bin *= _shift

    ## merge
    _merge_lst = []
    for _bin_smps, _bin_aps, _dt_smps, _dt_aps, _sh in zip(_smps_bin, _aps_bin, _smps.values, _aps.values, _shift):
        ## remove

        ## keep complete smps bins and data
        ## remove the aps bin data lower than smps bin
        _condi = _bin_aps >= _bin_smps[-1]

        _merge_bin = np.hstack((_bin_smps, _bin_aps[_condi]))
        _merge_dt = np.hstack((_dt_smps, _dt_aps[_condi]))

        # _merge_fit_loc = (_merge_bin<_aps_hb)&(_merge_bin>_smps_lb)
        _merge_fit_loc = (_merge_bin < 1500) & (_merge_bin > _smps_lb)

        ## coeA and coeB
        _unvpl_fc = unvpline(np.log(_merge_bin[_merge_fit_loc]), np.log(_merge_dt[_merge_fit_loc]), s=50)
        # _unvpl_fc = unvpline(_merge_bin[_merge_fit_loc],_merge_dt[_merge_fit_loc],s=150)
        # _inte_log_fc = interp1d(n.log10(_merge_bin[_merge_fit_loc]),n.log10(_merge_dt[_merge_fit_loc]),
        # kind='linear',fill_value='extrapolate')
        _inte_fc = interp1d(_merge_bin, _merge_dt, kind='linear', fill_value='extrapolate')

        __merge = np.exp(_unvpl_fc(np.log(_std_bin_merge)))
        # __merge = _unvpl_fc(_std_bin_merge)

        _merge_dt_fit = np.hstack((_inte_fc(_std_bin_inte1), __merge, _inte_fc(_std_bin_inte2)))
        # _merge_dt_fit = __merge
        # __test_plot(_bin_smps,_dt_smps,_bin_aps,_dt_aps,_std_bin,_merge_dt_fit,_merge_bin,_merge_dt,_sh)

        _merge_lst.append(_merge_dt_fit)

    _df_merge = DataFrame(_merge_lst, columns=_std_bin, index=_merge_idx)
    _df_merge = _df_merge.mask(_df_merge < 0)

    ## process output df
    ## average, align with index
    def _out_df(*_df_arg, **_df_kwarg):
        _df = DataFrame(*_df_arg, **_df_kwarg).reindex(_ori_idx)
        _df.index.name = 'time'
        return _df

    return _out_df(_df_merge), _out_df(_shift_ori ** 2)


## aps_fit_highbound : the diameter I choose randomly
def _merge_SMPS_APS(df_smps, df_aps, aps_unit, shift_mode, smps_overlap_lowbound, aps_fit_highbound):
    df_smps, df_aps = union_index(df_smps, df_aps)

    # print(f'\nMerge data :')
    # print(f' APS fittint higher diameter : {aps_fit_highbound:4d} nm')
    # print(f' SMPS overlap lower diameter : {smps_overlap_lowbound:4d} nm')
    # print(f' Average time                : {self.data_freq:>4s}\n')

    ## get data, remove 'total' and 'mode'
    ## set to the same units
    smps, aps = df_smps, df_aps
    smps.columns = smps.keys().to_numpy(float)
    aps.columns = aps.keys().to_numpy(float)

    if aps_unit == 'um':
        aps.columns = aps.keys() * 1e3

    ## shift infomation, calculate by powerlaw fitting
    shift, coe = _overlap_fitting(smps, aps, smps_overlap_lowbound, aps_fit_highbound)

    ## process data by shift infomation, and average data
    qc_cond, shift = _shift_data_process(shift)

    ## merge aps and smps..
    merge_data, density = _merge_data(smps, aps, shift, shift_mode, smps_overlap_lowbound, aps_fit_highbound, coe)
    density.columns = ['density']

    ## add total and mode
    # merge_total = merge_data.sum(axis=1,min_count=1).copy()
    # merge_mode  = merge_data.idxmax(axis=1).astype(float).copy()

    # merge_data['total'] = merge_total
    # merge_data['mode']  = merge_mode

    ## out
    out_dic = {
        'data_all': merge_data,
        'data_qc': merge_data.loc[qc_cond],
        'density_all': density,
        'density_qc': density.loc[qc_cond],
    }

    ## process data

    for _nam, _df in out_dic.items():
        out_dic[_nam] = _df.reindex(df_aps.index).copy()

    # merge_data = merge_data.reindex(df_aps.index)
    # density	   = density.reindex(df_aps.index)

    return out_dic
