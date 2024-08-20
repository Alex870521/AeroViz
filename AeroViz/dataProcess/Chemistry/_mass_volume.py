from pandas import concat, DataFrame


def _basic(df_che, df_ref, df_water, df_density, nam_lst):

    df_all = concat(df_che, axis=1)
    index = df_all.index.copy()
    df_all.columns = nam_lst

    # parameter
    mol_A, mol_S, mol_N = df_all['NH4+'] / 18, df_all['SO42-'] / 96, df_all['NO3-'] / 62
    df_all['status'] = mol_A / (2 * mol_S + mol_N)

    convert_nam = {'AS': 'SO42-',
                   'AN': 'NO3-',
                   'OM': 'OC',
                   'Soil': 'Fe',
                   'SS': 'Na+',
                   'EC': 'EC',
                   }

    mass_coe = {'AS': 1.375,
                'AN': 1.29,
                'OM': 1.8,
                'Soil': 28.57,
                'SS': 2.54,
                'EC': 1,
                }

    vol_coe = {'AS': 1.76,
               'AN': 1.73,
               'OM': 1.4,
               'Soil': 2.6,
               'SS': 2.16,
               'EC': 1.5,
               }

    RI_coe = {'550': {'ALWC': 1.333 + 0j,
                      'AS': 1.53 + 0j,
                      'AN': 1.55 + 0j,
                      'OM': 1.55 + 0.0163j,
                      'Soil': 1.56 + 0.006j,
                      'SS': 1.54 + 0j,
                      'EC': 1.80 + 0.72j,
                      },

              # m + kj -> m value is same as 550 current
              '450': {'ALWC': 1.333 + 0j,
                      'AS': 1.57 + 0j,
                      'AN': 1.57 + 0j,
                      'OM': 1.58 + 0.056,
                      'Soil': 1.56 + 0.009j,
                      'SS': 1.54 + 0j,
                      'EC': 1.80 + 0.79j,
                      },
              }

    # mass
    # NH4 Enough
    df_mass = DataFrame()
    df_enough = df_all.where(df_all['status'] >= 1).dropna().copy()

    for _mass_nam, _coe in mass_coe.items():
        df_mass[_mass_nam] = df_all[convert_nam[_mass_nam]] * _coe

    # NH4 Deficiency
    defic_idx = df_all['status'] < 1

    if defic_idx.any():
        residual = mol_A - 2 * mol_S

        # residual > 0
        _status = residual > 0
        if _status.any():
            _cond = _status & (residual <= mol_N)
            df_mass.loc[_cond, 'AN'] = residual.loc[_cond] * 80

            _cond = _status & (residual > mol_N)
            df_mass.loc[_cond, 'AN'] = mol_N.loc[_cond] * 80

        # residual < 0
        _status = residual <= 0
        if _status.any():
            df_mass.loc[_status, 'AN'] = 0

            _cond = _status & (mol_A <= 2 * mol_S)
            df_mass.loc[_cond, 'AS'] = mol_A.loc[_cond] / 2 * 132

            _cond = _status & (mol_A > 2 * mol_S)
            df_mass.loc[_cond, 'AS'] = mol_S.loc[_cond] * 132

    df_mass_cal = df_mass.dropna().copy()
    df_mass['total'] = df_mass.sum(axis=1, min_count=6)

    qc_ratio = df_mass['total'] / df_ref
    qc_cond = (qc_ratio >= 0.5) & (qc_ratio <= 1.5)

    # volume
    df_vol = DataFrame()
    for _vol_nam, _coe in vol_coe.items():
        df_vol[_vol_nam] = df_mass_cal[_vol_nam] / _coe

    if df_water is not None:
        df_vol['ALWC'] = df_water.copy()
        df_vol = df_vol.dropna()
        df_vol['total_wet'] = df_vol.sum(axis=1, min_count=6)

    df_vol['total_dry'] = df_vol[vol_coe.keys()].sum(axis=1, min_count=6)

    # density
    df_vol_cal = DataFrame()
    df_den_rec = df_mass['total'] / df_vol['total_dry']
    if df_density is not None:
        df_den_all = concat([df_all[['SO42-', 'NO3-', 'NH4+', 'EC']], df_density, df_mass['OM']], axis=1).dropna()

        df_vol_cal = (df_den_all[['SO42-', 'NO3-', 'NH4+']].sum(axis=1) / 1.75) + \
                     df_den_all['Cl-'] / 1.52 + \
                     df_den_all['OM'] / 1.4 + df_den_all['EC'] / 1.77

        df_den = df_den_all.sum(axis=1, min_count=6) / df_vol_cal
    else:
        df_den = df_den_rec

    # refractive index
    ri_dic = {}
    for _lambda, _coe in RI_coe.items():

        df_RI = DataFrame()

        for _ky, _df in df_vol.items():
            if 'total' in _ky: continue
            df_RI[_ky] = (_df * _coe[_ky])

        df_RI['RI_wet'] = None
        if df_water is not None:
            df_RI['RI_wet'] = (df_RI / df_vol['total_wet'].to_frame().values).sum(axis=1)

        df_RI['RI_dry'] = (df_RI[vol_coe.keys()] / df_vol['total_dry'].to_frame().values).sum(axis=1)

        ri_dic[f'RI_{_lambda}'] = df_RI[['RI_dry', 'RI_wet']]

    # mole and equivalent
    df_eq = concat((mol_A, mol_S, mol_N, mol_A * 1, mol_S * 2, mol_N * 1), axis=1)
    df_eq.columns = ['mol_NH4', 'mol_SO4', 'mol_NO3', 'eq_NH4', 'eq_SO4', 'eq_NO3', ]

    # out
    out = {'mass': df_mass,
           'volume': df_vol,
           'vol_cal': df_vol_cal,
           'eq': df_eq,
           'density_mat': df_den,
           'density_rec': df_den_rec,
           }
    out.update(ri_dic)

    for _ky, _df in out.items():
        out[_ky] = _df.reindex(index)

    return out


def mass_ratio(_df):
    if _df['PM25'] >= _df['total_mass']:
        _df['others'] = _df['PM25'] - _df['total_mass']
        for _val, _species in zip(_df.values, _df.index):
            _df[f'{_species}_ratio'] = _val / _df['PM25'].__round__(3)

    if _df['PM25'] < _df['total_mass']:
        _df['others'] = 0
        for _val, _species in zip(_df.values, _df.index):
            _df[f'{_species}_ratio'] = _val / _df['PM25'].__round__(3)

    return _df['others':].drop(labels=['PM25_ratio', 'total_mass_ratio'])
