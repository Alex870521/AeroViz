"""
Mass and volume reconstruction for aerosol chemical composition.

This module reconstructs aerosol mass and volume from ionic species measurements,
handling both ammonium-sufficient and ammonium-deficient conditions.

Required Input Columns
----------------------
- NH4+ : Ammonium (ug/m3)
- SO42-: Sulfate (ug/m3)
- NO3- : Nitrate (ug/m3)
- Fe   : Iron (ug/m3) - for Soil calculation
- Na+  : Sodium (ug/m3) - for Sea Salt calculation
- OC   : Organic Carbon (ug/m3)
- EC   : Elemental Carbon (ug/m3)

Output Species
--------------
- AS   : Ammonium Sulfate (NH4)2SO4
- AN   : Ammonium Nitrate NH4NO3
- OM   : Organic Matter
- Soil : Soil/Crustal matter
- SS   : Sea Salt
- EC   : Elemental Carbon
"""

from pandas import concat, DataFrame

from AeroViz.dataProcess.core import validate_inputs

# =============================================================================
# Constants
# =============================================================================

# Required input columns
REQUIRED_COLUMNS = ['NH4+', 'SO42-', 'NO3-', 'Fe', 'Na+', 'OC', 'EC']

# Input column descriptions 輸入欄位說明
COLUMN_DESCRIPTIONS = {
    'NH4+': 'Particulate Ammonium (μg/m³) 顆粒態銨鹽',
    'SO42-': 'Particulate Sulfate (μg/m³) 顆粒態硫酸鹽',
    'NO3-': 'Particulate Nitrate (μg/m³) 顆粒態硝酸鹽',
    'Fe': 'Iron (μg/m³) 鐵 - 用於計算土壤/地殼物質 Soil',
    'Na+': 'Sodium (μg/m³) 鈉 - 用於計算海鹽 Sea Salt',
    'OC': 'Organic Carbon (μg/m³) 有機碳 - 用於計算有機物 OM',
    'EC': 'Elemental Carbon (μg/m³) 元素碳',
}

# Molecular weights (g/mol)
MOLECULAR_WEIGHT = {
    'NH4+': 18,
    'SO42-': 96,
    'NO3-': 62,
    'AS': 132,  # (NH4)2SO4
    'AN': 80,   # NH4NO3
}

# Conversion: raw species -> reconstructed species
SPECIES_MAPPING = {
    'AS': 'SO42-',
    'AN': 'NO3-',
    'OM': 'OC',
    'Soil': 'Fe',
    'SS': 'Na+',
    'EC': 'EC',
}

# Mass reconstruction coefficients
# AS: (NH4)2SO4 / SO4 = 132/96 = 1.375
# AN: NH4NO3 / NO3 = 80/62 = 1.29
MASS_COEFFICIENTS = {
    'AS': 1.375,
    'AN': 1.29,
    'OM': 1.8,
    'Soil': 28.57,
    'SS': 2.54,
    'EC': 1.0,
}

# Density for volume calculation (g/cm3)
DENSITY_COEFFICIENTS = {
    'AS': 1.76,
    'AN': 1.73,
    'OM': 1.4,
    'Soil': 2.6,
    'SS': 2.16,
    'EC': 1.5,
}

# Refractive index at different wavelengths (n + kj)
REFRACTIVE_INDEX = {
    '550': {
        'ALWC': 1.333 + 0j,
        'AS': 1.53 + 0j,
        'AN': 1.55 + 0j,
        'OM': 1.55 + 0.0163j,
        'Soil': 1.56 + 0.006j,
        'SS': 1.54 + 0j,
        'EC': 1.80 + 0.72j,
    },
    '450': {
        'ALWC': 1.333 + 0j,
        'AS': 1.57 + 0j,
        'AN': 1.57 + 0j,
        'OM': 1.58 + 0.056j,
        'Soil': 1.56 + 0.009j,
        'SS': 1.54 + 0j,
        'EC': 1.80 + 0.79j,
    },
}


# =============================================================================
# Helper Functions
# =============================================================================

def calculate_molar_concentrations(df):
    """Calculate molar concentrations from mass concentrations."""
    mol_NH4 = df['NH4+'] / MOLECULAR_WEIGHT['NH4+']
    mol_SO4 = df['SO42-'] / MOLECULAR_WEIGHT['SO42-']
    mol_NO3 = df['NO3-'] / MOLECULAR_WEIGHT['NO3-']
    return mol_NH4, mol_SO4, mol_NO3


