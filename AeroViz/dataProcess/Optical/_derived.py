"""
Derived optical and atmospheric parameters.

This module provides functions for calculating various derived parameters
from optical and chemical measurements.

Available Functions
-------------------
- derived_parameters: Calculate multiple derived parameters at once
- calculate_visibility: Calculate visibility from extinction
- calculate_MAC: Mass Absorption Cross-section
- calculate_Ox: Total oxidant (NO2 + O3)
- calculate_fRH: Hygroscopic growth factor for extinction
"""

import numpy as np
from pandas import DataFrame, concat

from AeroViz.dataProcess.core import validate_inputs

__all__ = ['derived_parameters', 'calculate_visibility', 'calculate_MAC',
           'calculate_Ox', 'calculate_fRH', 'get_required_columns',
           'calculate_BrC_absorption']

# Column descriptions for validation
COLUMN_DESCRIPTIONS = {
    'Scattering': 'Scattering coefficient 散射係數 (Mm-1)',
    'Absorption': 'Absorption coefficient 吸收係數 (Mm-1)',
    'Extinction': 'Extinction coefficient 消光係數 (Mm-1)',
    'NO2': 'Nitrogen dioxide 二氧化氮 (ppb)',
    'O3': 'Ozone 臭氧 (ppb)',
    'EC': 'Elemental carbon 元素碳 (ug/m3)',
    'OC': 'Organic carbon 有機碳 (ug/m3)',
    'PM1': 'PM1 (ug/m3)',
    'PM2.5': 'PM2.5 (ug/m3)',
}


def derived_parameters(df_sca=None,
                       df_abs=None,
                       df_ext=None,
                       df_no2=None,
                       df_o3=None,
                       df_ec=None,
                       df_oc=None,
                       df_pm1=None,
                       df_pm25=None,
                       df_improve=None
                       ) -> DataFrame:
    """
    Calculate various derived atmospheric parameters.

    Parameters
    ----------
    df_sca : DataFrame, optional
        Scattering coefficient data (Mm-1).
    df_abs : DataFrame, optional
        Absorption coefficient data (Mm-1).
    df_ext : DataFrame, optional
        Extinction coefficient data (Mm-1).
    df_no2 : DataFrame, optional
        NO2 concentration (ppb).
    df_o3 : DataFrame, optional
        O3 concentration (ppb).
    df_ec : DataFrame, optional
        Elemental carbon concentration (ug/m3).
    df_oc : DataFrame, optional
        Organic carbon concentration (ug/m3).
    df_pm1 : DataFrame, optional
        PM1 concentration (ug/m3).
    df_pm25 : DataFrame, optional
        PM2.5 concentration (ug/m3).
    df_improve : DataFrame, optional
        IMPROVE extinction data with 'total_ext' and 'total_ext_dry' columns.

    Returns
    -------
    DataFrame
        Derived parameters including:
        - PG: Total extinction (particle + gas)
        - MAC: Mass Absorption Cross-section
        - Ox: Oxidant (NO2 + O3)
        - N2O5_tracer: NO2 * O3 indicator
        - Vis_cal: Calculated visibility (km)
        - fRH_IMPR: Hygroscopic growth factor from IMPROVE
        - OCEC_ratio: OC/EC ratio
        - PM1_PM25_ratio: PM1/PM2.5 ratio
    """
    # Combine all inputs to get common index
    all_dfs = [df for df in [df_sca, df_abs, df_ext, df_no2, df_o3, df_ec,
                              df_oc, df_pm1, df_pm25, df_improve] if df is not None]

    if not all_dfs:
        return DataFrame()

    common_index = concat(all_dfs, axis=1).index
    result = DataFrame(index=common_index)

    # Total extinction (particle + gas)
    if df_sca is not None and df_abs is not None:
        result['Bsp'] = df_sca.iloc[:, 0] if isinstance(df_sca, DataFrame) else df_sca
        result['Bap'] = df_abs.iloc[:, 0] if isinstance(df_abs, DataFrame) else df_abs
        result['PG'] = result['Bsp'] + result['Bap']

    # Mass Absorption Cross-section (MAC)
    if df_abs is not None and df_ec is not None:
        abs_val = df_abs.iloc[:, 0] if isinstance(df_abs, DataFrame) else df_abs
        ec_val = df_ec.iloc[:, 0] if isinstance(df_ec, DataFrame) else df_ec
        result['MAC'] = abs_val / ec_val

    # Oxidant (Ox = NO2 + O3)
    if df_no2 is not None and df_o3 is not None:
        no2_val = df_no2.iloc[:, 0] if isinstance(df_no2, DataFrame) else df_no2
        o3_val = df_o3.iloc[:, 0] if isinstance(df_o3, DataFrame) else df_o3
        result['Ox'] = no2_val + o3_val

        # N2O5 tracer (NO2 * O3)
        result['N2O5_tracer'] = no2_val * o3_val

    # Visibility calculation
    if df_ext is not None:
        ext_val = df_ext.iloc[:, 0] if isinstance(df_ext, DataFrame) else df_ext
        result['Vis_cal'] = 1096 / ext_val  # Koschmieder equation, visibility in km

    # fRH from IMPROVE
    if df_improve is not None and 'total_ext' in df_improve.columns and 'total_ext_dry' in df_improve.columns:
        result['fRH_IMPR'] = df_improve['total_ext'] / df_improve['total_ext_dry']

    # OC/EC ratio
    if df_oc is not None and df_ec is not None:
        oc_val = df_oc.iloc[:, 0] if isinstance(df_oc, DataFrame) else df_oc
        ec_val = df_ec.iloc[:, 0] if isinstance(df_ec, DataFrame) else df_ec
        result['OCEC_ratio'] = oc_val / ec_val

    # PM1/PM2.5 ratio
    if df_pm1 is not None and df_pm25 is not None:
        pm1_val = df_pm1.iloc[:, 0] if isinstance(df_pm1, DataFrame) else df_pm1
        pm25_val = df_pm25.iloc[:, 0] if isinstance(df_pm25, DataFrame) else df_pm25
        ratio = pm1_val / pm25_val
        result['PM1_PM25_ratio'] = np.where(ratio < 1, ratio, np.nan)

    return result


