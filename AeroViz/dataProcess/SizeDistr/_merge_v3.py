# from ContainerHandle.dataProcess.config import _union_index

from datetime import datetime as dtm

import numpy as n
from pandas import DataFrame, concat, DatetimeIndex
# from scipy.interpolate import interp1d
from scipy.interpolate import UnivariateSpline as unvpline, interp1d

np = n
from multiprocessing import Pool, cpu_count
from functools import partial

import warnings

warnings.filterwarnings("ignore")

__all__ = [
    '_merge_SMPS_APS',

]


def _test_plot(ax, smps, aps, unp, shft):
    fs = 22.
    font_dic = dict(fontsize=fs, math_fontfamily='custom')

    ax.plot(smps, c='#2693ff', label='smps')
    ax.plot(aps, c='#ff4c4d', label='aps_ori')
    ax.plot(aps.index / shft, aps.values, c='#ff181b', label='aps_shft', ls='--')
    ax.plot(unp, c='#333333', label='unp')

    # ax.tick_params(which='major', length=7, labelsize=fs-2.5)
    # ax.tick_params(which='minor', length=4.5)
    # ax.spines[['right', 'top']].set_visible(False)
    ax.set(xlim=(11.8, 2500), xscale='log')


# ax.set_xlabel('', **font_dic)
# ax.set_ylabel('', **font_dic)

# ax.set_xticks(,**font_dic)
# ax.set_yticks(,**font_dic)

# ax.legend(handles=[], framealpha=0, fontsize=fs-2.)

# ax.set_title(shft, **font_dic)
# fig.suptitle('', fontsize=fs+2.)
# fig.savefig(/'.png')
# show()
# close()


def test_plot(smps, aps, unp, shft):
    from matplotlib.pyplot import subplots, show, rcParams

    ## parameter
    fs = 22.
    # font_fam = 'DejaVu Sans'
    font_fam = 'Times New Roman'
    rcParams['font.sans-serif'] = font_fam
    rcParams['mathtext.fontset'] = 'custom'
    font_dic = dict(fontsize=fs, math_fontfamily='custom')

    ## plot
    fig, axes = subplots(3, 1)

    ds_fc = lambda _dt: _dt * _dt.index ** 2 * np.pi
    dv_fc = lambda _dt: _dt * _dt.index ** 3 * np.pi / 6

    axes[0].set_title(shft, **font_dic)
    # axes[0].legend(framealpha=0, fontsize=fs * .6)

    _test_plot(axes[0], smps, aps, unp, shft)
    _test_plot(axes[1], ds_fc(smps), ds_fc(aps), ds_fc(unp), shft)
    _test_plot(axes[2], dv_fc(smps), dv_fc(aps), dv_fc(unp), shft)

    show()


def _powerlaw_fit(_coeA, _coeB, _aps, _idx, _factor):
    # breakpoint()

    _smps_fit_df = _coeA * (_aps.keys().values / _factor) ** _coeB
    return DataFrame(((_smps_fit_df.copy() - _aps.copy()) ** 2).sum(axis=1), columns=[_idx])