def calculate_nh4_status(mol_NH4, mol_SO4, mol_NO3, index):
    """
    Calculate ammonium status (neutralization ratio).

    NH4 status = mol_NH4 / (2 * mol_SO4 + mol_NO3)
    - >= 1: Ammonium sufficient (Enough)
    - < 1: Ammonium deficient (Deficiency)
    """
    ratio = mol_NH4 / (2 * mol_SO4 + mol_NO3)

    df_status = DataFrame(index=index)
    df_status['ratio'] = ratio
    df_status['status'] = ratio.apply(lambda x: 'Enough' if x >= 1 else 'Deficiency')

    return df_status, ratio


def reconstruct_mass_enough(df, mol_NH4, mol_SO4, mol_NO3):
    """
    Reconstruct mass for NH4-sufficient conditions.

    When NH4 is sufficient:
    - AS = SO42- * 1.375 (full neutralization)
    - AN = NO3- * 1.29 (full neutralization)
    """
    df_mass = DataFrame(index=df.index)

    for species, coef in MASS_COEFFICIENTS.items():
        raw_col = SPECIES_MAPPING[species]
        df_mass[species] = df[raw_col] * coef

    return df_mass


def adjust_mass_deficiency(df_mass, mol_NH4, mol_SO4, mol_NO3, status_ratio):
    """
    Adjust AS and AN mass for NH4-deficient conditions.

    When NH4 is deficient (ratio < 1):
    1. Calculate residual NH4 after neutralizing SO4: residual = mol_NH4 - 2*mol_SO4
    2. If residual > 0: Some NH4 left to neutralize NO3
       - AN = min(residual, mol_NO3) * 80
    3. If residual <= 0: Not enough NH4 even for SO4
       - AN = 0
       - AS = mol_NH4/2 * 132 (partial neutralization)
    """
    deficient_mask = status_ratio < 1
    if not deficient_mask.any():
        return df_mass

    residual = mol_NH4 - 2 * mol_SO4

    # Case 1: residual > 0 (some NH4 left for NO3)
    pos_residual = residual > 0
    if pos_residual.any():
        # AN limited by residual or available NO3
        cond = pos_residual & (residual <= mol_NO3)
        df_mass.loc[cond, 'AN'] = residual.loc[cond] * MOLECULAR_WEIGHT['AN']

        cond = pos_residual & (residual > mol_NO3)
        df_mass.loc[cond, 'AN'] = mol_NO3.loc[cond] * MOLECULAR_WEIGHT['AN']

    # Case 2: residual <= 0 (not enough NH4 for SO4)
    neg_residual = residual <= 0
    if neg_residual.any():
        df_mass.loc[neg_residual, 'AN'] = 0

        # Partial AS neutralization
        cond = neg_residual & (mol_NH4 <= 2 * mol_SO4)
        df_mass.loc[cond, 'AS'] = mol_NH4.loc[cond] / 2 * MOLECULAR_WEIGHT['AS']

        cond = neg_residual & (mol_NH4 > 2 * mol_SO4)
        df_mass.loc[cond, 'AS'] = mol_SO4.loc[cond] * MOLECULAR_WEIGHT['AS']

    return df_mass


def calculate_volume(df_mass, df_water=None):
    """
    Calculate species volume concentrations from mass using density coefficients.

    Output columns:
    - {species}_volume: Volume concentration for each species (μm³/m³)
    - total_dry: Total dry aerosol volume concentration (μm³/m³)
    - ALWC: Aerosol liquid water content volume (μm³/m³), if df_water provided
    - total_wet: Total wet aerosol volume (μm³/m³), if df_water provided
    """
    df_vol = DataFrame(index=df_mass.index)

    # Calculate dry volumes (μg/m³ / g/cm³ = μm³/m³)
    for species, density in DENSITY_COEFFICIENTS.items():
        if species in df_mass.columns:
            df_vol[f'{species}_volume'] = df_mass[species] / density

    # Total dry aerosol volume concentration
    volume_cols = [f'{sp}_volume' for sp in DENSITY_COEFFICIENTS.keys() if f'{sp}_volume' in df_vol.columns]
    df_vol['total_dry'] = df_vol[volume_cols].sum(axis=1, min_count=6)

    # Add ALWC (Aerosol Liquid Water Content) if provided
    if df_water is not None:
        df_vol['ALWC'] = df_water.copy()
        df_vol = df_vol.dropna()
        df_vol['total_wet'] = df_vol['total_dry'] + df_vol['ALWC']

    return df_vol