def calculate_visibility(df_ext: DataFrame) -> DataFrame:
    """
    Calculate visibility from extinction coefficient.

    Uses the Koschmieder equation: Visibility = 3.912 / Bext
    For Bext in Mm-1, Visibility in km: Visibility = 1096 / Bext

    Parameters
    ----------
    df_ext : DataFrame
        Extinction coefficient data (Mm-1). Any column name accepted.

    Returns
    -------
    DataFrame
        Visibility in kilometers.

    Raises
    ------
    ValueError
        If df_ext is None or empty.
    """
    if df_ext is None or df_ext.empty:
        raise ValueError(
            "\ncalculate_visibility() 需要消光係數資料！\n"
            "  必要輸入: df_ext (Extinction coefficient, Mm-1)"
        )

    result = DataFrame(index=df_ext.index)
    ext_val = df_ext.iloc[:, 0] if isinstance(df_ext, DataFrame) else df_ext
    result['Visibility'] = 1096 / ext_val
    return result


def calculate_MAC(df_abs: DataFrame, df_ec: DataFrame) -> DataFrame:
    """
    Calculate Mass Absorption Cross-section (MAC).

    MAC = Babs / EC_mass

    Parameters
    ----------
    df_abs : DataFrame
        Absorption coefficient data (Mm-1). Any column name accepted.
    df_ec : DataFrame
        Elemental carbon concentration (ug/m3). Any column name accepted.

    Returns
    -------
    DataFrame
        MAC values (m2/g).

    Raises
    ------
    ValueError
        If df_abs or df_ec is None or empty.
    """
    if df_abs is None or (hasattr(df_abs, 'empty') and df_abs.empty):
        raise ValueError(
            "\ncalculate_MAC() 需要吸收係數資料！\n"
            "  必要輸入: df_abs (Absorption coefficient, Mm-1)"
        )
    if df_ec is None or (hasattr(df_ec, 'empty') and df_ec.empty):
        raise ValueError(
            "\ncalculate_MAC() 需要元素碳資料！\n"
            "  必要輸入: df_ec (Elemental carbon, ug/m3)"
        )

    result = DataFrame(index=df_abs.index)
    abs_val = df_abs.iloc[:, 0] if isinstance(df_abs, DataFrame) else df_abs
    ec_val = df_ec.iloc[:, 0] if isinstance(df_ec, DataFrame) else df_ec
    result['MAC'] = abs_val / ec_val
    return result