## Calculate S2
## 1. SMPS and APS power law fitting
## 2. shift factor from 0.5 ~ 3
## 3. calculate S2
## return : S2
# def _S2_calculate_dN(_smps, _aps):
def _powerlaw_fit_dN(_smps, _aps, _alg_type):
    print(f"\t\t{dtm.now().strftime('%m/%d %X')} : \033[92moverlap range fitting : {_alg_type}\033[0m")

    ## overlap fitting
    ## parmeter
    _dt_indx = _smps.index

    ## use SMPS data apply power law fitting
    ## y = Ax^B, A = e**coefa, B = coefb, x = logx, y = logy
    ## ref : http://mathworld.wolfram.com/LeastSquaresFittingPowerLaw.html
    ## power law fit to SMPS num conc at upper bins to log curve

    ## coefficient A, B
    _smps_qc_cond = ((_smps != 0) & np.isfinite(_smps))
    _smps_qc = _smps.where(_smps_qc_cond)

    _size = _smps_qc_cond.sum(axis=1)
    _size = _size.where(_size != 0.).copy()

    _logx, _logy = n.log(_smps_qc.keys()._data.astype(float)), n.log(_smps_qc)
    _x, _y, _xy, _xx = _logx.sum(), _logy.sum(axis=1), (_logx * _logy).sum(axis=1), (_logx ** 2).sum()

    _coeB = ((_size * _xy - _x * _y) / (_size * _xx - _x ** 2.))
    _coeA = n.exp((_y - _coeB * _x) / _size).values.reshape(-1, 1)
    _coeB = _coeB.values.reshape(-1, 1)

    ## rebuild shift smps data by coe. A, B
    ## x_shift = (y_ori/A)**(1/B)
    _aps_shift_x = (_aps / _coeA) ** (1 / _coeB)
    _aps_shift_x = _aps_shift_x.where(np.isfinite(_aps_shift_x))

    ## the least squares of diameter
    ## the shift factor which the closest to 1
    _shift_val = np.arange(0.3, 3.05, .05) ** .5
    # _shift_val = np.arange(0.9, 1.805, .005)**.5

    _shift_factor = DataFrame(columns=range(_shift_val.size), index=_aps_shift_x.index)
    _shift_factor.loc[:, :] = _shift_val

    # _dropna_idx = _shift_factor.dropna(how='all').index.copy()
    _dropna_idx = _aps_shift_x.dropna(how='all').index.copy()

    ## use the target function to get the similar aps and smps bin
    ## S2 = sum( (smps_fit_line(dia) - aps(dia*shift_factor) )**2 )
    ## assumption : the same diameter between smps and aps should get the same conc.

    ## be sure they art in log value
    _S2 = DataFrame(index=_aps_shift_x.index)
    _dia_table = DataFrame(n.full(_aps_shift_x.shape, _aps_shift_x.keys()),
                           columns=_aps_shift_x.keys(), index=_aps_shift_x.index)

    pool = Pool(cpu_count())

    _S2 = pool.starmap(partial(_powerlaw_fit, _coeA, _coeB, _aps), list(enumerate(_shift_val)))

    pool.close()
    pool.join()

    S2 = concat(_S2, axis=1)[np.arange(_shift_val.size)]
    # S2 /= S2.max(axis=1).to_frame().values

    shift_factor_dN = DataFrame(
        _shift_factor.loc[_dropna_idx].values[range(len(_dropna_idx)), S2.loc[_dropna_idx].idxmin(axis=1).values],
        index=_dropna_idx).reindex(_dt_indx).astype(float)

    shift_factor_dN = shift_factor_dN.mask((shift_factor_dN ** 2 < 0.6) | (shift_factor_dN ** 2 > 2.6))

    return shift_factor_dN


def _corr_fc(_aps_dia, _smps_dia, _smps_dn, _aps_dn, _smooth, _idx, _sh):
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


# def _S2_calculate_dSdV(_smps, _aps, _shft_dn, _S2, smps_ori, aps_ori):
# def _S2_calculate_dSdV(_smps, _aps, smps_ori=None):
def _corr_with_dNdSdV(_smps, _aps, _alg_type):
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

    _shift_val = np.arange(0.5, 2.605, .005) ** .5
    _shift_val = np.arange(0.9, 2.01, .01) ** .5
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