def calculate_refractive_index(df_vol, df_water=None):
    """
    Calculate volume-weighted refractive index at 550nm and 450nm.

    Output:
    - RI_dry: Dry aerosol refractive index (complex: n + kj)
    - RI_wet: Wet aerosol refractive index (if ALWC provided)
    """
    ri_results = {}

    for wavelength, ri_coef in REFRACTIVE_INDEX.items():
        df_ri = DataFrame(index=df_vol.index)

        # Calculate RI contribution from each species (volume * RI)
        available_species = []
        for species in DENSITY_COEFFICIENTS.keys():
            vol_col = f'{species}_volume'
            if vol_col in df_vol.columns:
                df_ri[species] = df_vol[vol_col] * ri_coef[species]
                available_species.append(species)

        # Dry RI (volume-weighted average): sum(Vi * RIi) / total_V
        df_ri['RI_dry'] = (df_ri[available_species] / df_vol['total_dry'].values.reshape(-1, 1)).sum(axis=1)

        # Wet RI (if ALWC provided)
        df_ri['RI_wet'] = None
        if df_water is not None and 'total_wet' in df_vol.columns:
            df_ri['ALWC'] = df_vol['ALWC'] * ri_coef['ALWC']
            all_species = available_species + ['ALWC']
            df_ri['RI_wet'] = (df_ri[all_species] / df_vol['total_wet'].values.reshape(-1, 1)).sum(axis=1)

        ri_results[f'RI_{wavelength}'] = df_ri[['RI_dry', 'RI_wet']]

    return ri_results


def calculate_density(df_mass, df_vol, df_all, df_density=None):
    """Calculate aerosol density (reconstructed and measured)."""
    # Reconstructed density
    density_rec = df_mass['total'] / df_vol['total_dry']

    # Measured density (if density data provided)
    if df_density is not None:
        df_den_all = concat([
            df_all[['SO42-', 'NO3-', 'NH4+', 'EC']],
            df_density,
            df_mass['OM']
        ], axis=1).dropna()

        vol_cal = (
            df_den_all[['SO42-', 'NO3-', 'NH4+']].sum(axis=1) / 1.75 +
            df_den_all['Cl-'] / 1.52 +
            df_den_all['OM'] / 1.4 +
            df_den_all['EC'] / 1.77
        )
        density_mat = df_den_all.sum(axis=1, min_count=6) / vol_cal
    else:
        vol_cal = DataFrame()
        density_mat = density_rec

    return density_mat, density_rec, vol_cal


def calculate_equivalents(mol_NH4, mol_SO4, mol_NO3):
    """Calculate molar and equivalent concentrations."""
    df_eq = concat([
        mol_NH4, mol_SO4, mol_NO3,
        mol_NH4 * 1,  # eq_NH4 (charge = 1)
        mol_SO4 * 2,  # eq_SO4 (charge = 2)
        mol_NO3 * 1   # eq_NO3 (charge = 1)
    ], axis=1)
    df_eq.columns = ['mol_NH4', 'mol_SO4', 'mol_NO3', 'eq_NH4', 'eq_SO4', 'eq_NO3']
    return df_eq


# =============================================================================
# Main Function
# =============================================================================