def calculate_Ox(df_no2: DataFrame, df_o3: DataFrame) -> DataFrame:
    """
    Calculate total oxidant (Ox = NO2 + O3).

    Parameters
    ----------
    df_no2 : DataFrame
        NO2 concentration (ppb). Any column name accepted.
    df_o3 : DataFrame
        O3 concentration (ppb). Any column name accepted.

    Returns
    -------
    DataFrame
        Ox values (ppb).

    Raises
    ------
    ValueError
        If df_no2 or df_o3 is None or empty.
    """
    if df_no2 is None or (hasattr(df_no2, 'empty') and df_no2.empty):
        raise ValueError(
            "\ncalculate_Ox() 需要 NO2 資料！\n"
            "  必要輸入: df_no2 (NO2 concentration, ppb)"
        )
    if df_o3 is None or (hasattr(df_o3, 'empty') and df_o3.empty):
        raise ValueError(
            "\ncalculate_Ox() 需要 O3 資料！\n"
            "  必要輸入: df_o3 (O3 concentration, ppb)"
        )

    result = DataFrame(index=df_no2.index)
    no2_val = df_no2.iloc[:, 0] if isinstance(df_no2, DataFrame) else df_no2
    o3_val = df_o3.iloc[:, 0] if isinstance(df_o3, DataFrame) else df_o3
    result['Ox'] = no2_val + o3_val
    return result


def calculate_fRH(df_ext_wet: DataFrame, df_ext_dry: DataFrame) -> DataFrame:
    """
    Calculate the hygroscopic growth factor for extinction (fRH).

    fRH = Bext(wet) / Bext(dry)

    Parameters
    ----------
    df_ext_wet : DataFrame
        Wet extinction coefficient. Any column name accepted.
    df_ext_dry : DataFrame
        Dry extinction coefficient. Any column name accepted.

    Returns
    -------
    DataFrame
        fRH values.

    Raises
    ------
    ValueError
        If df_ext_wet or df_ext_dry is None or empty.
    """
    if df_ext_wet is None or (hasattr(df_ext_wet, 'empty') and df_ext_wet.empty):
        raise ValueError(
            "\ncalculate_fRH() 需要濕消光係數資料！\n"
            "  必要輸入: df_ext_wet (Wet extinction coefficient)"
        )
    if df_ext_dry is None or (hasattr(df_ext_dry, 'empty') and df_ext_dry.empty):
        raise ValueError(
            "\ncalculate_fRH() 需要乾消光係數資料！\n"
            "  必要輸入: df_ext_dry (Dry extinction coefficient)"
        )

    result = DataFrame(index=df_ext_wet.index)
    wet_val = df_ext_wet.iloc[:, 0] if isinstance(df_ext_wet, DataFrame) else df_ext_wet
    dry_val = df_ext_dry.iloc[:, 0] if isinstance(df_ext_dry, DataFrame) else df_ext_dry
    result['fRH'] = wet_val / dry_val
    return result


def get_required_columns():
    """
    Get required inputs for derived parameter functions.

    Returns
    -------
    dict
        Dictionary with function names as keys and required inputs as values.

    Examples
    --------
    >>> cols = get_required_columns()
    >>> print(cols['calculate_MAC'])
    """
    return {
        'derived_parameters': {
            'description': '所有輸入皆為可選，根據提供的資料計算相應的衍生參數',
            'PG': 'df_sca + df_abs',
            'MAC': 'df_abs + df_ec',
            'Ox': 'df_no2 + df_o3',
            'Vis_cal': 'df_ext',
            'fRH_IMPR': "df_improve['total_ext', 'total_ext_dry']",
            'OCEC_ratio': 'df_oc + df_ec',
            'PM1_PM25_ratio': 'df_pm1 + df_pm25'
        },
        'calculate_visibility': ['Extinction coefficient (any column)'],
        'calculate_MAC': ['Absorption coefficient (any column)', 'EC (any column)'],
        'calculate_Ox': ['NO2 (any column)', 'O3 (any column)'],
        'calculate_fRH': ['Wet extinction (any column)', 'Dry extinction (any column)'],
        'calculate_BrC_absorption': ['Absorption coefficients at multiple wavelengths (DataFrame with abs_370, abs_470, etc.)']
    }


