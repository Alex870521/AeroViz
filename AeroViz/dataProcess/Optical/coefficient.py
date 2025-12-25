import numpy as np
import pandas as pd
from scipy.optimize import curve_fit


def _scaCoe(df, instru, specified_band: list):
    band_Neph = np.array([450, 550, 700])
    band_Aurora = np.array([450, 525, 635])

    band = band_Neph if instru == 'Neph' else band_Aurora

    df_sca = df.copy().dropna()

    if instru == 'Neph':
        df_out = df_sca[['G']].copy()
        df_out.columns = [f'sca_{_band}' for _band in specified_band]
    else:
        df_out = df_sca.apply(get_species_wavelength, axis=1, result_type='expand', args=(specified_band,))
        df_out.columns = [f'sca_{_band}' for _band in specified_band]

    # calculate
    df_SAE = df[['B', 'G', 'R']].dropna().apply(get_Angstrom_exponent, axis=1, result_type='expand', args=(band,))
    df_SAE.columns = ['SAE', 'SAE_intercept']

    _df = pd.concat([df_out, df_SAE['SAE']], axis=1)

    return _df.reindex(df.index)


def _absCoe(df, instru, specified_band: list):
    band_AE33 = np.array([370, 470, 520, 590, 660, 880, 950])
    band_BC1054 = np.array([370, 430, 470, 525, 565, 590, 660, 700, 880, 950])
    band_MA350 = np.array([375, 470, 528, 625, 880])

    MAE_AE33 = np.array([18.47, 14.54, 13.14, 11.58, 10.35, 7.77, 7.19]) * 1e-3
    MAE_BC1054 = np.array([18.48, 15.90, 14.55, 13.02, 12.10, 11.59, 10.36, 9.77, 7.77, 7.20]) * 1e-3
    MAE_MA350 = np.array([24.069, 19.070, 17.028, 14.091, 10.120]) * 1e-3

    band = band_AE33 if instru == 'AE33' else band_BC1054
    MAE = MAE_AE33 if instru == 'AE33' else MAE_BC1054
    eBC = 'BC6' if instru == 'AE33' else 'BC9'

    # calculate
    df_abs = (df.copy().dropna() * MAE).copy()

    df_out = df_abs.apply(get_species_wavelength, axis=1, result_type='expand', args=(specified_band,))
    df_out.columns = [f'abs_{_band}' for _band in specified_band]
    df_out['eBC'] = df[eBC]

    df_AAE = df_abs.apply(get_Angstrom_exponent, axis=1, result_type='expand', args=(band,))
    df_AAE.columns = ['AAE', 'AAE_intercept']
    df_AAE = df_AAE.mask((-df_AAE['AAE'] < 0.8) | (-df_AAE['AAE'] > 2.)).copy()

    _df = pd.concat([df_out, df_AAE['AAE']], axis=1)
    return _df.reindex(df.index)


def get_species_wavelength(df, specified_band):
    func = lambda wavelength, _sl, _int: _sl * wavelength + _int
    popt, pcov = curve_fit(func, specified_band, df.values)

    return func(np.array(specified_band), *popt)


def get_Angstrom_exponent(df, band):
    if (df <= 0).any():
        return pd.Series([np.nan, np.nan], index=['slope', 'intercept'])  # 返回包含 NaN 的 Series，保持 DataFrame 结构

    func = lambda wavelength, _sl, _int: _sl * wavelength + _int
    popt, _ = curve_fit(func, np.log(band), np.log(df))

    return pd.Series(popt, index=['slope', 'intercept'])  # 返回带有索引的 Series
