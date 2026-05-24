# from ContainerHandle.dataProcess.config import _union_index

import warnings
from datetime import datetime as dtm
from functools import partial
from multiprocessing import Pool, cpu_count

import numpy as np
from pandas import DataFrame, concat

from ._core import powerlaw_shift_fit, _shift_residual_s2, _corr_with_dNdSdV, merge_data as _merge_data
from ._debug_plot import plot_overlap, plot_nsv  # noqa: F401 -- optional debug plots, callable from any version

warnings.filterwarnings("ignore")

__all__ = ['merge_SMPS_APS']


## Calculate S2
## 1. SMPS and APS power law fitting
## 2. shift factor from 0.5 ~ 3
## 3. calculate S2
## return : S2
# def _S2_calculate_dN(_smps, _aps):
def _powerlaw_fit_dN(_smps, _aps, _alg_type, density_range=(0.6, 2.6)):
    print(f"\t\t\t{dtm.now().strftime('%m/%d %X')} : \033[92moverlap range fitting : {_alg_type}\033[0m")

    ## overlap fitting
    ## parmeter
    _dt_indx = _smps.index

    ## use SMPS data apply power law fitting
    ## y = Ax^B, A = e**coefa, B = coefb, x = logx, y = logy
    ## ref : http://mathworld.wolfram.com/LeastSquaresFittingPowerLaw.html
    ## power law fit to SMPS num conc at upper bins to log curve

    ## power-law fit (A, B) + implied mobility-equivalent APS diameters (shared core)
    _coeA, _coeB, _aps_shift_x = powerlaw_shift_fit(_smps, _aps)

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
    _dia_table = DataFrame(np.full(_aps_shift_x.shape, _aps_shift_x.keys()),
                           columns=_aps_shift_x.keys(), index=_aps_shift_x.index)

    pool = Pool(cpu_count())

    _S2 = pool.starmap(partial(_shift_residual_s2, _coeA, _coeB, _aps), list(enumerate(_shift_val)))

    pool.close()
    pool.join()

    S2 = concat(_S2, axis=1)[np.arange(_shift_val.size)]
    # S2 /= S2.max(axis=1).to_frame().values

    shift_factor_dN = DataFrame(
        _shift_factor.loc[_dropna_idx].values[range(len(_dropna_idx)), S2.loc[_dropna_idx].idxmin(axis=1).values],
        index=_dropna_idx).reindex(_dt_indx).astype(float)

    # shift² == estimated effective density (g/cm³); drop out-of-range timestamps
    _rho_min, _rho_max = density_range
    shift_factor_dN = shift_factor_dN.mask((shift_factor_dN ** 2 < _rho_min) | (shift_factor_dN ** 2 > _rho_max))

    return shift_factor_dN


# _corr_fc / _corr_with_dNdSdV (dN/dS/dV correlation shift finder) moved to _core.py


# _merge_data (SMPS + shifted-APS blend) moved to _core.py


def _fitness_func(psd, rho, pm25):
    psd_pm25 = psd[psd.keys()[psd.keys().values <= 2500]] * np.diff(np.log10(psd.keys())).mean()
    rho_pm25 = pm25 / (psd_pm25 * np.pi * psd_pm25.keys().values ** 3 / 6 * 1e-9).sum(axis=1, min_count=1)

    return (rho['density'] - rho_pm25) ** 2


