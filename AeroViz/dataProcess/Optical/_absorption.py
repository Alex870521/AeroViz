def _absCoe(df, instru, specified_band: list):
    import numpy as np
    from pandas import concat
    from .Angstrom_exponent import get_Angstrom_exponent, get_species_wavelength

    band_AE33 = np.array([370, 470, 520, 590, 660, 880, 950])
    band_BC1054 = np.array([370, 430, 470, 525, 565, 590, 660, 700, 880, 950])

    MAE_AE33 = np.array([18.47, 14.54, 13.14, 11.58, 10.35, 7.77, 7.19]) * 1e-3
    MAE_BC1054 = np.array([18.48, 15.90, 14.55, 13.02, 12.10, 11.59, 10.36, 9.77, 7.77, 7.20]) * 1e-3

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

    _df = concat([df_out, df_AAE['AAE']], axis=1)
    return _df.reindex(df.index)
