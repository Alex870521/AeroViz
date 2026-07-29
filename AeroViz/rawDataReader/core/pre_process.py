import numba
import numpy as np
import pandas as pd


@numba.jit(nopython=True)
def _angstrom_fit_numba(log_wavelengths, log_values):
    """
    Fast implementation of linear fit for Ångström exponent calculation using numba.

    Parameters
    ----------
    log_wavelengths : numpy.ndarray
        Log of wavelengths
    log_values : numpy.ndarray
        Log of measurement values

    Returns
    -------
    tuple
        Slope and intercept of the linear fit
    """
    n = len(log_wavelengths)
    sum_x = np.sum(log_wavelengths)
    sum_y = np.sum(log_values)
    sum_xy = np.sum(log_wavelengths * log_values)
    sum_xx = np.sum(log_wavelengths * log_wavelengths)

    # Calculate slope and intercept
    slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x)
    intercept = (sum_y - slope * sum_x) / n

    return slope, intercept


@numba.jit(nopython=True)
def calculate_bulk_angstrom_numba(abs_values, log_wavelengths):
    """
    JIT-compiled function to calculate Ångström exponents for multiple rows.

    Parameters
    ----------
    abs_values : numpy.ndarray
        2D array of absorption values [n_samples, n_wavelengths]
    log_wavelengths : numpy.ndarray
        Log of wavelengths

    Returns
    -------
    numpy.ndarray
        Array of [slope, intercept] pairs for each row
    """
    n_samples = abs_values.shape[0]
    results = np.empty((n_samples, 2))

    for i in range(n_samples):
        row = abs_values[i]

        # Skip rows with zero or negative values
        if np.any(row <= 0):
            results[i, 0] = np.nan
            results[i, 1] = np.nan
            continue

        log_values = np.log(row)
        results[i, 0], results[i, 1] = _angstrom_fit_numba(log_wavelengths, log_values)

    return results


def _angstrom_exponent(values, band):
    """
    Ångström exponent per row, in the positive sign convention.

    A log-log fit of X(λ) = K·λ^(-AE) has slope -AE, so the raw slope returned by
    ``calculate_bulk_angstrom_numba`` is negated here. AAE and SAE are reported as
    positive numbers throughout AeroViz (and in the literature), and that is also
    what ``calculate_specific_wavelengths_numba`` expects.

    Parameters
    ----------
    values : array_like
        2D array of measurements [n_samples, n_wavelengths]
    band : numpy.ndarray
        Wavelengths (nm) matching the columns of ``values``

    Returns
    -------
    numpy.ndarray
        Positive Ångström exponent per row (NaN where the fit is undefined)
    """
    fit = calculate_bulk_angstrom_numba(np.ascontiguousarray(values, dtype=np.float64), np.log(band))
    return -fit[:, 0]


@numba.jit(nopython=True)
def calculate_specific_wavelengths_numba(ref_values, ae_values, ratio_factor):
    """
    JIT-compiled function to calculate values at specific wavelengths using Ångström relation.

    Parameters
    ----------
    ref_values : numpy.ndarray
        Reference values at reference wavelength
    ae_values : numpy.ndarray
        Ångström exponent values (positive)
    ratio_factor : float
        Wavelength ratio factor (target_wl / ref_wl)

    Returns
    -------
    numpy.ndarray
        Calculated values at target wavelength

    Notes
    -----
    This function implements the Ångström power law relationship:
    X(λ₂) = X(λ₁) × (λ₂/λ₁)^(-AE)

    where:
    - X is either absorption or scattering coefficient
    - AE is the Ångström exponent (AAE for absorption, SAE for scattering)
    - The negative sign in the exponent reflects that both absorption and
      scattering coefficients typically decrease with increasing wavelength

    By convention, both AAE and SAE are reported as positive values in the literature,
    with the negative sign included in the formula. This function expects positive
    AE values and applies the negative sign internally.

    Typical values:
    - AAE: 1-2 for black carbon, higher for brown carbon and dust
    - SAE: 0-4, with ~4 for small particles and ~0 for large particles

    """
    n_samples = len(ref_values)
    results = np.empty(n_samples)

    for i in range(n_samples):
        if np.isnan(ae_values[i]):
            results[i] = np.nan
        else:
            # Note the negative sign to follow the Ångström relation
            results[i] = ref_values[i] * (ratio_factor ** -ae_values[i])

    return results


SCA_BANDS = {
    'NEPH': np.array([450, 550, 700]),  # TSI 3563
    'AURORA': np.array([450, 525, 635]),  # Ecotech Aurora 3000
}

SCA_CHANNELS = ['B', 'G', 'R']


