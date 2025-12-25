"""
IMPROVE extinction reconstruction algorithms.

This module implements the IMPROVE (Interagency Monitoring of Protected
Visual Environments) equation for reconstructing aerosol light extinction
from chemical composition data.

Required Columns
----------------
For revised/modified functions:
    - AS  : Ammonium Sulfate (ug/m3)
    - AN  : Ammonium Nitrate (ug/m3)
    - OM  : Organic Matter (ug/m3)
    - Soil: Soil/Crustal (ug/m3)
    - SS  : Sea Salt (ug/m3)
    - EC  : Elemental Carbon (ug/m3)

References
----------
Pitchford, M., et al. (2007). Revised Algorithm for Estimating Light
Extinction from IMPROVE Particle Speciation Data. JAPCA J. Air Waste Ma.
"""

from pathlib import Path

import numpy as np
from pandas import DataFrame, read_pickle

from AeroViz.dataProcess.core import union_index, validate_inputs

# Required columns and descriptions
REQUIRED_MASS_COLUMNS = ['AS', 'AN', 'OM', 'Soil', 'SS', 'EC']

COLUMN_DESCRIPTIONS = {
    'AS': 'Ammonium Sulfate 硫酸銨 (ug/m3)',
    'AN': 'Ammonium Nitrate 硝酸銨 (ug/m3)',
    'OM': 'Organic Matter 有機物 (ug/m3)',
    'Soil': 'Soil/Crustal 土壤/地殼 (ug/m3)',
    'SS': 'Sea Salt 海鹽 (ug/m3)',
    'EC': 'Elemental Carbon 元素碳 (ug/m3)',
}

# Mass extinction efficiencies (m2/g) for reference
EXTINCTION_COEFFICIENTS = {
    'revised': {
        'small_mode': {'AS': 2.2, 'AN': 2.4, 'OM': 2.8},
        'large_mode': {'AS': 4.8, 'AN': 5.1, 'OM': 6.1},
        'other': {'Soil': 1.0, 'SS': 1.7, 'EC': 10.0}
    },
    'modified': {
        'AS': 3.0, 'AN': 3.0, 'OM': 4.0,
        'Soil': 1.0, 'SS': 1.7, 'EC': 10.0
    }
}

# Cache for fRH lookup table
_FRH_CACHE = None


def load_fRH():
    """
    Load the f(RH) lookup table from pickle file.

    Returns
    -------
    DataFrame
        f(RH) values indexed by relative humidity (0-95%).
    """
    global _FRH_CACHE
    if _FRH_CACHE is None:
        with (Path(__file__).parent / 'fRH.pkl').open('rb') as f:
            _FRH_CACHE = read_pickle(f)
            _FRH_CACHE.loc[np.nan] = np.nan
    return _FRH_CACHE


def get_fRH_factors(rh_data, fRH_table):
    """
    Get hygroscopic growth factors for given RH values.

    Parameters
    ----------
    rh_data : Series or None
        Relative humidity data (%).
    fRH_table : DataFrame
        f(RH) lookup table.

    Returns
    -------
    tuple
        (f_rh, f_rh_ss, f_rh_small, f_rh_large) growth factors.
    """
    if rh_data is None:
        return 1, 1, 1, 1

    rh_clipped = rh_data.mask(rh_data > 95, 95).round(0)
    return fRH_table.loc[rh_clipped].values.T


def split_size_modes(mass_data):
    """
    Split mass into small and large size modes.

    For mass < 20 ug/m3:
        large = mass^2 / 20
        small = mass - large
    For mass >= 20 ug/m3:
        large = mass
        small = 0

    Parameters
    ----------
    mass_data : DataFrame
        Mass concentrations with columns AS, AN, OM.

    Returns
    -------
    tuple
        (large_mode, small_mode) DataFrames.
    """
    mode_data = mass_data[['AS', 'AN', 'OM']].copy()

    large_mode = mode_data.mask(mode_data < 20, mode_data ** 2 / 20)
    small_mode = mode_data.values - large_mode

    large_mode.columns = ['L_AS', 'L_AN', 'L_OM']
    small_mode.columns = ['S_AS', 'S_AN', 'S_OM']

    return large_mode, small_mode


