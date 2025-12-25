"""
Refractive index retrieval from optical measurements.

This module provides functions for retrieving the complex refractive
index of aerosol particles using a grid search minimization approach
based on Mie theory calculations.

Required Columns
----------------
For retrieve_RI:
    - Extinction : Extinction coefficient (Mm-1)
    - Scattering : Scattering coefficient (Mm-1)
    - Absorption : Absorption coefficient (Mm-1)
    - PNSD columns : Particle number size distribution (dN/dlogDp)
"""

import numpy as np
from pandas import DataFrame

from AeroViz.dataProcess.core import validate_inputs

__all__ = ['retrieve_RI', 'grid_search_RI', 'get_required_columns']

# Required columns for optical data
REQUIRED_OPTICAL_COLUMNS = ['Extinction', 'Scattering', 'Absorption']

COLUMN_DESCRIPTIONS = {
    'Extinction': 'Extinction coefficient 消光係數 (Mm-1)',
    'Scattering': 'Scattering coefficient 散射係數 (Mm-1)',
    'Absorption': 'Absorption coefficient 吸收係數 (Mm-1)',
}


def grid_search_RI(bext_mea: float,
                   bsca_mea: float,
                   babs_mea: float,
                   dp: np.ndarray,
                   ndp: np.ndarray,
                   dlogdp: float = 0.014,
                   wavelength: float = 550,
                   n_range: tuple = (1.33, 1.60),
                   k_range: tuple = (0.00, 0.60),
                   space_size: int = 31
                   ) -> tuple:
    """
    Retrieve the complex refractive index using grid search minimization.

    This function performs a two-stage grid search to find the refractive
    index that best matches the measured optical properties.

    Parameters
    ----------
    bext_mea : float
        Measured extinction coefficient (Mm-1).
    bsca_mea : float
        Measured scattering coefficient (Mm-1).
    babs_mea : float
        Measured absorption coefficient (Mm-1).
    dp : np.ndarray
        Particle diameter array (nm).
    ndp : np.ndarray
        Number concentration for each diameter (dN/dlogDp).
    dlogdp : float, default=0.014
        Logarithmic bin width.
    wavelength : float, default=550
        Wavelength for Mie calculation (nm).
    n_range : tuple, default=(1.33, 1.60)
        Range of real refractive index (n) to search.
    k_range : tuple, default=(0.00, 0.60)
        Range of imaginary refractive index (k) to search.
    space_size : int, default=31
        Number of grid points in each dimension.

    Returns
    -------
    tuple
        (n_retrieved, k_retrieved) - The retrieved refractive index components.
    """
    from .mie_theory import Mie_PESD

    n_array = np.linspace(n_range[0], n_range[1], num=space_size)
    k_array = np.linspace(k_range[0], k_range[1], space_size)
    delta_array = np.zeros((space_size, space_size))

    # First pass: coarse grid search
    for ki, k in enumerate(k_array):
        for ni, n in enumerate(n_array):
            m = n + (1j * k)

            ext_dist, sca_dist, abs_dist = Mie_PESD(m, wavelength, dp, ndp)

            bext_cal = sum(ext_dist) * dlogdp
            bsca_cal = sum(sca_dist) * dlogdp
            babs_cal = sum(abs_dist) * dlogdp

            # Normalized chi-squared
            delta_array[ni][ki] = ((babs_mea - babs_cal) / 18.23) ** 2 + \
                                  ((bsca_mea - bsca_cal) / 83.67) ** 2

    # Find minimum and refine
    min_delta = delta_array.argmin()
    next_n = n_array[(min_delta // space_size)]
    next_k = k_array[(min_delta % space_size)]

    # Second pass: fine grid search around the minimum
    n_min = max(next_n - 0.02, 1.33)
    n_max = next_n + 0.02
    k_min = max(next_k - 0.04, 0)
    k_max = next_k + 0.04
    fine_size = 41

    n_fine = np.linspace(n_min, n_max, fine_size)
    k_fine = np.linspace(k_min, k_max, fine_size)
    delta_fine = np.zeros((fine_size, fine_size))

    for ki, k in enumerate(k_fine):
        for ni, n in enumerate(n_fine):
            m = n + (1j * k)

            ext_dist, sca_dist, abs_dist = Mie_PESD(m, wavelength, dp, ndp)

            bext_cal = sum(ext_dist) * dlogdp
            bsca_cal = sum(sca_dist) * dlogdp
            babs_cal = sum(abs_dist) * dlogdp

            delta_fine[ni][ki] = ((bext_mea - bext_cal) / 18.23) ** 2 + \
                                 ((bsca_mea - bsca_cal) / 83.67) ** 2

    min_delta_fine = delta_fine.argmin()
    n_retrieved = n_fine[(min_delta_fine // fine_size)]
    k_retrieved = k_fine[(min_delta_fine % fine_size)]

    return n_retrieved, k_retrieved


def retrieve_RI(df_optical: DataFrame,
                df_pnsd: DataFrame,
                dlogdp: float = 0.014,
                wavelength: float = 550,
                n_range: tuple = (1.33, 1.60),
                k_range: tuple = (0.00, 0.60),
                space_size: int = 31
                ) -> DataFrame:
    """
    Retrieve refractive index for a time series of measurements.

    Parameters
    ----------
    df_optical : DataFrame
        Optical measurements with required columns:
        - Extinction : Extinction coefficient (Mm-1)
        - Scattering : Scattering coefficient (Mm-1)
        - Absorption : Absorption coefficient (Mm-1)
    df_pnsd : DataFrame
        Particle number size distribution with diameter columns (nm).
        Column names should be diameter values (e.g., 10.0, 20.0, ...).
    dlogdp : float, default=0.014
        Logarithmic bin width.
    wavelength : float, default=550
        Wavelength for Mie calculation (nm).
    n_range : tuple, default=(1.33, 1.60)
        Range of real refractive index to search.
    k_range : tuple, default=(0.00, 0.60)
        Range of imaginary refractive index to search.
    space_size : int, default=31
        Number of grid points for initial search.

    Returns
    -------
    DataFrame
        Retrieved refractive index with columns: re_real, re_imaginary.

    Raises
    ------
    ValueError
        If required columns are missing from df_optical or df_pnsd is empty.

    Examples
    --------
    >>> cols = get_required_columns()
    >>> print(cols['retrieve_RI'])
    """
    from pandas import concat

    # Validate optical data
    validate_inputs(df_optical, REQUIRED_OPTICAL_COLUMNS, 'retrieve_RI', COLUMN_DESCRIPTIONS)

    # Validate PNSD data
    if df_pnsd is None or df_pnsd.empty:
        raise ValueError(
            "\nretrieve_RI() 需要粒徑分布資料！\n"
            "  必要輸入: df_pnsd (Particle Number Size Distribution)\n"
            "  欄位格式: 粒徑值作為欄位名稱 (nm)"
        )

    combined = concat([df_optical, df_pnsd], axis=1).dropna()
    dp = np.array(df_pnsd.columns, dtype=float)

    results = []

    for idx, row in combined.iterrows():
        bext_mea = row['Extinction']
        bsca_mea = row['Scattering']
        babs_mea = row['Absorption']
        ndp = np.array(row[df_pnsd.columns])

        n_ret, k_ret = grid_search_RI(
            bext_mea, bsca_mea, babs_mea,
            dp, ndp, dlogdp, wavelength,
            n_range, k_range, space_size
        )

        results.append({'re_real': n_ret, 're_imaginary': k_ret})

    result_df = DataFrame(results, index=combined.index)

    return result_df.reindex(df_optical.index)


def get_required_columns():
    """
    Get required column names for refractive index retrieval.

    Returns
    -------
    dict
        Dictionary with function names as keys and required columns as values.

    Examples
    --------
    >>> cols = get_required_columns()
    >>> print(cols['retrieve_RI'])
    """
    return {
        'retrieve_RI': {
            'df_optical': REQUIRED_OPTICAL_COLUMNS.copy(),
            'df_pnsd': 'Diameter values as column names (nm)'
        },
        'grid_search_RI': {
            'description': '單點反演，需提供標量值',
            'inputs': ['bext_mea', 'bsca_mea', 'babs_mea', 'dp (array)', 'ndp (array)']
        }
    }