def _scaCoe(df, instru, specified_band: list):
    """
    Calculate scattering coefficients and Ångström exponent for scattering.

    Parameters
    ----------
    df : pandas.DataFrame
        Data frame containing scattering measurements (needs columns B, G, R)
    instru : str
        Instrument type ('NEPH' or 'Aurora'), matched case-insensitively
    specified_band : list
        List of wavelengths to calculate scattering coefficients for

    Returns
    -------
    pandas.DataFrame
        Data frame with scattering coefficients and Ångström exponent.
        ``SAE`` is reported positive, following the usual convention.
    """
    key = str(instru).upper()
    if key not in SCA_BANDS:
        raise KeyError(f'Unknown nephelometer {instru!r}; expected one of {sorted(SCA_BANDS)}')
    band = SCA_BANDS[key]

    # Drop repeats while keeping order — a duplicated wavelength would otherwise
    # create duplicate columns and break the .loc assignments below
    target_bands = list(dict.fromkeys(specified_band))

    # Create mask for valid rows to avoid copying data
    mask = ~df[SCA_CHANNELS].isna().any(axis=1)

    # Pre-allocate output DataFrame
    result_columns = [f'sca_{wl}' for wl in target_bands] + ['SAE']
    result_df = pd.DataFrame(np.nan, index=df.index, columns=result_columns)

    # Exit early if no valid data
    if not mask.any():
        return pd.concat([df, result_df], axis=1)

    # SAE from a log-log fit over all three channels, positive by convention
    sae_values = _angstrom_exponent(df.loc[mask, SCA_CHANNELS].values, band)
    result_df.loc[mask, 'SAE'] = sae_values

    for wl in target_bands:
        exact = np.flatnonzero(band == wl)
        if exact.size:
            # Measured directly — use the channel as-is rather than round-tripping
            # it through the power law (which would also drop rows with no SAE)
            result_df.loc[mask, f'sca_{wl}'] = df.loc[mask, SCA_CHANNELS[exact[0]]].values
            continue

        # Extrapolate from the nearest channel: sca(λ₂) = sca(λ₁)·(λ₂/λ₁)^(-SAE)
        closest_idx = int(np.abs(band - wl).argmin())
        ref_values = df.loc[mask, SCA_CHANNELS[closest_idx]].values.astype(float)
        ratio = wl / band[closest_idx]
        result_df.loc[mask, f'sca_{wl}'] = calculate_specific_wavelengths_numba(
            ref_values, sae_values, ratio)

    # Combine with original data
    return pd.concat([df, result_df], axis=1)


def _absCoe(df, instru, specified_band: list):
    """
    Calculate absorption coefficients and Ångström exponent for absorption.

    Parameters
    ----------
    df : pandas.DataFrame
        Data frame containing black carbon measurements — exactly one column per
        instrument wavelength, in ascending-wavelength order
    instru : str
        Instrument type ('AE33', 'BC1054', or 'MA350')
    specified_band : list
        List of wavelengths to calculate absorption coefficients for

    Returns
    -------
    pandas.DataFrame
        Data frame with original data, absorption coefficients, coefficients at
        specified wavelengths, and Ångström exponent. ``AAE`` is reported
        positive, following the usual convention.
    """
    config = {
        'AE33': {
            'band': np.array([370, 470, 520, 590, 660, 880, 950]),
            'MAE': np.array([18.47, 14.54, 13.14, 11.58, 10.35, 7.77, 7.19]) * 1e-3,
            'eBC': 'BC6'
        },
        'BC1054': {
            'band': np.array([370, 430, 470, 525, 565, 590, 660, 700, 880, 950]),
            'MAE': np.array([18.48, 15.90, 14.55, 13.02, 12.10, 11.59, 10.36, 9.77, 7.77, 7.20]) * 1e-3,
            'eBC': 'BC9'
        },
        'MA350': {
            'band': np.array([375, 470, 528, 625, 880]),
            'MAE': np.array([24.069, 19.070, 17.028, 14.091, 10.120]) * 1e-3,
            'eBC': 'BC5'
        }
    }

    # Get configuration for the instrument
    if instru not in config:
        raise KeyError(f'Unknown aethalometer {instru!r}; expected one of {sorted(config)}')
    band_config = config[instru]
    band = band_config['band']

    # The BC channels are matched to wavelengths positionally, so the caller must
    # hand over exactly one column per band, in ascending-wavelength order
    if df.shape[1] != len(band):
        raise ValueError(
            f'{instru} expects {len(band)} BC columns (one per wavelength {band.tolist()}), '
            f'got {df.shape[1]}: {list(df.columns)}')

    # Create mask for valid rows - non-zero and non-NaN
    mask = ~((df == 0).all(axis=1) | df.isna().any(axis=1))

    # Pre-allocate output columns. Wavelengths that the instrument measures
    # directly are skipped in the specified list, so no column is duplicated
    extra_bands = [wl for wl in dict.fromkeys(specified_band) if wl not in band]
    result_columns = ([f'abs_{_band}' for _band in band] +
                      [f'abs_{_band}' for _band in extra_bands] +
                      ['eBC', 'AAE'])
    result_df = pd.DataFrame(np.nan, index=df.index, columns=result_columns)

    # Exit early if no valid data
    if not mask.any():
        return pd.concat([df, result_df], axis=1)

    # Get valid rows for processing
    df_valid = df[mask]

    # Calculate absorption coefficients (vectorized)
    for i, wl in enumerate(band):
        result_df.loc[mask, f'abs_{wl}'] = df_valid[df_valid.columns[i]] * band_config['MAE'][i]

    # Extract absorption values as array for AAE calculation
    abs_cols = [f'abs_{wl}' for wl in band]
    abs_values = result_df.loc[mask, abs_cols].values

    # AAE from a log-log fit over all bands, positive by convention
    aae_values = _angstrom_exponent(abs_values, band)
    result_df.loc[mask, 'AAE'] = aae_values

    # Calculate absorption at the requested wavelengths that are not measured directly
    for target_wl in extra_bands:
        # Find the closest reference wavelength
        closest_idx = int(np.abs(band - target_wl).argmin())
        ref_wl = band[closest_idx]

        # Extrapolate: abs(λ₂) = abs(λ₁)·(λ₂/λ₁)^(-AAE)
        ref_values = result_df.loc[mask, f'abs_{ref_wl}'].values
        ratio = target_wl / ref_wl
        result_df.loc[mask, f'abs_{target_wl}'] = calculate_specific_wavelengths_numba(
            ref_values, aae_values, ratio)

    # Set eBC values
    result_df.loc[mask, 'eBC'] = df_valid[band_config['eBC']]

    # Combine with original data
    return pd.concat([df, result_df], axis=1)
