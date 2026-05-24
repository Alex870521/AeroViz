import warnings

from pandas import concat

from ._core import _powerlaw_fit_dN, _corr_with_dNdSdV, merge_data as _merge_data
from ._debug_plot import plot_overlap, plot_nsv  # noqa: F401 -- optional debug plots, callable from any version

warnings.filterwarnings("ignore")

__all__ = ['merge_SMPS_APS']


# _powerlaw_fit_dN (grid-search shift finder) moved to _core.py


# _corr_fc / _corr_with_dNdSdV (dN/dS/dV correlation shift finder) moved to _core.py


# _merge_data (SMPS + shifted-APS blend) moved to _core.py


def merge_SMPS_APS(df_smps, df_aps, aps_unit='um', smps_overlap_lowbound=500, aps_fit_highbound=1000,
                   dndsdv_alg=True, density_range=(0.6, 2.6)):
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
        'data': merge_data,  # primary = cor_dndsdv (APS-corrected dN/dS/dV)
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
