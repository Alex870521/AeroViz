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
           'calculate_Ox', 'calculate_fRH', 'get_required_columns']

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
        'calculate_fRH': ['Wet extinction (any column)', 'Dry extinction (any column)']
    }
