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


def _scaCoe(df, instru, specified_band: list):
    """
    Calculate scattering coefficients and Ångström exponent for scattering.

    Parameters
    ----------
    df : pandas.DataFrame
        Data frame containing scattering measurements
    instru : str
        Instrument type ('Neph' or 'Aurora')
    specified_band : list
        List of wavelengths to calculate scattering coefficients for

    Returns
    -------
    pandas.DataFrame
        Data frame with scattering coefficients and Ångström exponent
    """
    band_Neph = np.array([450, 550, 700])
    band_Aurora = np.array([450, 525, 635])

    band = band_Neph if instru == 'Neph' else band_Aurora

    # Create mask for valid rows to avoid copying data
    mask = ~df[['B', 'G', 'R']].isna().any(axis=1)

    # Pre-allocate output DataFrame
    result_columns = [f'sca_{_band}' for _band in specified_band] + ['SAE']
    result_df = pd.DataFrame(np.nan, index=df.index, columns=result_columns)

    # Calculate only for valid rows
    if mask.any():
        if instru == 'Neph':
            # For Nephelometer, directly use G column
            if len(specified_band) == 1 and specified_band[0] == 550:
                # Common case optimization
                result_df.loc[mask, f'sca_550'] = df.loc[mask, 'G']
            else:
                # Need to extrapolate to other wavelengths
                bgr_values = df.loc[mask, ['B', 'G', 'R']].values
                log_band = np.log(band)

                # Calculate SAE using numba function
                sae_results = calculate_bulk_angstrom_numba(bgr_values, log_band)

                # Use the calculated SAE to get scattering at specified wavelengths
                for i, wl in enumerate(specified_band):
                    closest_idx = np.abs(band - wl).argmin()
                    ref_wl = band[closest_idx]
                    ref_idx = ['B', 'G', 'R'][closest_idx]

                    # Get reference measurements
                    ref_values = df.loc[mask, ref_idx].values

                    # Calculate scattering at target wavelength
                    ratio = wl / ref_wl
                    result_df.loc[mask, f'sca_{wl}'] = ref_values * (ratio ** -sae_results[:, 0])

                # Store SAE values
                result_df.loc[mask, 'SAE'] = sae_results[:, 0]
        else:
            # For Aurora, calculate using numba-optimized function instead of get_species_wavelength
            bgr_values = df.loc[mask, ['B', 'G', 'R']].values
            log_band = np.log(band)

            # Calculate SAE using numba function
            sae_results = calculate_bulk_angstrom_numba(bgr_values, log_band)

            # Store SAE values
            result_df.loc[mask, 'SAE'] = sae_results[:, 0]

            # Calculate scattering at specified wavelengths
            for i, wl in enumerate(specified_band):
                closest_idx = np.abs(band - wl).argmin()
                ref_wl = band[closest_idx]
                ref_idx = ['B', 'G', 'R'][closest_idx]

                # Get reference measurements
                ref_values = df.loc[mask, ref_idx].values

                # Calculate using the same function as for absorption, but with negative SAE
                ratio = wl / ref_wl
                # Note the negative sign for SAE
                neg_sae_values = -sae_results[:, 0]  # Negative SAE for scattering
                result_df.loc[mask, f'sca_{wl}'] = calculate_specific_wavelengths_numba(
                    ref_values, neg_sae_values, ratio)

    # Combine with original data
    return pd.concat([df, result_df], axis=1)


def _absCoe(df, instru, specified_band: list):
    """
    Calculate absorption coefficients and Ångström exponent for absorption.

    Parameters
    ----------
    df : pandas.DataFrame
        Data frame containing black carbon measurements
    instru : str
        Instrument type ('AE33', 'BC1054', or 'MA350')
    specified_band : list
        List of wavelengths to calculate absorption coefficients for

    Returns
    -------
    pandas.DataFrame
        Data frame with original data, absorption coefficients,
        coefficients at specified wavelengths, and Ångström exponent
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
    band_config = config[instru]

    # Create mask for valid rows - non-zero and non-NaN
    mask = ~((df == 0).all(axis=1) | df.isna().any(axis=1))

    # Pre-allocate output columns
    result_columns = ([f'abs_{_band}' for _band in band_config['band']] +
                      [f'abs_{_band}' for _band in specified_band] +
                      ['eBC', 'AAE'])
    result_df = pd.DataFrame(np.nan, index=df.index, columns=result_columns)

    # Exit early if no valid data
    if not mask.any():
        return pd.concat([df, result_df], axis=1)

    # Get valid rows for processing
    df_valid = df[mask]

    # Calculate absorption coefficients (vectorized)
    for i, wl in enumerate(band_config['band']):
        col_name = f'abs_{wl}'
        if col_name not in result_df.columns:
            continue
        result_df.loc[mask, col_name] = df_valid[df_valid.columns[i]] * band_config['MAE'][i]

    # Extract absorption values as array for AAE calculation
    abs_cols = [f'abs_{wl}' for wl in band_config['band']]
    abs_values = result_df.loc[mask, abs_cols].values

    # Calculate AAE with numba
    log_wavelengths = np.log(band_config['band'])
    aae_results = calculate_bulk_angstrom_numba(abs_values, log_wavelengths)

    # Store AAE values
    result_df.loc[mask, 'AAE'] = aae_results[:, 0]

    # Calculate absorption at specified wavelengths
    for target_wl in specified_band:
        # Find the closest reference wavelength
        closest_idx = np.abs(band_config['band'] - target_wl).argmin()
        ref_wl = band_config['band'][closest_idx]
        ref_col = f'abs_{ref_wl}'

        # Get reference values and AAE
        ref_values = result_df.loc[mask, ref_col].values
        aae_values = result_df.loc[mask, 'AAE'].values

        # Calculate using ratio
        ratio = target_wl / ref_wl
        result_df.loc[mask, f'abs_{target_wl}'] = calculate_specific_wavelengths_numba(
            ref_values, aae_values, ratio)

    # Set eBC values
    result_df.loc[mask, 'eBC'] = df_valid[band_config['eBC']]

    # Combine with original data
    return pd.concat([df, result_df], axis=1)
