from AeroViz.dataProcess.core import union_index
from ._core import _overlap_fitting, _shift_data_process, merge_data as _merge_data
from ._debug_plot import plot_overlap, plot_nsv  # noqa: F401 -- optional debug plots, callable from any version

__all__ = ['merge_SMPS_APS']


# _overlap_fitting / _shift_data_process / _merge_data moved to _core.py


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