def revised(df_mass, df_rh=None, df_nh4_status=None):
    """
    Calculate extinction using the revised IMPROVE equation.

    The revised IMPROVE algorithm uses size-dependent mass extinction
    efficiencies with separate coefficients for small and large modes.

    Parameters
    ----------
    df_mass : DataFrame
        Mass concentrations (ug/m3) with required columns:
        - AS   : Ammonium Sulfate 硫酸銨
        - AN   : Ammonium Nitrate 硝酸銨
        - OM   : Organic Matter 有機物
        - Soil : Soil/Crustal 土壤
        - SS   : Sea Salt 海鹽
        - EC   : Elemental Carbon 元素碳
    df_rh : DataFrame or None, optional
        Relative humidity data (%). If None, only dry extinction is calculated.
    df_nh4_status : DataFrame or None, optional
        NH4 status from reconstruction_basic(). If provided, rows with
        'Deficiency' status will be excluded from calculation.
        Must have 'status' column with 'Enough' or 'Deficiency' values.

    Returns
    -------
    dict
        Dictionary with keys:
        - 'dry': Dry extinction DataFrame (AS, AN, OM, Soil, SS, EC, total)
        - 'wet': Wet extinction DataFrame (if df_rh provided)
        - 'ALWC': Water contribution to extinction (wet - dry) for AS, AN, SS, total
        - 'fRH': Hygroscopic growth factor (wet_total / dry_total)

    Raises
    ------
    ValueError
        If required columns are missing from df_mass.

    Notes
    -----
    Mass extinction efficiencies (m2/g):
    - Small mode: AS=2.2, AN=2.4, OM=2.8
    - Large mode: AS=4.8, AN=5.1, OM=6.1
    - Soil=1.0, SS=1.7, EC=10.0

    Examples
    --------
    >>> # Basic usage
    >>> result = revised(df_mass, df_rh)
    >>>
    >>> # With NH4 status filtering (exclude deficient samples)
    >>> chem_result = reconstruction_basic(...)
    >>> result = revised(df_mass, df_rh, df_nh4_status=chem_result['NH4_status'])
    """
    # Validate input columns
    validate_inputs(df_mass, REQUIRED_MASS_COLUMNS, 'revised', COLUMN_DESCRIPTIONS)

    # Store original index for reindexing at the end
    original_index = df_mass.index.copy()

    # Filter out NH4 deficient samples if status provided
    if df_nh4_status is not None:
        if 'status' not in df_nh4_status.columns:
            raise ValueError(
                "\ndf_nh4_status 需要 'status' 欄位！\n"
                "  應使用 reconstruction_basic() 的 'NH4_status' 輸出"
            )
        enough_mask = df_nh4_status['status'] == 'Enough'
        df_mass = df_mass.loc[enough_mask].copy()
        if df_rh is not None:
            df_rh = df_rh.loc[enough_mask].copy()

    df_mass, df_rh = union_index(df_mass, df_rh)
    fRH_table = load_fRH()

    # Split into size modes
    large_mode, small_mode = split_size_modes(df_mass)
    df_mass = df_mass.join(large_mode).join(small_mode)

    def calculate_extinction(rh_data=None):
        f_rh, f_rh_ss, f_rh_small, f_rh_large = get_fRH_factors(rh_data, fRH_table)

        ext = DataFrame(index=df_mass.index)

        # Revised IMPROVE coefficients with size-dependent modes
        ext['AS'] = 2.2 * f_rh_small * df_mass['S_AS'] + 4.8 * f_rh_large * df_mass['L_AS']
        ext['AN'] = 2.4 * f_rh_small * df_mass['S_AN'] + 5.1 * f_rh_large * df_mass['L_AN']
        ext['OM'] = 2.8 * df_mass['S_OM'] + 6.1 * df_mass['L_OM']
        ext['Soil'] = 1.0 * df_mass['Soil']
        ext['SS'] = 1.7 * f_rh_ss * df_mass['SS']
        ext['EC'] = 10.0 * df_mass['EC']

        ext['total'] = ext.sum(axis=1)

        return ext.dropna()

    result = {'dry': calculate_extinction()}

    if df_rh is not None:
        result['wet'] = calculate_extinction(df_rh)

        # Calculate ALWC contribution (wet - dry)
        alwc = DataFrame(index=result['dry'].index)
        alwc['AS'] = result['wet']['AS'] - result['dry']['AS']
        alwc['AN'] = result['wet']['AN'] - result['dry']['AN']
        alwc['SS'] = result['wet']['SS'] - result['dry']['SS']
        alwc['total'] = result['wet']['total'] - result['dry']['total']
        result['ALWC'] = alwc

        # Calculate fRH (hygroscopic growth factor)
        result['fRH'] = result['wet']['total'] / result['dry']['total']

    # Reindex to original index (NH4 deficient rows will be NaN)
    for key in result:
        if isinstance(result[key], DataFrame):
            result[key] = result[key].reindex(original_index)
        else:
            result[key] = result[key].reindex(original_index)

    return result


