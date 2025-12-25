"""
Chemical calculations for aerosol analysis.

This module provides functions for:
- Molar concentration conversion
- Volume-average mixing refractive index
- Kappa (hygroscopicity parameter)
- Growth factor (gRH)
- Gas-particle partitioning ratios (SOR, NOR, NTR, epsilon)
"""

from pandas import concat, DataFrame

from AeroViz.dataProcess.core import validate_inputs

# =============================================================================
# Constants
# =============================================================================

# Molecular weights in g/mol
MOLECULAR_WEIGHTS = {
    'SO42-': 96.06,
    'NO3-': 62.00,
    'Cl-': 35.4,
    'Ca2+': 40.078,
    'K+': 39.098,
    'Mg2+': 24.305,
    'Na+': 22.99,
    'NH4+': 18.04,
}

# Gas molecular weights for partition calculations
GAS_MOLECULAR_WEIGHTS = {
    'SO2': 64.07,
    'NO2': 46.01,
    'NH3': 17.03,
    'HNO3': 63.01,
    'HCl': 36.46,
}

# =============================================================================
# Required columns definitions
# =============================================================================

VOLUME_MIXING_REQUIRED = ['total_dry']
VOLUME_MIXING_SPECIES = ['AS', 'AN', 'OM', 'Soil', 'SS', 'EC']

KAPPA_REQUIRED = ['gRH', 'AT', 'RH']
GRH_VOLUME_REQUIRED = ['total_dry']
GRH_ALWC_REQUIRED = ['ALWC']

# Partition calculation required columns
PARTITION_REQUIRED = ['temp']  # Temperature is required for molar conversion
PARTITION_SPECIES = {
    'SOR': ['SO42-', 'SO2'],      # Sulfur Oxidation Ratio
    'NOR': ['NO3-', 'NO2'],       # Nitrogen Oxidation Ratio
    'NOR_2': ['NO3-', 'NO2', 'HNO3'],  # NOR including HNO3
    'NTR': ['NH4+', 'NH3'],       # Nitrogen Transformation Ratio
    'epls_NO3': ['NO3-', 'HNO3'],  # NO3 partitioning
    'epls_NH4': ['NH4+', 'NH3'],   # NH4 partitioning
    'epls_Cl': ['Cl-', 'HCl'],     # Cl partitioning
}

# =============================================================================
# Column descriptions (Chinese/English) - 欄位說明
# =============================================================================

# Volume-average mixing 體積平均混合計算所需欄位
VOLUME_COLUMN_DESCRIPTIONS = {
    'AS_volume': 'Ammonium Sulfate volume (μm³/m³) 硫酸銨體積濃度',
    'AN_volume': 'Ammonium Nitrate volume (μm³/m³) 硝酸銨體積濃度',
    'OM_volume': 'Organic Matter volume (μm³/m³) 有機物體積濃度',
    'Soil_volume': 'Soil/Crustal volume (μm³/m³) 土壤/地殼物質體積濃度',
    'SS_volume': 'Sea Salt volume (μm³/m³) 海鹽體積濃度',
    'EC_volume': 'Elemental Carbon volume (μm³/m³) 元素碳體積濃度',
    'total_dry': 'Total dry aerosol volume (μm³/m³) 乾氣膠總體積濃度',
}

# Kappa 吸濕參數計算所需欄位
KAPPA_COLUMN_DESCRIPTIONS = {
    'gRH': 'Hygroscopic growth factor (Dp_wet/Dp_dry) 吸濕成長因子 (濕粒徑/乾粒徑)',
    'AT': 'Ambient Temperature (°C) 環境溫度',
    'RH': 'Relative Humidity (%) 相對濕度',
}

# gRH 成長因子計算所需欄位
GRH_COLUMN_DESCRIPTIONS = {
    'total_dry': 'Total dry aerosol volume (μm³/m³) 乾氣膠總體積濃度',
    'ALWC': 'Aerosol Liquid Water Content (μg/m³) 氣膠液態水含量',
}

