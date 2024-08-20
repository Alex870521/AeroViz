import numpy as np
from pandas import concat

__all__ = ['_scaCoe']


def _scaCoe(df, instru, specified_band: list):
    from .Angstrom_exponent import get_Angstrom_exponent, get_species_wavelength
    band_Neph = np.array([450, 550, 700])
    band_Aurora = np.array([450, 525, 635])

    band = band_Neph if instru == 'Neph' else band_Aurora

    df_sca = df.copy().dropna()

    if instru == 'Neph':
        df_out = df_sca[['B']].copy()
        df_out.columns = [f'sca_{_band}' for _band in specified_band]
    else:
        df_out = df_sca.apply(get_species_wavelength, axis=1, result_type='expand', args=(specified_band,))
        df_out.columns = [f'sca_{_band}' for _band in specified_band]

    # calculate
    df_SAE = df[['B', 'G', 'R']].dropna().apply(get_Angstrom_exponent, axis=1, result_type='expand', args=(band,))
    df_SAE.columns = ['SAE', 'SAE_intercept']

    _df = concat([df_out, df_SAE['SAE']], axis=1)

    return _df.reindex(df.index)