def reconstruction_basic(df_che, df_ref, df_water=None, df_density=None, nam_lst=None):
    """
    Reconstruct aerosol mass and volume from chemical composition.

    This function converts ionic species (NH4+, SO42-, NO3-, etc.) to
    reconstructed species (AS, AN, OM, Soil, SS, EC) considering the
    ammonium neutralization status.

    Parameters
    ----------
    df_che : tuple of DataFrames
        Chemical composition data. Will be concatenated and renamed to nam_lst.
    df_ref : DataFrame or Series
        Reference mass (e.g., PM2.5) for quality control.
    df_water : DataFrame or None, optional
        Aerosol liquid water content (ALWC).
    df_density : DataFrame or None, optional
        Measured density data (requires 'Cl-' column).
    nam_lst : list, optional
        Column names for df_che after concatenation.
        Default: ['NH4+', 'SO42-', 'NO3-', 'Fe', 'Na+', 'OC', 'EC']

    Returns
    -------
    dict
        Dictionary containing:
        - 'mass': Reconstructed mass (AS, AN, OM, Soil, SS, EC, total)
        - 'volume': Reconstructed volume (species + total_dry, total_wet)
        - 'vol_cal': Calculated volume for density
        - 'eq': Molar and equivalent concentrations
        - 'NH4_status': Ammonium status ('ratio' and 'status')
        - 'density_mat': Measured density
        - 'density_rec': Reconstructed density
        - 'RI_550': Refractive index at 550nm
        - 'RI_450': Refractive index at 450nm

    Raises
    ------
    ValueError
        If required columns are missing.

    Examples
    --------
    >>> result = reconstruction_basic(
    ...     df_che=(df_ions, df_carbon),
    ...     df_ref=df_pm25,
    ...     df_water=df_alwc,
    ...     nam_lst=['NH4+', 'SO42-', 'NO3-', 'Fe', 'Na+', 'OC', 'EC']
    ... )
    >>> result['mass']       # Reconstructed mass
    >>> result['NH4_status'] # Ammonium status
    """
    # Default column names
    if nam_lst is None:
        nam_lst = REQUIRED_COLUMNS

    # Prepare input data
    df_all = concat(df_che, axis=1)
    original_index = df_all.index.copy()
    df_all.columns = nam_lst

    # Validate required columns
    validate_inputs(df_all, REQUIRED_COLUMNS, 'reconstruction_basic', COLUMN_DESCRIPTIONS)

    # Step 1: Calculate molar concentrations
    mol_NH4, mol_SO4, mol_NO3 = calculate_molar_concentrations(df_all)

    # Step 2: Calculate NH4 status
    df_nh4_status, status_ratio = calculate_nh4_status(mol_NH4, mol_SO4, mol_NO3, original_index)

    # Step 3: Reconstruct mass (assuming NH4 sufficient)
    df_mass = reconstruct_mass_enough(df_all, mol_NH4, mol_SO4, mol_NO3)

    # Step 4: Adjust for NH4 deficiency
    df_mass = adjust_mass_deficiency(df_mass, mol_NH4, mol_SO4, mol_NO3, status_ratio)
    df_mass['total'] = df_mass.sum(axis=1, min_count=6)

    # Quality control ratio
    qc_ratio = df_mass['total'] / df_ref
    qc_valid = (qc_ratio >= 0.5) & (qc_ratio <= 1.5)

    # Step 5: Calculate volume
    df_mass_valid = df_mass.dropna().copy()
    df_vol = calculate_volume(df_mass_valid, df_water)

    # Step 6: Calculate density
    density_mat, density_rec, vol_cal = calculate_density(df_mass, df_vol, df_all, df_density)

    # Step 7: Calculate refractive index
    ri_results = calculate_refractive_index(df_vol, df_water)

    # Step 8: Calculate equivalents
    df_eq = calculate_equivalents(mol_NH4, mol_SO4, mol_NO3)

    # Compile output
    out = {
        'mass': df_mass,
        'volume': df_vol,
        'vol_cal': vol_cal,
        'eq': df_eq,
        'NH4_status': df_nh4_status,
        'density_mat': density_mat,
        'density_rec': density_rec,
    }
    out.update(ri_results)

    # Reindex all outputs to original index
    for key, value in out.items():
        if hasattr(value, 'reindex'):
            out[key] = value.reindex(original_index)

    return out


# =============================================================================
# Utility Functions
# =============================================================================

def mass_ratio(df):
    """
    Calculate mass ratios relative to PM2.5.

    Parameters
    ----------
    df : Series
        Must contain 'PM25' and 'total_mass' values.

    Returns
    -------
    Series
        Mass ratios for each species.
    """
    if df['PM25'] >= df['total_mass']:
        df['others'] = df['PM25'] - df['total_mass']
    else:
        df['others'] = 0

    for val, species in zip(df.values, df.index):
        df[f'{species}_ratio'] = round(val / df['PM25'], 3)

    return df['others':].drop(labels=['PM25_ratio', 'total_mass_ratio'])


def get_required_columns():
    """
    Get required column names and output descriptions.

    Returns
    -------
    dict
        Documentation for reconstruction_basic inputs and outputs.
    """
    return {
        'reconstruction_basic': {
            'required_columns': REQUIRED_COLUMNS.copy(),
            'column_descriptions': COLUMN_DESCRIPTIONS.copy(),
            'outputs': {
                'mass': 'Reconstructed mass (AS, AN, OM, Soil, SS, EC, total)',
                'volume': 'Reconstructed volume with ALWC',
                'eq': 'Molar and equivalent concentrations',
                'NH4_status': "Ammonium status: 'ratio' and 'status' (Enough/Deficiency)",
                'density_mat': 'Measured density',
                'density_rec': 'Reconstructed density',
                'RI_550': 'Refractive index at 550nm (RI_dry, RI_wet)',
                'RI_450': 'Refractive index at 450nm (RI_dry, RI_wet)',
            },
            'coefficients': {
                'mass': MASS_COEFFICIENTS,
                'density': DENSITY_COEFFICIENTS,
            }
        },
    }


# Backward compatibility
_basic = reconstruction_basic
DEFAULT_REQUIRED_COLUMNS = REQUIRED_COLUMNS