# Partition 氣固分配比計算所需欄位
PARTITION_COLUMN_DESCRIPTIONS = {
    'temp': 'Ambient Temperature (°C) 環境溫度',
    'SO42-': 'Particulate Sulfate (μg/m³) 顆粒態硫酸鹽',
    'SO2': 'Gaseous Sulfur Dioxide (μg/m³) 氣態二氧化硫',
    'NO3-': 'Particulate Nitrate (μg/m³) 顆粒態硝酸鹽',
    'NO2': 'Gaseous Nitrogen Dioxide (μg/m³) 氣態二氧化氮',
    'HNO3': 'Gaseous Nitric Acid (μg/m³) 氣態硝酸',
    'NH4+': 'Particulate Ammonium (μg/m³) 顆粒態銨鹽',
    'NH3': 'Gaseous Ammonia (μg/m³) 氣態氨',
    'Cl-': 'Particulate Chloride (μg/m³) 顆粒態氯鹽',
    'HCl': 'Gaseous Hydrochloric Acid (μg/m³) 氣態鹽酸',
}


def convert_mass_to_molar_concentration(df):
    """
    Convert mass concentration (μg/m³) to molar concentration (μmol/m³ for particles, ppm for gases).

    This function identifies ionic species based on the MOLECULAR_WEIGHTS dictionary
    and converts them from mass to molar units. Gaseous species are converted using
    the ideal gas law with temperature data from the input DataFrame.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing concentration data with column names matching ions
        in MOLECULAR_WEIGHTS. Must include 'temp' column in Celsius.

    Returns
    -------
    pandas.DataFrame
        DataFrame with all concentrations converted to molar units:
        - Ionic species: μg/m³ → μmol/m³
        - Gaseous species: μg/m³ → ppm (using ideal gas law)

    Notes
    -----
    - The function assumes temperature ('temp') is in Celsius and converts it to Kelvin
    - Uses the ideal gas constant of 0.082 L·atm/(mol·K)
    - Non-matched columns (except 'temp' and 'RH') are treated as gaseous species

    Examples
    --------
    >>> import pandas as pd
    >>> data = pd.DataFrame({
    ...     'SO42-': [10.0, 15.0],
    ...     'NO3-': [5.0, 7.5],
    ...     'O3': [30.0, 45.0],
    ...     'temp': [25.0, 30.0],
    ...     'RH': [60.0, 70.0]
    ... })
    >>> convert_mass_to_molar_concentration(data)
    """
    # Identify which columns are particulate ions vs. gases
    particle_keys = list(set(df.keys()) & set(MOLECULAR_WEIGHTS.keys()))
    gas_keys = list(set(df.keys()) - set(MOLECULAR_WEIGHTS.keys()) - {'temp', 'RH'})

    # Calculate gas constant * temperature factor for gas conversion (ideal gas law)
    temperature_factor = (df['temp'].to_frame() + 273.15) * 0.082

    # Convert particulate species (μg/m³ → μmol/m³)
    df_particles = concat([
        (df[key] / MOLECULAR_WEIGHTS[key]).copy() for key in particle_keys
    ], axis=1)

    # Convert gaseous species (μg/m³ → ppm)
    df_gases = df[gas_keys] / temperature_factor.values

    # Combine results
    return concat([df_particles, df_gases], axis=1)