## Create merge data
##  shift all smps bin and remove the aps bin which smaller than the latest old smps bin
## Return : merge bins, merge data, density
def _merge_data(_smps_ori, _aps_ori, _shift_ori, _smps_lb, _aps_hb, _shift_mode, _alg_type):
    print(f"\t\t{dtm.now().strftime('%m/%d %X')} : \033[92mcreate merge data : {_shift_mode} and {_alg_type}\033[0m")

    _ori_idx = _smps_ori.index
    _merge_idx = _smps_ori.loc[_aps_ori.dropna(how='all').index].dropna(how='all').index

    _corr_aps_cond = _aps_ori.keys() < 700
    _corr_aps_ky = _aps_ori.keys()[_corr_aps_cond]

    _uni_idx = DatetimeIndex(set(_smps_ori.dropna(how='all').index) & set(_aps_ori.dropna(how='all').index) &
                             set(_shift_ori.dropna(how='all').index)).sort_values()

    _smps, _aps, _shift = _smps_ori.loc[_merge_idx], _aps_ori.loc[_merge_idx], _shift_ori.loc[_merge_idx].values

    ## parameter
    _smps_key, _aps_key = _smps.keys()._data.astype(float), _aps.keys()._data.astype(float)

    _cntr = 1000
    _bin_lb = _smps_key[-1]

    ## make shift bins
    _smps_bin = n.full(_smps.shape, _smps_key)
    _aps_bin = n.full(_aps.shape, _aps_key)

    _std_bin = n.geomspace(_smps_key[0], _aps_key[-1], 230)
    _std_bin_merge = _std_bin[(_std_bin < _cntr) & (_std_bin > _bin_lb)]
    _std_bin_inte1 = _std_bin[_std_bin <= _bin_lb]
    _std_bin_inte2 = _std_bin[_std_bin >= _cntr]
    # breakpoint()
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

        _merge_bin = n.hstack((_bin_smps, _bin_aps[_condi]))
        _merge_dt = n.hstack((_dt_smps, _dt_aps[_condi]))

        _merge_fit_loc = (_merge_bin < 1500) & (_merge_bin > _smps_lb)

        ## coeA and coeB
        _unvpl_fc = unvpline(n.log(_merge_bin[_merge_fit_loc]), n.log(_merge_dt[_merge_fit_loc]), s=50)
        _inte_fc = interp1d(_merge_bin, _merge_dt, kind='linear', fill_value='extrapolate')

        _merge_dt_fit = n.hstack((_inte_fc(_std_bin_inte1), n.exp(_unvpl_fc(n.log(_std_bin_merge))),
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


def merge_SMPS_APS(df_smps, df_aps, aps_unit='um', smps_overlap_lowbound=500, aps_fit_highbound=1000, dndsdv_alg=True):
    merge_data, merge_data_dn, merge_data_dsdv, merge_data_cor_dn, density, density_dn, density_dsdv, density_cor_dn = [
                                                                                                                           DataFrame(
                                                                                                                               [
                                                                                                                                   np.nan])] * 8

    ## set to the same units
    smps, aps_ori = df_smps.copy(), df_aps.copy()
    smps.columns = smps.keys().to_numpy(float)
    aps_ori.columns = aps_ori.keys().to_numpy(float)

    if aps_unit == 'um':
        aps_ori.columns = aps_ori.keys() * 1e3

    den_lst, mer_lst = [], []
    aps_input = aps_ori.loc[:, (aps_ori.keys() > 700) & (aps_ori.keys() < 1000)].copy()

    # aps_over  = aps[ aps.keys()[aps.keys() < 1000] ].copy()
    smps_over = smps[smps.keys()[smps.keys() > 500]].copy()

    for _count in range(2):

        ## shift data calculate
        if _count == 0:
            alg_type = 'dn'
            shift = _powerlaw_fit_dN(smps_over, aps_input)

            if dndsdv_alg:
                shift_dsdv = _corr_with_dNdSdV(smps_over, aps_input).mask(shift.isna())

        else:
            alg_type = 'cor_dndsdv'
            shift_cor = _powerlaw_fit_dN(smps_over, aps_input)

            if dndsdv_alg:
                shift = _corr_with_dNdSdV(smps_over, aps_input).mask(shift_cor.isna())

        ## merge aps and smps
        ## 1. power law fit (dn) -> return dn data and aps correct factor
        ## 2. correaltion with dn, ds, dv -> return corrected dn_ds_dv data
        if (alg_type == 'dn') | dndsdv_alg:
            merge_arg = (smps, aps_ori, shift, smps_overlap_lowbound, aps_fit_highbound)

            merge_data, density, _corr = _merge_data(*merge_arg, 'mobility', _alg_type=alg_type)
            density.columns = ['density']

        ## without aps correct
        if _count == 0:
            ## merge aps and smps
            ## dn_ds_dv data
            if dndsdv_alg:
                merge_arg = (smps, aps_ori, shift_dsdv, smps_overlap_lowbound, aps_fit_highbound)

                merge_data_dsdv, density_dsdv, _ = _merge_data(*merge_arg, 'mobility', _alg_type='dndsdv')
                density_dsdv.columns = ['density']

            ## dn data
            merge_data_dn, density_dn = merge_data.copy(), density.copy()

            ## correct aps data
            corr = _corr.resample('1d').mean().reindex(smps.index).ffill()
            corr = corr.mask(corr < 1, 1)
            aps_ori.loc[:, corr.keys()] *= corr

            aps_input = aps_ori.copy()

        ## with aps correct
        else:
            ## merge aps and smps
            ## dn data
            merge_arg = (smps, aps_ori, shift_cor, smps_overlap_lowbound, aps_fit_highbound)

            merge_data_cor_dn, density_cor_dn, _ = _merge_data(*merge_arg, 'mobility', _alg_type='cor_dn')
            density_cor_dn.columns = ['density']

    out_rho = concat([density_dn, density_cor_dn, density_dsdv, density], axis=1)
    out_rho.columns = ['dn', 'cor_dn', 'dndsdv', 'cor_dndsdv']

    ## out
    out_dic = {
        'data_cor_dndsdv': merge_data,
        'data_dn': merge_data_dn,
        'data_dndsdv': merge_data_dsdv,
        'data_cor_dn': merge_data_cor_dn,

        'density': out_rho,

        # 'data_all_aer' : merge_data_aer,

        # 'density_cor_dndsdv' : density,
        # 'density_dn'   		 : density_dn,
        # 'density_dndsdv'	 : density_dsdv,
        # 'density_cor_dn'	 : density_cor_dn,
    }

    ## process data
    for _nam, _df in out_dic.items():
        out_dic[_nam] = _df.reindex(smps.index).copy()

    return out_dic


def merge_SMPS_APS(df_smps, df_aps, aps_unit='um', smps_overlap_lowbound=500, aps_fit_highbound=1000, dndsdv_alg=True):
    # merge_data, merge_data_dn, merge_data_dsdv, merge_data_cor_dn, density, density_dn, density_dsdv, density_cor_dn = [DataFrame([np.nan])] * 8

    ## set to the same units
    smps, aps = df_smps.copy(), df_aps.copy()
    smps.columns = smps.keys().to_numpy(float)
    aps.columns = aps.keys().to_numpy(float)

    if aps_unit == 'um':
        aps.columns = aps.keys() * 1e3

    oth_typ = dict()

    aps_input = aps.copy()
    aps_over = aps_input.loc[:, (aps.keys() > 700) & (aps.keys() < 1000)].copy()

    smps_input = smps.copy()
    smps_over = smps_input[smps.keys()[smps.keys() > 500]].copy()

    for _count in range(2):

        ## shift data calculate
        ## original
        if _count == 0:
            alg_type = 'dn'
            shift = _powerlaw_fit_dN(smps_over, aps_over, alg_type)

            if dndsdv_alg:
                shift_dsdv = _corr_with_dNdSdV(smps_over, aps_over, 'dndsdv').mask(shift.isna())

        ## aps correct
        else:
            alg_type = 'cor_dndsdv'
            shift_cor = _powerlaw_fit_dN(smps_over, aps_over, 'cor_dn')

            if dndsdv_alg:
                shift = _corr_with_dNdSdV(smps_over, aps_over, alg_type).mask(shift_cor.isna())

        ## merge aps and smps
        ## 1. power law fit (dn) -> return dn data and aps correct factor
        ## 2. correaltion with dn, ds, dv -> return corrected dn_ds_dv data
        if (alg_type == 'dn') | dndsdv_alg:
            merge_arg = (smps_input, aps_input, shift, smps_overlap_lowbound, aps_fit_highbound)

            merge_data, density, _corr = _merge_data(*merge_arg, 'mobility', _alg_type=alg_type)
            density.columns = ['density']

        ## without aps correct
        if _count == 0:
            ## merge aps and smps
            ## dn_ds_dv data
            if dndsdv_alg:
                alg_type = 'dndsdv'
                merge_arg = (smps_input, aps_input, shift_dsdv, smps_overlap_lowbound, aps_fit_highbound)

                merge_data_dsdv, density_dsdv, _ = _merge_data(*merge_arg, 'mobility', _alg_type=alg_type)
                density_dsdv.columns = ['density']

            ## dn data
            merge_data_dn, density_dn = merge_data.copy(), density.copy()

            ## correct aps data
            corr = _corr.resample('1d').mean().reindex(smps.index).ffill()
            corr = corr.mask(corr < 1, 1)

            aps_input.loc[:, corr.keys()] *= corr
            aps_over = aps_input.copy()


        ## with aps correct
        else:
            ## merge aps and smps
            ## dn data
            alg_type = 'cor_dn'
            merge_arg = (smps_input, aps_input, shift_cor, smps_overlap_lowbound, aps_fit_highbound)

            merge_data_cor_dn, density_cor_dn, _ = _merge_data(*merge_arg, 'mobility', _alg_type=alg_type)
            density_cor_dn.columns = ['density']

    ## out
    out_rho = concat([density_dn, density_cor_dn, density_dsdv, density], axis=1)
    out_rho.columns = ['dn', 'cor_dn', 'dndsdv', 'cor_dndsdv']

    out_dic = {
        'data_cor_dndsdv': merge_data,
        'data_dn': merge_data_dn,
        'data_dndsdv': merge_data_dsdv,
        'data_cor_dn': merge_data_cor_dn,

        'density': out_rho,

        # 'data_all_aer' : merge_data_aer,

        # 'density_cor_dndsdv' : density,
        # 'density_dn'   		 : density_dn,
        # 'density_dndsdv'	 : density_dsdv,
        # 'density_cor_dn'	 : density_cor_dn,
    }

    ## process data
    for _nam, _df in out_dic.items():
        out_dic[_nam] = _df.reindex(smps.index).copy()

    return out_dic
