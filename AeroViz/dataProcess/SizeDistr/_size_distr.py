__all__ = ['_basic']


def _geometric_prop(_dp, _prop):
    import numpy as n

    _prop_t = _prop.sum(axis=1)
    _prop_t = _prop_t.where(_prop_t > 0).copy()

    _dp = n.log(_dp)
    _gmd = (((_prop * _dp).sum(axis=1)) / _prop_t.copy())

    _dp_mesh, _gmd_mesh = n.meshgrid(_dp, _gmd)
    _gsd = ((((_dp_mesh - _gmd_mesh) ** 2) * _prop).sum(axis=1) / _prop_t.copy()) ** .5

    return _prop_t, _gmd.apply(n.exp), _gsd.apply(n.exp)


def _basic(df, hybrid, unit, bin_rg, input_type):
    import numpy as n
    from pandas import DataFrame

    ## get number conc. data and total, mode
    dN = df
    dN.columns = dN.keys().to_numpy(float)

    dN_ky = dN.keys()[(dN.keys() >= bin_rg[0]) & (dN.keys() <= bin_rg[-1])]
    dN = dN[dN_ky].copy()

    out_dic = {}
    ## diameter
    dp = dN.keys().to_numpy()
    if hybrid:
        dlog_dp = n.diff(n.log10(dp)).mean()
    else:
        dlog_dp = n.ones(dp.size)
        dlog_dp[:hybrid] = n.diff(n.log10(dp[:hybrid])).mean()
        dlog_dp[hybrid:] = n.diff(n.log10(dp[hybrid:])).mean()

    ## calculate normalize and non-normalize data
    if input_type == 'norm':
        out_dic['number'] = (dN * dlog_dp).copy()
        out_dic['number_norm'] = dN.copy()
    else:
        out_dic['number'] = dN.copy()
        out_dic['number_norm'] = (dN / dlog_dp).copy()

    out_dic['surface'] = out_dic['number'] * n.pi * dp ** 2
    out_dic['volume'] = out_dic['number'] * n.pi * (dp ** 3) / 6

    out_dic['surface_norm'] = out_dic['number_norm'] * n.pi * dp ** 2
    out_dic['volume_norm'] = out_dic['number_norm'] * n.pi * (dp ** 3) / 6

    ## size range mode process
    df_oth = DataFrame(index=dN.index)

    bound = n.array([(dp.min(), dp.max() + 1), (10, 25), (25, 100), (100, 1e3), (1e3, 2.5e3), ])
    if unit == 'um':
        bound[1:] /= 1e3

    for _tp_nam, _tp_dt in zip(['num', 'surf', 'vol'], [out_dic['number'], out_dic['surface'], out_dic['volume']]):

        for _md_nam, _range in zip(['all', 'Nucleation', 'Aitken', 'Accumulation', 'Coarse'], bound):

            _dia = dp[(dp >= _range[0]) & (dp < _range[-1])]
            if ~_dia.any(): continue

            _dt = _tp_dt[_dia].copy()

            df_oth[f'total_{_tp_nam}_{_md_nam}'], df_oth[f'GMD_{_tp_nam}_{_md_nam}'], df_oth[
                f'GSD_{_tp_nam}_{_md_nam}'] = _geometric_prop(_dia, _dt)
            df_oth[f'mode_{_tp_nam}_{_md_nam}'] = _dt.idxmax(axis=1)

    ## out
    out_dic['other'] = df_oth

    return out_dic

# old 20230113

# _dN = out_dic['number'][_dia].copy()
# df_oth[f'{_nam}_mode'] = _dN.idxmax(axis=1)
# df_oth[f'{_nam}_TNC']  = _dN.sum(axis=1,min_count=1)

## total, GMD and GSD
# df_oth['total'], df_oth['GMD'], df_oth['GSD'] = _geometric_prop(dp,out_dic['number'])
# df_oth['total_surf'], df_oth['GMD_surf'], df_oth['GSD_surf'] = _geometric_prop(dp,out_dic['surface'])
# df_oth['total_volume'], df_oth['GMD_volume'], df_oth['GSD_volume'] = _geometric_prop(dp,out_dic['volume'])

## mode
# df_oth['mode']  	   = out_dic['number'].idxmax(axis=1)
# df_oth['mode_surface'] = out_dic['surface'].idxmax(axis=1)
# df_oth['mode_volume']  = out_dic['volume'].idxmax(axis=1)