def volume_average_mixing(df_volume, df_alwc=None):
    """
    Calculate volume-average refractive index using mixing rule.

    This function calculates the dry and ambient refractive indices
    based on volume-weighted mixing of individual species at 550 nm.

    Parameters
    ----------
    df_volume : DataFrame
        Volume concentration data (μm³/m³) with columns:
        - total_dry : Total dry aerosol volume concentration (required)
        - At least one of: AS_volume, AN_volume, OM_volume, Soil_volume, SS_volume, EC_volume
    df_alwc : DataFrame, optional
        Aerosol liquid water content (μg/m³) with 'ALWC' column.

    Returns
    -------
    DataFrame
        Refractive index data with columns:
        - n_dry : Real part of dry aerosol RI (dimensionless)
        - k_dry : Imaginary part of dry aerosol RI (dimensionless)
        - n_amb : Real part of ambient (wet) aerosol RI
        - k_amb : Imaginary part of ambient aerosol RI
        - gRH : Hygroscopic growth factor (Dp_wet/Dp_dry)

    Raises
    ------
    ValueError
        If required columns are missing.

    Notes
    -----
    Volume-average mixing rule: RI_mix = Σ(Vi * RIi) / V_total
    """
    import numpy as np
    from pandas import DataFrame

    # Validate required columns
    validate_inputs(df_volume, VOLUME_MIXING_REQUIRED, 'volume_average_mixing', VOLUME_COLUMN_DESCRIPTIONS)

    # Check that at least one volume species exists
    available_species = [col for col in VOLUME_MIXING_SPECIES if f'{col}_volume' in df_volume.columns]
    if not available_species:
        volume_cols = [f'{sp}_volume' for sp in VOLUME_MIXING_SPECIES]
        raise ValueError(
            f"\nvolume_average_mixing() 至少需要一個體積欄位！\n"
            f"  可用欄位: {volume_cols}\n"
            f"  現有欄位: {sorted(df_volume.columns.tolist())}"
        )

    if df_alwc is not None:
        validate_inputs(df_alwc, GRH_ALWC_REQUIRED, 'volume_average_mixing (df_alwc)', GRH_COLUMN_DESCRIPTIONS)

    # Refractive index values at 550 nm
    RI_values = {
        'n': {'AS': 1.53, 'AN': 1.55, 'OM': 1.55, 'Soil': 1.56, 'SS': 1.54, 'EC': 1.80, 'ALWC': 1.33},
        'k': {'AS': 0.00, 'AN': 0.00, 'OM': 0.00, 'Soil': 0.01, 'SS': 0.00, 'EC': 0.54, 'ALWC': 0.00}
    }

    volume_cols = ['AS', 'AN', 'OM', 'Soil', 'SS', 'EC']
    volume_ratio = DataFrame(index=df_volume.index)

    for col in volume_cols:
        if f'{col}_volume' in df_volume.columns:
            volume_ratio[f'{col}_volume_ratio'] = df_volume[f'{col}_volume'] / df_volume['total_dry']

    result = DataFrame(index=df_volume.index)

    result['n_dry'] = sum(
        RI_values['n'][col] * volume_ratio[f'{col}_volume_ratio']
        for col in volume_cols if f'{col}_volume_ratio' in volume_ratio.columns
    )

    result['k_dry'] = sum(
        RI_values['k'][col] * volume_ratio[f'{col}_volume_ratio']
        for col in volume_cols if f'{col}_volume_ratio' in volume_ratio.columns
    )

    if df_alwc is not None and 'ALWC' in df_alwc.columns:
        v_dry = df_volume['total_dry']
        v_wet = df_volume['total_dry'] + df_alwc['ALWC']

        multiplier = v_dry / v_wet
        alwc_ratio = 1 - multiplier

        result['ALWC_volume_ratio'] = alwc_ratio

        result['n_amb'] = (
                sum(
                    RI_values['n'][col] * volume_ratio[f'{col}_volume_ratio']
                    for col in volume_cols if f'{col}_volume_ratio' in volume_ratio.columns
                ) * multiplier +
                RI_values['n']['ALWC'] * alwc_ratio
        )

        result['k_amb'] = (
                sum(
                    RI_values['k'][col] * volume_ratio[f'{col}_volume_ratio']
                    for col in volume_cols if f'{col}_volume_ratio' in volume_ratio.columns
                ) * multiplier
        )

        result['gRH'] = (v_wet / v_dry) ** (1 / 3)
    else:
        result['n_amb'] = np.nan
        result['k_amb'] = np.nan
        result['gRH'] = np.nan

    return result


def kappa_calculate(df_data, diameter=0.5):
    """
    Calculate the hygroscopicity parameter kappa.

    Parameters
    ----------
    df_data : DataFrame
        Data containing:
        - gRH : Hygroscopic growth factor
        - AT  : Ambient temperature (Celsius)
        - RH  : Relative humidity (%)
    diameter : float, default=0.5
        Particle dry diameter in micrometers.

    Returns
    -------
    DataFrame
        Kappa values with 'kappa_chem' column.

    Raises
    ------
    ValueError
        If required columns (gRH, AT, RH) are missing.

    Examples
    --------
    >>> cols = get_required_columns()['kappa_calculate']
    >>> print(cols)
    ['gRH', 'AT', 'RH']
    """
    import numpy as np
    from pandas import DataFrame

    # Validate required columns
    validate_inputs(df_data, KAPPA_REQUIRED, 'kappa_calculate', KAPPA_COLUMN_DESCRIPTIONS)

    surface_tension = 0.072
    Mw = 18
    density = 1
    R = 8.314

    result = DataFrame(index=df_data.index)

    T = df_data['AT'] + 273
    A = 4 * (surface_tension * Mw) / (density * R * T)
    power = A / (diameter * 1e-6)

    a_w = (df_data['RH'] / 100) * np.exp(-power)

    gRH = df_data['gRH']
    result['kappa_chem'] = (gRH ** 3 - 1) * (1 - a_w) / a_w

    return result