def merge_SMPS_APS(df_smps, df_aps, df_pm25, aps_unit='um', smps_overlap_lowbound=500, aps_fit_highbound=1000,
                   dndsdv_alg=True, density_range=(0.6, 2.6), times_range=(0.8, 1.25, .05)):
    # merge_data, merge_data_dn, merge_data_dsdv, merge_data_cor_dn, density, density_dn, density_dsdv, density_cor_dn = [DataFrame([np.nan])] * 8

    ## set to the same units
    smps, aps = df_smps.copy(), df_aps.copy()
    smps.columns = smps.keys().to_numpy(float)
    aps.columns = aps.keys().to_numpy(float)

    if aps_unit == 'um':
        aps.columns = aps.keys() * 1e3

    fitness_typ = dict(dn=[], cor_dn=[], dndsdv=[], cor_dndsdv=[])
    shift_typ = dict(dn=[], cor_dn=[], dndsdv=[], cor_dndsdv=[])
    oth_typ = dict()

    times_ary = np.arange(*times_range).round(4)
    # times_ary = np.arange(*(0.8, 0.9, .05)).round(4)

    for times in times_ary:

        print(f"\t\t{dtm.now().strftime('%m/%d %X')} : \033[92mSMPS times value : {times}\033[0m")

        aps_input = aps.copy()
        aps_over = aps_input.loc[:, (aps.keys() > 700) & (aps.keys() < 1000)].copy()

        smps_input = (smps * times).copy()
        smps_over = smps_input[smps.keys()[smps.keys() > 500]].copy()

        for _count in range(2):

            ## shift data calculate
            ## original
            if _count == 0:
                alg_type = 'dn'
                shift = _powerlaw_fit_dN(smps_over, aps_over, alg_type, density_range)

                if dndsdv_alg:
                    shift_dsdv = _corr_with_dNdSdV(smps_over, aps_over, 'dndsdv').mask(shift.isna())

            ## aps correct
            else:
                alg_type = 'cor_dndsdv'
                shift_cor = _powerlaw_fit_dN(smps_over, aps_over, 'cor_dn', density_range)

                if dndsdv_alg:
                    shift = _corr_with_dNdSdV(smps_over, aps_over, alg_type).mask(shift_cor.isna())

            ## merge aps and smps
            ## 1. power law fit (dn) -> return dn data and aps correct factor
            ## 2. correaltion with dn, ds, dv -> return corrected dn_ds_dv data
            if (alg_type == 'dn') | dndsdv_alg:
                merge_arg = (smps_input, aps_input, shift, smps_overlap_lowbound, aps_fit_highbound)

                merge_data, density, _corr = _merge_data(*merge_arg, 'mobility', _alg_type=alg_type)
                density.columns = ['density']

                fitness_typ[alg_type].append(_fitness_func(merge_data, density, df_pm25))
                shift_typ[alg_type].append(shift[0])

            ## without aps correct
            if _count == 0:
                ## merge aps and smps
                ## dn_ds_dv data
                if dndsdv_alg:
                    alg_type = 'dndsdv'
                    merge_arg = (smps_input, aps_input, shift_dsdv, smps_overlap_lowbound, aps_fit_highbound)

                    merge_data_dsdv, density_dsdv, _ = _merge_data(*merge_arg, 'mobility', _alg_type=alg_type)
                    density_dsdv.columns = ['density']

                    fitness_typ[alg_type].append(_fitness_func(merge_data_dsdv, density_dsdv, df_pm25))
                    shift_typ[alg_type].append(shift_dsdv[0])

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

                fitness_typ[alg_type].append(_fitness_func(merge_data_cor_dn, density_cor_dn, df_pm25))
                shift_typ[alg_type].append(shift_cor[0])

    ## get times value and shift value
    out_dic = {}
    for (_typ, _lst), (_typ, _shft) in zip(fitness_typ.items(), shift_typ.items()):
        oth_typ[_typ] = None
        if len(_lst) == 0: continue

        df_times_min = concat(_lst, axis=1, keys=range(len(_lst))).idxmin(axis=1).dropna().astype(int)
        df_shift = concat(_shft, axis=1, keys=times_ary.tolist()).loc[df_times_min.index].values[
            range(len(df_times_min.index)), df_times_min.values]

        oth_typ[_typ] = DataFrame(np.array([df_shift, times_ary[df_times_min.values]]).T,
                                  index=df_times_min.index, columns=['shift', 'times']).reindex(smps.index)

    ## re-calculate merge_data
    alg_type = ['dn', 'cor_dn', 'dndsdv', 'cor_dndsdv'] if dndsdv_alg else ['dn', 'cor_dn']

    out_dic = {}
    den_lst, times_lst = [], []
    for _typ in alg_type:
        print(f"\t\t{dtm.now().strftime('%m/%d %X')} : \033[92mre-caculate merge data with times: {_typ}\033[0m")
        typ = oth_typ[_typ]
        smps_input = smps.copy() * typ['times'].to_frame().values

        corr_typ = corr if 'cor' in _typ else 1
        aps_input = aps.copy()
        aps_input.loc[:, corr.keys()] *= corr_typ

        merge_arg = (smps_input, aps_input, typ['shift'].to_frame(), smps_overlap_lowbound, aps_fit_highbound)

        merge_data, density, _corr = _merge_data(*merge_arg, 'mobility', _alg_type=_typ)
        density.columns = ['density']

        out_dic[f'data_{_typ}'] = merge_data

        den_lst.append(density)
        times_lst.append(typ['times'])

    out_rho = concat(den_lst, axis=1)
    out_times = concat(times_lst, axis=1)
    out_rho.columns = alg_type
    out_times.columns = alg_type

    # breakpoint()

    ## out — unified keys: primary 'data' (= cor_dndsdv) + variant data_* + density + times
    if 'data_cor_dndsdv' in out_dic:
        out_dic = {'data': out_dic.pop('data_cor_dndsdv'), **out_dic}
    out_dic.update(dict(density=out_rho, times=out_times))

    # out_dic = {
    # 'data_cor_dndsdv' : merge_data,
    # 'data_dn'     : merge_data_dn,
    # 'data_dndsdv' : merge_data_dsdv,
    # 'data_cor_dn' : merge_data_cor_dn,

    # 'density' : out_rho,

    # 'data_all_aer' : merge_data_aer,

    # 'density_cor_dndsdv' : density,
    # 'density_dn'   		 : density_dn,
    # 'density_dndsdv'	 : density_dsdv,
    # 'density_cor_dn'	 : density_cor_dn,
    # }

    ## process data
    for _nam, _df in out_dic.items():
        out_dic[_nam] = _df.reindex(smps.index).copy()

    return out_dic