def modified(df_mass, df_rh=None, df_nh4_status=None):
    """
    Calculate extinction using the modified IMPROVE equation.

    The modified version uses simpler coefficients without
    size-dependent modes.

    Parameters
    ----------
    df_mass : DataFrame
        Mass concentrations (ug/m3) with required columns:
        - AS   : Ammonium Sulfate 硫酸銨
        - AN   : Ammonium Nitrate 硝酸銨
        - OM   : Organic Matter 有機物
        - Soil : Soil/Crustal 土壤
        - SS   : Sea Salt 海鹽
        - EC   : Elemental Carbon 元素碳
    df_rh : DataFrame or None, optional
        Relative humidity data (%).
    df_nh4_status : DataFrame or None, optional
        NH4 status from reconstruction_basic(). If provided, rows with
        'Deficiency' status will be excluded from calculation.
        Must have 'status' column with 'Enough' or 'Deficiency' values.

    Returns
    -------
    dict
        Dictionary with keys:
        - 'dry': Dry extinction DataFrame (AS, AN, OM, Soil, SS, EC, total)
        - 'wet': Wet extinction DataFrame (if df_rh provided)
        - 'ALWC': Water contribution to extinction (wet - dry) for AS, AN, SS, total
        - 'fRH': Hygroscopic growth factor (wet_total / dry_total)

    Raises
    ------
    ValueError
        If required columns are missing from df_mass.

    Notes
    -----
    Mass extinction efficiencies (m2/g):
    - AS=3.0, AN=3.0, OM=4.0
    - Soil=1.0, SS=1.7, EC=10.0

    Examples
    --------
    >>> # With NH4 status filtering (exclude deficient samples)
    >>> chem_result = reconstruction_basic(...)
    >>> result = modified(df_mass, df_rh, df_nh4_status=chem_result['NH4_status'])
    """
    # Validate input columns
    validate_inputs(df_mass, REQUIRED_MASS_COLUMNS, 'modified', COLUMN_DESCRIPTIONS)

    # Store original index for reindexing at the end
    original_index = df_mass.index.copy()

    # Filter out NH4 deficient samples if status provided
    if df_nh4_status is not None:
        if 'status' not in df_nh4_status.columns:
            raise ValueError(
                "\ndf_nh4_status 需要 'status' 欄位！\n"
                "  應使用 reconstruction_basic() 的 'NH4_status' 輸出"
            )
        enough_mask = df_nh4_status['status'] == 'Enough'
        df_mass = df_mass.loc[enough_mask].copy()
        if df_rh is not None:
            df_rh = df_rh.loc[enough_mask].copy()

    df_mass, df_rh = union_index(df_mass, df_rh)
    fRH_table = load_fRH()

    def calculate_extinction(rh_data=None):
        f_rh, f_rh_ss, f_rh_small, f_rh_large = get_fRH_factors(rh_data, fRH_table)

        ext = DataFrame(index=df_mass.index)

        # Modified IMPROVE coefficients (simpler version)
        ext['AS'] = 3.0 * f_rh * df_mass['AS']
        ext['AN'] = 3.0 * f_rh * df_mass['AN']
        ext['OM'] = 4.0 * df_mass['OM']
        ext['Soil'] = 1.0 * df_mass['Soil']
        ext['SS'] = 1.7 * f_rh_ss * df_mass['SS']
        ext['EC'] = 10.0 * df_mass['EC']

        ext['total'] = ext.sum(axis=1)

        return ext.dropna()

    result = {'dry': calculate_extinction()}

    if df_rh is not None:
        result['wet'] = calculate_extinction(df_rh)

        # Calculate ALWC contribution (wet - dry)
        alwc = DataFrame(index=result['dry'].index)
        alwc['AS'] = result['wet']['AS'] - result['dry']['AS']
        alwc['AN'] = result['wet']['AN'] - result['dry']['AN']
        alwc['SS'] = result['wet']['SS'] - result['dry']['SS']
        alwc['total'] = result['wet']['total'] - result['dry']['total']
        result['ALWC'] = alwc

        # Calculate fRH (hygroscopic growth factor)
        result['fRH'] = result['wet']['total'] / result['dry']['total']

    # Reindex to original index (NH4 deficient rows will be NaN)
    for key in result:
        if isinstance(result[key], DataFrame):
            result[key] = result[key].reindex(original_index)
        else:
            result[key] = result[key].reindex(original_index)

    return result