def gRH_calculate(df_volume, df_alwc):
    """
    Calculate the hygroscopic growth factor gRH.

    Parameters
    ----------
    df_volume : DataFrame
        Volume data with 'total_dry' column.
    df_alwc : DataFrame
        Aerosol liquid water content with 'ALWC' column.

    Returns
    -------
    DataFrame
        Growth factor data with 'gRH' column.

    Raises
    ------
    ValueError
        If required columns are missing.

    Examples
    --------
    >>> cols = get_required_columns()['gRH_calculate']
    >>> print(cols)
    """
    from pandas import DataFrame

    # Validate required columns
    validate_inputs(df_volume, GRH_VOLUME_REQUIRED, 'gRH_calculate (df_volume)', GRH_COLUMN_DESCRIPTIONS)
    validate_inputs(df_alwc, GRH_ALWC_REQUIRED, 'gRH_calculate (df_alwc)', GRH_COLUMN_DESCRIPTIONS)

    result = DataFrame(index=df_volume.index)

    v_dry = df_volume['total_dry']
    v_wet = v_dry + df_alwc['ALWC']

    result['gRH'] = (v_wet / v_dry) ** (1 / 3)

    return result


def get_required_columns():
    """
    Get required column names for calculation functions.

    Returns
    -------
    dict
        Dictionary with function names as keys and required columns as values.

    Examples
    --------
    >>> cols = get_required_columns()
    >>> print(cols['kappa_calculate'])
    ['gRH', 'AT', 'RH']
    """
    return {
        'convert_mass_to_molar_concentration': {
            'required': ['temp'],
            'ionic_species': list(MOLECULAR_WEIGHTS.keys()),
            'description': 'Converts mass to molar concentration. Ionic species are optional.'
        },
        'volume_average_mixing': {
            'required': VOLUME_MIXING_REQUIRED.copy(),
            'species': [f'{sp}_volume' for sp in VOLUME_MIXING_SPECIES],
            'optional': ['ALWC (for ambient RI calculation)']
        },
        'kappa_calculate': KAPPA_REQUIRED.copy(),
        'gRH_calculate': {
            'df_volume': GRH_VOLUME_REQUIRED.copy(),
            'df_alwc': GRH_ALWC_REQUIRED.copy()
        },
        'partition_ratios': {
            'required': PARTITION_REQUIRED.copy(),
            'species': PARTITION_SPECIES.copy(),
            'description': 'Calculate gas-particle partitioning ratios'
        }
    }


# =============================================================================
# Gas-Particle Partitioning Functions
# =============================================================================

