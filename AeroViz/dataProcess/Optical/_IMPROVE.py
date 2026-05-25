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

    # Accept a single-column DataFrame as well as a Series — indexing the lookup
    # table with a 2-D key raises "Cannot index with multidimensional key".
    if isinstance(rh_data, DataFrame):
        if rh_data.shape[1] != 1:
            raise ValueError(
                "df_RH must be a single RH column (a Series or 1-column DataFrame), "
                f"got {rh_data.shape[1]} columns."
            )
        rh_data = rh_data.iloc[:, 0]

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


def localized(df_mass, df_ext, df_rh=None, df_nh4_status=None, oa_oc_ratio=1.8,
               upper_bounds=None):
    """
    Calculate extinction using the Localized IMPROVE algorithm.

    This method keeps AS, AN, Soil, SS from the Revised IMPROVE
    (with small/large mode split), and uses multiple linear regression
    to determine the MSE/MAE of POA, SOA, and EC.

    OM is split into small/large modes using the Revised IMPROVE formula,
    then redistributed to POA and SOA by their mass fractions.

    Parameters
    ----------
    df_mass : DataFrame
        Mass concentrations (ug/m3) with required columns:
        AS, AN, POC, SOC, Soil, SS, EC.
    df_ext : DataFrame
        Measured extinction data with columns:
        - Scattering : measured scattering coefficient (Mm-1)
        - Absorption : measured absorption coefficient (Mm-1)
    df_rh : DataFrame or None, optional
        Relative humidity data (%).
    df_nh4_status : DataFrame or None, optional
        NH4 status from reconstruction_basic().
    oa_oc_ratio : float, optional
        OA/OC conversion ratio (default 1.8).
    upper_bounds : dict or None, optional
        Upper bounds for MLR coefficients. Default:
        {'S_POA': 10, 'L_POA': 10, 'S_SOA': 10, 'L_SOA': 10, 'EC_sca': 1, 'EC_abs': 20}

    Returns
    -------
    dict
        Dictionary with keys:
        - 'dry': Dry extinction DataFrame
        - 'wet': Wet extinction DataFrame (if df_rh provided)
        - 'ALWC': Water contribution to extinction
        - 'fRH': Hygroscopic growth factor
        - 'coefficients': MLR-derived MSE/MAE coefficients
        - 'regression': Regression statistics (slope, R2)
    """
    from scipy.optimize import curve_fit

    REQUIRED_LOCALIZED_COLUMNS = ['AS', 'AN', 'POC', 'SOC', 'Soil', 'SS', 'EC']
    validate_inputs(df_mass, REQUIRED_LOCALIZED_COLUMNS, 'localized', {
        'AS': 'Ammonium Sulfate (ug/m3)',
        'AN': 'Ammonium Nitrate (ug/m3)',
        'POC': 'Primary Organic Carbon (ug/m3)',
        'SOC': 'Secondary Organic Carbon (ug/m3)',
        'Soil': 'Soil/Crustal (ug/m3)',
        'SS': 'Sea Salt (ug/m3)',
        'EC': 'Elemental Carbon (ug/m3)',
    })

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
        df_ext = df_ext.loc[enough_mask].copy()
        if df_rh is not None:
            df_rh = df_rh.loc[enough_mask].copy()

    df_mass, df_ext = union_index(df_mass, df_ext)
    df_mass, df_rh = union_index(df_mass, df_rh)
    fRH_table = load_fRH()

    # --- Step 1: Revised IMPROVE for AS, AN, Soil, SS ---
    # Add OM column (= POA + SOA) for split_size_modes which requires AS, AN, OM
    OM_total = df_mass['POC'] * oa_oc_ratio + df_mass['SOC'] * oa_oc_ratio
    df_mass_with_om = df_mass.assign(OM=OM_total)

    # AS, AN with small/large split (same as Revised)
    large_mode_as_an, small_mode_as_an = split_size_modes(df_mass_with_om)

    revised_ext = DataFrame(index=df_mass.index)
    revised_ext['AS'] = 2.2 * small_mode_as_an['S_AS'] + 4.8 * large_mode_as_an['L_AS']
    revised_ext['AN'] = 2.4 * small_mode_as_an['S_AN'] + 5.1 * large_mode_as_an['L_AN']
    revised_ext['Soil'] = 1.0 * df_mass['Soil']
    revised_ext['SS'] = 1.7 * df_mass['SS']

    # --- Step 2: Split OM into small/large, redistribute to POA/SOA ---
    POA = df_mass['POC'] * oa_oc_ratio
    SOA = df_mass['SOC'] * oa_oc_ratio
    OM = POA + SOA

    # Split total OM into small/large mode
    L_OM = OM.where(OM >= 20, OM ** 2 / 20)
    S_OM = OM - L_OM

    # Redistribute by mass fraction
    f_POA = (POA / OM).fillna(0)
    f_SOA = (SOA / OM).fillna(0)

    S_POA = S_OM * f_POA
    L_POA = L_OM * f_POA
    S_SOA = S_OM * f_SOA
    L_SOA = L_OM * f_SOA

    # --- Step 3: MLR to find POA/SOA MSE (EC fixed at Revised IMPROVE = 10.0) ---
    EC_MEE = 10.0
    measured_ext = df_ext['Scattering'].add(df_ext['Absorption'], fill_value=0)
    revised_ext['EC'] = EC_MEE * df_mass['EC']
    residual = measured_ext - revised_ext.sum(axis=1)

    # Drop NaN for regression
    reg_df = DataFrame({
        'S_POA': S_POA, 'L_POA': L_POA,
        'S_SOA': S_SOA, 'L_SOA': L_SOA,
        'residual': residual
    }).dropna()

    if upper_bounds is None:
        upper_bounds = {
            'S_POA': 10, 'L_POA': 10,
            'S_SOA': 10, 'L_SOA': 10,
        }

    X = reg_df[['S_POA', 'L_POA', 'S_SOA', 'L_SOA']].values

    def mlr_func(x, a1, a2, a3, a4):
        return a1 * x[:, 0] + a2 * x[:, 1] + a3 * x[:, 2] + a4 * x[:, 3]

    popt, pcov = curve_fit(
        mlr_func, X, reg_df['residual'].values,
        p0=[2.8, 6.1, 2.8, 6.1],
        bounds=(0, [upper_bounds['S_POA'], upper_bounds['L_POA'],
                    upper_bounds['S_SOA'], upper_bounds['L_SOA']])
    )

    coeff_names = ['MSE_S_POA', 'MSE_L_POA', 'MSE_S_SOA', 'MSE_L_SOA']
    coefficients = dict(zip(coeff_names, popt))
    coefficients['MAE_EC'] = EC_MEE

    # Effective MSE (mass-weighted average of small/large modes)
    total_POA = (S_POA + L_POA).sum()
    total_SOA = (S_SOA + L_SOA).sum()
    if total_POA > 0:
        coefficients['MSE_POA'] = (popt[0] * S_POA.sum() + popt[1] * L_POA.sum()) / total_POA
    if total_SOA > 0:
        coefficients['MSE_SOA'] = (popt[2] * S_SOA.sum() + popt[3] * L_SOA.sum()) / total_SOA

    # Regression statistics
    predicted = mlr_func(X, *popt)
    ss_res = np.sum((reg_df['residual'].values - predicted) ** 2)
    ss_tot = np.sum((reg_df['residual'].values - reg_df['residual'].mean()) ** 2)
    r2_residual = 1 - ss_res / ss_tot

    # Full reconstruction statistics
    full_predicted = revised_ext.sum(axis=1).reindex(reg_df.index) + predicted
    full_measured = measured_ext.reindex(reg_df.index)
    slope = np.polyfit(full_measured.values, full_predicted.values, 1)[0]
    ss_res_full = np.sum((full_measured.values - full_predicted.values) ** 2)
    ss_tot_full = np.sum((full_measured.values - full_measured.mean()) ** 2)
    r2_full = 1 - ss_res_full / ss_tot_full

    regression = {'slope': slope, 'R2': r2_full, 'R2_residual': r2_residual}

    # --- Step 4: Build extinction DataFrame ---
    def calculate_extinction(rh_data=None):
        f_rh, f_rh_ss, f_rh_small, f_rh_large = get_fRH_factors(rh_data, fRH_table)

        ext = DataFrame(index=df_mass.index)

        # Revised IMPROVE for AS, AN (with f(RH))
        ext['AS'] = 2.2 * f_rh_small * small_mode_as_an['S_AS'] + 4.8 * f_rh_large * large_mode_as_an['L_AS']
        ext['AN'] = 2.4 * f_rh_small * small_mode_as_an['S_AN'] + 5.1 * f_rh_large * large_mode_as_an['L_AN']

        # POA and SOA with MLR-derived coefficients (no f(RH) applied)
        ext['POA'] = popt[0] * S_POA + popt[1] * L_POA
        ext['SOA'] = popt[2] * S_SOA + popt[3] * L_SOA

        # Revised IMPROVE for Soil, SS, EC
        ext['Soil'] = 1.0 * df_mass['Soil']
        ext['SS'] = 1.7 * f_rh_ss * df_mass['SS']
        ext['EC'] = EC_MEE * df_mass['EC']

        ext['total'] = ext.sum(axis=1)

        return ext.dropna()

    result = {'dry': calculate_extinction()}

    if df_rh is not None:
        result['wet'] = calculate_extinction(df_rh)

        alwc = DataFrame(index=result['dry'].index)
        alwc['AS'] = result['wet']['AS'] - result['dry']['AS']
        alwc['AN'] = result['wet']['AN'] - result['dry']['AN']
        alwc['SS'] = result['wet']['SS'] - result['dry']['SS']
        alwc['total'] = result['wet']['total'] - result['dry']['total']
        result['ALWC'] = alwc

        result['fRH'] = result['wet']['total'] / result['dry']['total']

    result['coefficients'] = coefficients
    result['regression'] = regression

    # Reindex to original index
    for key in result:
        if isinstance(result[key], (DataFrame,)):
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

    # Rayleigh scattering (temperature-dependent); use 273.15 to be consistent
    # with the rest of the package (e.g. _calculate.kappa_calculate).
    temp_kelvin = 273.15 + df_temp.iloc[:, 0]
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
