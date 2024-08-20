from pathlib import Path
from subprocess import Popen, PIPE

import numpy as np
from pandas import concat, DataFrame, to_numeric, read_csv

from ._calculate import _ug2umol


def _basic(df_che, path_out, nam_lst):
    # parameter
    df_all = concat(df_che, axis=1)
    index = df_all.index.copy()
    df_all.columns = nam_lst

    df_umol = _ug2umol(df_all)

    # output
    # Na, SO4, NH3, NO3, Cl, Ca, K, Mg, RH, TEMP
    df_input = DataFrame(index=index)
    df_out = DataFrame(index=index)

    pth_input = path_out / '_temp_input.txt'
    pth_output = path_out / '_temp_input.dat'

    pth_input.unlink(missing_ok=True)
    pth_output.unlink(missing_ok=True)

    # header
    _header = 'Input units (0=umol/m3, 1=ug/m3)\n' + '0\n\n' + \
              'Problem type (0=forward, 1=reverse); Phase state (0=solid+liquid, 1=metastable)\n' + '0, 1\n\n' + \
              'NH4-SO4 system case\n'

    # software
    path_iso = Path(__file__).parent / 'isrpia2.exe'

    # make input file and output temp input (without index)
    # NH3
    df_input['NH3'] = df_umol['NH4+'].fillna(0).copy() + df_umol['NH3']

    # NO3
    df_input['NO3'] = df_umol['HNO3'].fillna(0).copy() + df_umol['NO3-']

    # Cl
    df_input['Cl'] = df_umol['HCl'].fillna(0).copy() + df_umol['Cl-']

    # temp, RH
    df_input['RH'] = df_all['RH'] / 100
    df_input['TEMP'] = df_all['temp'] + 273.15

    df_input[['Na', 'SO4', 'Ca', 'K', 'Mg']] = df_umol[['Na+', 'SO42-', 'Ca2+', 'K+', 'Mg2+']].copy()

    df_input = df_input[['Na', 'SO4', 'NH3', 'NO3', 'Cl', 'Ca', 'K', 'Mg', 'RH', 'TEMP']].fillna('-').copy()

    # output the input data
    df_input.to_csv(pth_input, index=False)
    with (pth_input).open('r+', encoding='utf-8', errors='ignore') as _f:
        _cont = _f.read()
        _f.seek(0)

        _f.write(_header)
        _f.write(_cont)

    # use ISOROPIA2
    run = Popen([path_iso], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    scrn_res, run_res = run.communicate(input=str(pth_input.resolve()).encode())

    # read dat file and transform to the normal name
    cond_idx = df_all[['SO42-', 'NH4+', 'NO3-']].dropna().index

    with pth_output.open('r', encoding='utf-8', errors='ignore') as f:
        df_res = read_csv(f, delimiter=r'\s+').apply(to_numeric, errors='coerce').set_index(index)

    df_out['H'] = df_res['HLIQ'] / (df_res['WATER'] / 1000)

    df_out.loc[cond_idx, 'pH'] = -np.log10(df_out['H'].loc[cond_idx])
    df_out['pH'] = df_out['pH'].where((df_all['RH'] <= 95) & (df_all['RH'] >= 20))

    cond_idx = df_out['pH'].dropna().index
    df_out.loc[cond_idx, 'ALWC'] = df_res['WATER'].loc[cond_idx]

    df_out[['NH3', 'HNO3', 'HCl', 'NH4+', 'NO3-', 'Cl-']] = df_res[
        ['GNH3', 'GHNO3', 'GHCL', 'NH4AER', 'NO3AER', 'CLAER']]

    # calculate partition
    # df_out['epls_NO3-'] = df_umol['NO3-'] / (df_umol['NO3-'] + df_umol['HNO3'])
    # df_out['epls_NH4+'] = df_umol['NH4+'] / (df_umol['NH4+'] + df_umol['NH3'])
    # df_out['epls_Cl-']  = df_umol['Cl-'] / (df_umol['Cl-'] + df_umol['HCl'])

    # remove _temp file (input and output)
    pth_input.unlink(missing_ok=True)
    pth_output.unlink(missing_ok=True)

    # output input and output
    out = {
        'input': df_input,
        'output': df_out,
    }

    return out