def calculate_BrC_absorption(df_abs: DataFrame,
                              wavelengths: list[int] = None,
                              ref_wavelength: int = 880,
                              aae_bc: float = 1.0) -> DataFrame:
    """
    Calculate Brown Carbon (BrC) absorption by separating BC and BrC contributions.

    This method assumes:
    1. Black Carbon (BC) has a wavelength-independent AAE (default: 1.0)
    2. Absorption at the reference wavelength (880nm) is entirely from BC
    3. BrC absorption = Total absorption - BC absorption

    The BC absorption at any wavelength λ is calculated as:
        abs_BC(λ) = abs_ref * (ref_wavelength / λ)^AAE_BC

    Parameters
    ----------
    df_abs : DataFrame
        Absorption coefficient data with columns like 'abs_370', 'abs_470', etc.
        Units should be Mm-1.
    wavelengths : list[int], optional
        List of wavelengths to calculate BrC absorption for.
        Default: [370, 470, 520, 590, 660] (all wavelengths shorter than reference)
    ref_wavelength : int, default=880
        Reference wavelength (nm) where absorption is assumed to be purely BC.
    aae_bc : float, default=1.0
        Absorption Ångström Exponent for Black Carbon.
        Literature values typically range from 0.8 to 1.1 for fresh BC.

    Returns
    -------
    DataFrame
        DataFrame with columns:
        - abs_BC_{wl}: BC absorption at each wavelength (Mm-1)
        - abs_BrC_{wl}: BrC absorption at each wavelength (Mm-1, NaN if invalid)
        - BrC_fraction_{wl}: BrC contribution fraction (0-1, NaN if invalid)
        - AAE_BrC: Absorption Ångström Exponent of BrC (NaN if invalid)

    Notes
    -----
    This separation method is based on the assumption that BC has a constant AAE
    of approximately 1.0 across all wavelengths, while BrC exhibits stronger
    absorption at shorter wavelengths (higher AAE).

    The AAE_BC = 1.0 assumption comes from Mie theory calculations for pure
    graphitic carbon particles. However, this value can vary depending on
    particle size and mixing state.

    **Validity check**: If calculated BC absorption exceeds total absorption
    at ANY wavelength, the entire row is marked as invalid (NaN for all BrC values).
    This indicates the separation assumption is not valid for that data point.

    References
    ----------
    - Lack, D.A. and Langridge, J.M. (2013). Atmos. Chem. Phys., 13, 8321-8341.
    - Kirchstetter, T.W. et al. (2004). J. Geophys. Res., 109, D21208.

    Examples
    --------
    >>> from AeroViz import DataProcess
    >>> optical = DataProcess(method='Optical')
    >>> brc_result = optical.BrC(df_abs, aae_bc=1.0)
    """
    if df_abs is None or df_abs.empty:
        raise ValueError(
            "\ncalculate_BrC_absorption() 需要多波長吸收係數資料！\n"
            "  必要輸入: df_abs (含有 abs_370, abs_470, ... 等欄位的 DataFrame)"
        )

    # Default wavelengths for BrC calculation (shorter than reference)
    if wavelengths is None:
        wavelengths = [370, 470, 520, 590, 660]

    # Find available absorption columns
    abs_cols = [col for col in df_abs.columns if col.startswith('abs_')]
    available_wl = []
    for col in abs_cols:
        try:
            wl = int(col.split('_')[1])
            available_wl.append(wl)
        except (ValueError, IndexError):
            continue

    # Check if reference wavelength is available
    ref_col = f'abs_{ref_wavelength}'
    if ref_col not in df_abs.columns:
        raise ValueError(
            f"\n找不到參考波長 {ref_wavelength}nm 的吸收資料！\n"
            f"  可用的波長: {sorted(available_wl)}\n"
            f"  請確保 df_abs 包含 '{ref_col}' 欄位"
        )

    # Filter wavelengths to those available and shorter than reference
    calc_wavelengths = [wl for wl in wavelengths
                        if wl in available_wl and wl < ref_wavelength]

    if not calc_wavelengths:
        raise ValueError(
            f"\n沒有可用的短波長資料用於 BrC 計算！\n"
            f"  請求的波長: {wavelengths}\n"
            f"  可用的波長: {sorted(available_wl)}\n"
            f"  參考波長: {ref_wavelength}nm"
        )

    result = DataFrame(index=df_abs.index)

    # Reference absorption (assumed to be pure BC at 880nm)
    abs_ref = df_abs[ref_col]

    # Track if BC > total at any wavelength (invalid separation)
    bc_exceeds_total = np.zeros(len(df_abs), dtype=bool)

    # Calculate BC and BrC absorption at each wavelength
    brc_abs_data = {}
    bc_abs_data = {}

    for wl in calc_wavelengths:
        abs_col = f'abs_{wl}'
        abs_total = df_abs[abs_col]

        # BC absorption at this wavelength using power law
        # abs_BC(λ) = abs_ref * (λ_ref / λ)^AAE_BC
        abs_bc = abs_ref * (ref_wavelength / wl) ** aae_bc

        # Check if BC exceeds total at this wavelength
        bc_exceeds_total |= (abs_bc > abs_total).values

        # BrC absorption = Total - BC
        abs_brc = abs_total - abs_bc

        # BrC fraction (before clipping)
        brc_fraction = np.where(abs_total > 0, abs_brc / abs_total, np.nan)

        # Store raw values
        bc_abs_data[wl] = abs_bc
        brc_abs_data[wl] = abs_brc.clip(lower=0)  # Clip for AAE calculation

        result[f'abs_BC_{wl}'] = abs_bc
        result[f'abs_BrC_{wl}'] = abs_brc.clip(lower=0)
        result[f'BrC_fraction_{wl}'] = np.where(brc_fraction >= 0, brc_fraction, np.nan)

    # Calculate BrC AAE using linear regression on log-log scale
    brc_wavelengths = np.array(sorted(brc_abs_data.keys()))

    def calc_brc_aae(row_data):
        """Calculate AAE for a single row of BrC absorption data."""
        brc_values = np.array([row_data.get(wl, np.nan) for wl in brc_wavelengths])

        # Need at least 2 valid points for AAE calculation
        valid_mask = (brc_values > 0) & np.isfinite(brc_values)
        if valid_mask.sum() < 2:
            return np.nan

        valid_wl = brc_wavelengths[valid_mask]
        valid_brc = brc_values[valid_mask]

        # Linear fit on log-log scale: log(abs) = -AAE * log(λ) + intercept
        try:
            log_wl = np.log(valid_wl)
            log_brc = np.log(valid_brc)
            slope, _ = np.polyfit(log_wl, log_brc, 1)
            return -slope  # AAE is negative of slope
        except (np.linalg.LinAlgError, ValueError):
            return np.nan

    # Calculate AAE_BrC for each row
    aae_brc_values = []
    for idx in df_abs.index:
        row_data = {wl: brc_abs_data[wl].loc[idx] for wl in brc_wavelengths}
        aae_brc_values.append(calc_brc_aae(row_data))

    aae_raw = np.array(aae_brc_values)

    # Validity check: BC must not exceed total absorption at any wavelength
    # If BC > total at any wavelength, the entire row is invalid
    valid_separation = ~bc_exceeds_total

    # Set all values to NaN for invalid rows (including BC)
    for wl in calc_wavelengths:
        result.loc[~valid_separation, f'abs_BC_{wl}'] = np.nan
        result.loc[~valid_separation, f'abs_BrC_{wl}'] = np.nan
        result.loc[~valid_separation, f'BrC_fraction_{wl}'] = np.nan

    result['AAE_BrC'] = np.where(valid_separation, aae_raw, np.nan)

    return result