def partition_ratios(df_data):
    """
    Calculate gas-particle partitioning ratios.

    Calculates oxidation ratios and equilibrium partitioning coefficients
    to assess the degree of secondary aerosol formation.

    Parameters
    ----------
    df_data : DataFrame
        Data containing particle and gas concentrations (μg/m³).
        Required column: 'temp' (temperature in Celsius)
        Optional species columns (at least one pair needed):
        - SO42-, SO2 : for SOR (Sulfur Oxidation Ratio)
        - NO3-, NO2 : for NOR (Nitrogen Oxidation Ratio)
        - NO3-, NO2, HNO3 : for NOR_2 (complete nitrogen)
        - NH4+, NH3 : for NTR (Nitrogen Transformation Ratio)
        - Cl-, HCl : for chloride partitioning

    Returns
    -------
    DataFrame
        Partitioning ratios with columns:
        - SOR : SO₄²⁻ / (SO₄²⁻ + SO₂) - Sulfur oxidation ratio
        - NOR : NO₃⁻ / (NO₃⁻ + NO₂) - Nitrogen oxidation ratio
        - NOR_2 : (NO₃⁻ + HNO₃) / (NO₃⁻ + NO₂ + HNO₃) - Complete NOR
        - NTR : NH₄⁺ / (NH₄⁺ + NH₃) - Nitrogen transformation ratio
        - epls_SO42- : Same as SOR (epsilon for sulfate)
        - epls_NO3- : NO₃⁻ / (NO₃⁻ + HNO₃) - Nitrate partitioning
        - epls_NH4+ : Same as NTR (epsilon for ammonium)
        - epls_Cl- : Cl⁻ / (Cl⁻ + HCl) - Chloride partitioning

    Notes
    -----
    **Physical Meaning:**

    - **SOR (Sulfur Oxidation Ratio)**: Indicates the degree of SO₂ → SO₄²⁻
      conversion. Higher values suggest more aged/processed aerosols.
      SOR > 0.1 typically indicates secondary sulfate formation.

    - **NOR (Nitrogen Oxidation Ratio)**: Indicates the degree of NOₓ → NO₃⁻
      conversion. Higher values suggest photochemical aging.

    - **NTR (Nitrogen Transformation Ratio)**: Indicates the conversion of
      gaseous NH₃ to particulate NH₄⁺. Related to acid-base neutralization.

    - **Epsilon (ε)**: Equilibrium partitioning coefficient. Represents the
      fraction in particle phase at thermodynamic equilibrium.

    **Interpretation:**
    - Values near 1.0: Nearly complete conversion to particle phase
    - Values near 0.0: Gas phase dominant
    - Values 0.3-0.7: Active gas-particle partitioning

    Examples
    --------
    >>> import pandas as pd
    >>> data = pd.DataFrame({
    ...     'SO42-': [10.0, 15.0],
    ...     'SO2': [5.0, 3.0],
    ...     'NO3-': [8.0, 12.0],
    ...     'NO2': [20.0, 15.0],
    ...     'temp': [25.0, 30.0]
    ... })
    >>> result = partition_ratios(data)
    >>> print(result['SOR'])  # [0.67, 0.83]
    """
    # Validate temperature column exists
    validate_inputs(df_data, PARTITION_REQUIRED, 'partition_ratios', PARTITION_COLUMN_DESCRIPTIONS)

    # Convert to molar concentrations
    df_mol = convert_mass_to_molar_concentration(df_data)

    result = DataFrame(index=df_data.index)

    # Helper function to safely calculate ratio
    def safe_ratio(numerator, denominator):
        """Calculate ratio, returning NaN for division by zero."""
        import numpy as np
        with np.errstate(divide='ignore', invalid='ignore'):
            ratio = numerator / denominator
            ratio = ratio.replace([np.inf, -np.inf], np.nan)
        return ratio

    # SOR: Sulfur Oxidation Ratio
    # SO₄²⁻ / (SO₄²⁻ + SO₂)
    if 'SO42-' in df_mol.columns and 'SO2' in df_mol.columns:
        result['SOR'] = safe_ratio(
            df_mol['SO42-'],
            df_mol['SO42-'] + df_mol['SO2']
        )
        result['epls_SO42-'] = result['SOR']

    # NOR: Nitrogen Oxidation Ratio
    # NO₃⁻ / (NO₃⁻ + NO₂)
    if 'NO3-' in df_mol.columns and 'NO2' in df_mol.columns:
        result['NOR'] = safe_ratio(
            df_mol['NO3-'],
            df_mol['NO3-'] + df_mol['NO2']
        )

    # NOR_2: Complete NOR including HNO3
    # (NO₃⁻ + HNO₃) / (NO₃⁻ + NO₂ + HNO₃)
    if all(col in df_mol.columns for col in ['NO3-', 'NO2', 'HNO3']):
        result['NOR_2'] = safe_ratio(
            df_mol['NO3-'] + df_mol['HNO3'],
            df_mol['NO3-'] + df_mol['NO2'] + df_mol['HNO3']
        )

    # NTR: Nitrogen Transformation Ratio (also called NTR+)
    # NH₄⁺ / (NH₄⁺ + NH₃)
    if 'NH4+' in df_mol.columns and 'NH3' in df_mol.columns:
        result['NTR'] = safe_ratio(
            df_mol['NH4+'],
            df_mol['NH4+'] + df_mol['NH3']
        )
        result['epls_NH4+'] = result['NTR']

    # Epsilon (ε) for NO3: NO₃⁻ / (NO₃⁻ + HNO₃)
    if 'NO3-' in df_mol.columns and 'HNO3' in df_mol.columns:
        result['epls_NO3-'] = safe_ratio(
            df_mol['NO3-'],
            df_mol['NO3-'] + df_mol['HNO3']
        )

    # Epsilon (ε) for Cl: Cl⁻ / (Cl⁻ + HCl)
    if 'Cl-' in df_mol.columns and 'HCl' in df_mol.columns:
        result['epls_Cl-'] = safe_ratio(
            df_mol['Cl-'],
            df_mol['Cl-'] + df_mol['HCl']
        )

    if result.empty:
        raise ValueError(
            "\npartition_ratios() 需要至少一組氣-固物種對！\n"
            f"  可用物種對: {list(PARTITION_SPECIES.keys())}\n"
            f"  現有欄位: {sorted(df_data.columns.tolist())}\n"
            "  例如: SO42- + SO2, NO3- + NO2, NH4+ + NH3"
        )

    return result