def gas_extinction(df_no2, df_temp):
    """
    Calculate gas contribution to atmospheric extinction.

    Parameters
    ----------
    df_no2 : DataFrame
        NO2 concentration (ppb). Any column name accepted.
    df_temp : DataFrame
        Ambient temperature (Celsius). Any column name accepted.

    Returns
    -------
    DataFrame
        Gas extinction contributions (Mm-1) with columns:
        - ScatteringByGas: Rayleigh scattering by air molecules
        - AbsorptionByGas: Absorption by NO2
        - ExtinctionByGas: Total gas extinction

    Notes
    -----
    Rayleigh scattering coefficient: 11.4 Mm-1 at 293K
    NO2 absorption cross-section: 0.33 Mm-1/ppb at 550nm

    Examples
    --------
    >>> df_no2 = pd.DataFrame({'NO2': [20.0, 30.0]})
    >>> df_temp = pd.DataFrame({'temp': [25.0, 28.0]})
    >>> result = gas_extinction(df_no2, df_temp)
    """
    if df_no2 is None or df_no2.empty:
        raise ValueError("gas_extinction() 需要 NO2 濃度資料 (ppb)")
    if df_temp is None or df_temp.empty:
        raise ValueError("gas_extinction() 需要溫度資料 (Celsius)")

    df_no2, df_temp = union_index(df_no2, df_temp)

    result = DataFrame(index=df_no2.index)

    # Rayleigh scattering (temperature-dependent)
    temp_kelvin = 273 + df_temp.iloc[:, 0]
    result['ScatteringByGas'] = 11.4 * 293 / temp_kelvin

    # NO2 absorption
    result['AbsorptionByGas'] = 0.33 * df_no2.iloc[:, 0]

    # Total gas extinction
    result['ExtinctionByGas'] = result['ScatteringByGas'] + result['AbsorptionByGas']

    return result


def get_required_columns():
    """
    Get the required column names for IMPROVE calculations.

    Returns
    -------
    dict
        Dictionary with function names as keys and required columns as values.

    Examples
    --------
    >>> cols = get_required_columns()
    >>> print(cols['revised'])
    """
    return {
        'revised': {
            'df_mass': REQUIRED_MASS_COLUMNS.copy(),
            'df_rh': 'Relative humidity (%) - optional',
            'df_nh4_status': "NH4 status from reconstruction_basic()['NH4_status'] - optional",
            'outputs': ['dry', 'wet', 'ALWC', 'fRH']
        },
        'modified': {
            'df_mass': REQUIRED_MASS_COLUMNS.copy(),
            'df_rh': 'Relative humidity (%) - optional',
            'df_nh4_status': "NH4 status from reconstruction_basic()['NH4_status'] - optional",
            'outputs': ['dry', 'wet', 'ALWC', 'fRH']
        },
        'gas_extinction': {
            'df_no2': 'NO2 concentration (ppb)',
            'df_temp': 'Temperature (Celsius)',
            'outputs': ['ScatteringByGas', 'AbsorptionByGas', 'ExtinctionByGas']
        }
    }
