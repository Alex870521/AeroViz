from AeroViz.dataProcess.core import union_index
from ._core import _overlap_fitting, _shift_data_process, merge_data as _merge_data
from ._debug_plot import plot_overlap, plot_nsv  # noqa: F401 -- optional debug plots, callable from any version

__all__ = ['_merge_SMPS_APS']


# _overlap_fitting / _shift_data_process / _merge_data moved to _core.py
# v1 uses with_corr=False (no APS correction / no _df_corr output).


## aps_fit_highbound : the diameter I choose randomly
def _merge_SMPS_APS(df_smps, df_aps, aps_unit, shift_mode, smps_overlap_lowbound, aps_fit_highbound,
                    density_range=(0.6, 2.6)):
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

    ## quality control by estimated effective density (shift²), then merge
    shift = _shift_data_process(shift, density_range)

    ## merge aps and smps..
    merge_data, density, _ = _merge_data(smps, aps, shift, smps_overlap_lowbound, aps_fit_highbound, shift_mode,
                                         with_corr=False)
    density.columns = ['density']

    ## out — unified keys: 'data' (merged dN/dlogDp) + 'density'
    out_dic = {
        'data': merge_data,
        'density': density,
    }

    for _nam, _df in out_dic.items():
        out_dic[_nam] = _df.reindex(df_aps.index).copy()

    return out_dic
